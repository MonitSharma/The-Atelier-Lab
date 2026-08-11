"""Hardened general-web search and webpage extraction.

Every external page is untrusted. The transport pins a validated public DNS
answer for each HTTPS hop, revalidates redirects, observes robots.txt, applies
per-domain pacing, bounds response size and type, and stores only extracted
text plus provenance in the research cache.
"""

from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import os
import socket
import ssl
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from atelier.config import settings
from atelier.security import detect_prompt_injection, redact_secrets
from atelier.workspace import WorkspaceError, current_workspace_context
from tools.base import Tool

USER_AGENT = "AtelierResearchBot/1.0"
SEARCH_PROVIDER = "bing_rss"
SEARCH_ENDPOINT = "https://www.bing.com/search"
ALLOWED_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_TRACKING_PARAMS = frozenset({
    "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "ref", "ref_src",
})
_SENSITIVE_QUERY_PARAMS = frozenset({
    "access_token", "api_key", "apikey", "auth", "authorization", "key",
    "password", "secret", "sig", "signature", "token",
})

Resolver = Callable[..., list[tuple[Any, ...]]]
Sleeper = Callable[[float], None]
Clock = Callable[[], float]


class WebPolicyError(RuntimeError):
    """A URL or response violated the web research policy."""

    def __init__(self, error_type: str, message: str) -> None:
        super().__init__(message)
        self.error_type = error_type


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    resolved_ip: str


Transport = Callable[[str, str, dict[str, str], int, float], HttpResult]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _network_error() -> dict[str, Any] | None:
    context = current_workspace_context()
    if context is None:
        return {"status": "denied", "error_type": "network_context_required",
                "message": "Web research requires an explicit workspace context."}
    try:
        context.require_network()
    except WorkspaceError as exc:
        return {"status": "denied", "error_type": "network_denied", "message": str(exc)}
    return None


def canonicalize_url(url: str) -> str:
    """Normalize a public URL identity without fetching it."""
    parsed = urlsplit(url.strip())
    host = (parsed.hostname or "").encode("idna").decode("ascii").lower()
    netloc = host
    if parsed.port and parsed.port != 443:
        netloc = f"{host}:{parsed.port}"
    query = urlencode([
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_PARAMS
    ], doseq=True)
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), netloc, path, query, ""))


def _public_addresses(hostname: str, resolver: Resolver) -> list[str]:
    try:
        answers = resolver(hostname, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise WebPolicyError("dns_failed", f"Could not resolve {hostname}: {exc}") from exc
    addresses: list[str] = []
    for answer in answers:
        sockaddr = answer[4]
        if not sockaddr:
            continue
        address = str(sockaddr[0])
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise WebPolicyError("dns_invalid", f"Resolver returned an invalid address for {hostname}") from exc
        if not ip.is_global:
            raise WebPolicyError("private_address_denied", f"Host {hostname} resolves to non-public address {ip}")
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise WebPolicyError("dns_failed", f"No usable public address found for {hostname}")
    return addresses


def validate_public_https_url(url: str, *, resolver: Resolver = socket.getaddrinfo) -> tuple[str, str]:
    """Return canonical URL and pinned public IP, or raise policy denial."""
    if not isinstance(url, str) or not url.strip() or len(url) > 2048:
        raise WebPolicyError("invalid_url", "URL must be a non-empty string no longer than 2048 characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in url):
        raise WebPolicyError("invalid_url", "URL cannot contain control characters")
    try:
        parsed = urlsplit(url.strip())
        port = parsed.port
    except ValueError as exc:
        raise WebPolicyError("invalid_url", f"Invalid URL: {exc}") from exc
    if parsed.scheme.lower() != "https":
        raise WebPolicyError("https_required", "Only HTTPS webpages may be fetched")
    if parsed.username or parsed.password:
        raise WebPolicyError("credentials_denied", "URLs containing credentials are not allowed")
    if not parsed.hostname:
        raise WebPolicyError("invalid_url", "URL must include a hostname")
    if port not in {None, 443}:
        raise WebPolicyError("port_denied", "Only the standard HTTPS port is allowed")
    try:
        host = parsed.hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise WebPolicyError("invalid_hostname", "Hostname is not valid IDNA") from exc
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise WebPolicyError("ip_literal_denied", "IP-literal webpage URLs are not allowed")
    query_names = {key.casefold() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    if query_names & _SENSITIVE_QUERY_PARAMS:
        raise WebPolicyError("sensitive_query_denied", "URL query contains credential-shaped parameters")
    normalized = canonicalize_url(urlunsplit(("https", host, parsed.path or "/", parsed.query, "")))
    addresses = _public_addresses(host, resolver)
    return normalized, addresses[0]


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, resolved_ip: str, *, timeout: float) -> None:
        super().__init__(hostname, port=443, timeout=timeout, context=ssl.create_default_context())
        self.resolved_ip = resolved_ip

    def connect(self) -> None:
        raw = socket.create_connection((self.resolved_ip, 443), self.timeout)
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host)


def _pinned_transport(
    url: str, resolved_ip: str, headers: dict[str, str], max_bytes: int, timeout: float,
) -> HttpResult:
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    path = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    connection = _PinnedHTTPSConnection(hostname, resolved_ip, timeout=timeout)
    try:
        connection.request("GET", path, headers={"Host": hostname, **headers})
        response = connection.getresponse()
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        body = response.read(max_bytes + 1)
        return HttpResult(response.status, response_headers, body, url, resolved_ip)
    finally:
        connection.close()


class DomainRateLimiter:
    """Process-local, per-domain pacing for polite sequential research."""

    def __init__(self, *, minimum_interval: float = 1.0, clock: Clock = time.monotonic, sleeper: Sleeper = time.sleep) -> None:
        self.minimum_interval = max(0.0, minimum_interval)
        self.clock = clock
        self.sleeper = sleeper
        self._last_request: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, hostname: str, *, crawl_delay: float | None = None) -> None:
        interval = max(self.minimum_interval, crawl_delay or 0.0)
        with self._lock:
            now = self.clock()
            remaining = interval - (now - self._last_request.get(hostname, now - interval))
            if remaining > 0:
                self.sleeper(remaining)
            self._last_request[hostname] = self.clock()


class WebResearchClient:
    """Search and fetch public webpages under an explicit security policy."""

    def __init__(
        self,
        *,
        resolver: Resolver = socket.getaddrinfo,
        transport: Transport = _pinned_transport,
        cache_dir: str | Path | None = None,
        timeout: float = 20.0,
        max_redirects: int = 3,
        minimum_interval: float = 1.0,
        clock: Clock = time.monotonic,
        sleeper: Sleeper = time.sleep,
    ) -> None:
        self.resolver = resolver
        self.transport = transport
        self.cache_dir = Path(cache_dir or (settings.research_cache_dir / "web")).expanduser().resolve()
        self.timeout = min(max(timeout, 1.0), 60.0)
        self.max_redirects = min(max(max_redirects, 0), 5)
        self.rate_limiter = DomainRateLimiter(minimum_interval=minimum_interval, clock=clock, sleeper=sleeper)

    def validate_url(self, url: str) -> tuple[str, str]:
        return validate_public_https_url(url, resolver=self.resolver)

    def _cache_path(self, namespace: str, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{namespace}-{digest}.json"

    def _cache_read(self, namespace: str, key: str, ttl_seconds: int) -> dict[str, Any] | None:
        path = self._cache_path(namespace, key)
        try:
            if time.time() - path.stat().st_mtime > ttl_seconds:
                return None
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else None
        except (OSError, json.JSONDecodeError, TypeError):
            return None

    def _cache_write(self, namespace: str, key: str, payload: dict[str, Any]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._cache_path(namespace, key)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(self.cache_dir), text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _request(
        self, url: str, *, max_bytes: int, respect_rate_limit: bool = True,
    ) -> HttpResult:
        current = url
        for hop in range(self.max_redirects + 1):
            normalized, resolved_ip = self.validate_url(current)
            hostname = urlsplit(normalized).hostname or ""
            if respect_rate_limit:
                self.rate_limiter.wait(hostname)
            response = self.transport(
                normalized,
                resolved_ip,
                {"User-Agent": USER_AGENT, "Accept": "text/html,text/plain,application/xhtml+xml,application/xml,text/xml", "Accept-Encoding": "identity"},
                max_bytes,
                self.timeout,
            )
            if len(response.body) > max_bytes:
                raise WebPolicyError("response_too_large", f"Response exceeded {max_bytes} bytes")
            if response.status in _REDIRECT_STATUSES:
                location = response.headers.get("location")
                if not location:
                    raise WebPolicyError("redirect_invalid", "Redirect response omitted Location")
                if hop >= self.max_redirects:
                    raise WebPolicyError("too_many_redirects", "Webpage exceeded the redirect limit")
                current = urljoin(normalized, location)
                continue
            return HttpResult(response.status, response.headers, response.body, normalized, resolved_ip)
        raise WebPolicyError("too_many_redirects", "Webpage exceeded the redirect limit")

    def _robots(self, url: str) -> tuple[bool, float | None, str]:
        parsed = urlsplit(url)
        robots_url = urlunsplit(("https", parsed.hostname or "", "/robots.txt", "", ""))
        robots_cache_key = f"{robots_url}:{url}"
        cached = self._cache_read("robots", robots_cache_key, 86_400)
        if cached is not None:
            return bool(cached.get("allowed")), cached.get("crawl_delay"), str(cached.get("status", "cached"))
        try:
            response = self._request(robots_url, max_bytes=512_000)
        except WebPolicyError:
            return False, None, "unreachable"
        if response.status == 429:
            return False, None, "rate_limited_429"
        if 400 <= response.status < 500:
            payload = {"allowed": True, "crawl_delay": None, "status": f"unavailable_{response.status}"}
            self._cache_write("robots", robots_cache_key, payload)
            return True, None, payload["status"]
        if response.status >= 500:
            return False, None, f"unreachable_{response.status}"
        robots_content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if robots_content_type not in {"text/plain", ""}:
            return False, None, f"invalid_content_type_{robots_content_type}"
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.body.decode("utf-8", errors="replace").splitlines())
        allowed = parser.can_fetch(USER_AGENT, url)
        delay = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*")
        crawl_delay = float(delay) if isinstance(delay, (int, float)) else None
        payload = {"allowed": allowed, "crawl_delay": crawl_delay, "status": "parsed"}
        self._cache_write("robots", robots_cache_key, payload)
        return allowed, crawl_delay, "parsed"

    def search(self, query: str, *, max_results: int = 5) -> dict[str, Any]:
        params = urlencode({"format": "rss", "q": query})
        request_url = f"{SEARCH_ENDPOINT}?{params}"
        cache_key = f"{SEARCH_PROVIDER}:{query}:{max_results}"
        cached = self._cache_read("search", cache_key, 3_600)
        if cached is not None:
            safe_records = []
            for record in cached.get("records", []):
                try:
                    safe_url, _ = self.validate_url(str(record.get("url", "")))
                except WebPolicyError:
                    continue
                safe_records.append({**record, "url": safe_url})
            return {**cached, "records": safe_records[:max_results], "cached": True}
        response = self._request(request_url, max_bytes=1_000_000)
        if response.status != 200:
            raise WebPolicyError("search_failed", f"Search provider returned HTTP {response.status}")
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in {"application/rss+xml", "application/xml", "text/xml"}:
            raise WebPolicyError("search_content_type", f"Unexpected search content type: {content_type or 'missing'}")
        try:
            root = ElementTree.fromstring(response.body)
        except ElementTree.ParseError as exc:
            raise WebPolicyError("search_parse_failed", f"Search provider returned invalid XML: {exc}") from exc
        records: list[dict[str, Any]] = []
        rejected = 0
        for item in root.findall("./channel/item"):
            title = " ".join((item.findtext("title") or "").split())
            candidate = (item.findtext("link") or "").strip()
            if not title or not candidate:
                continue
            try:
                safe_url, _ = self.validate_url(candidate)
            except WebPolicyError:
                rejected += 1
                continue
            records.append({
                "title": title,
                "url": safe_url,
                "summary": " ".join((item.findtext("description") or "").split())[:1000],
                "published": (item.findtext("pubDate") or "").strip() or None,
            })
            if len(records) >= max_results:
                break
        payload = {
            "status": "success", "tool": "web_search", "provider": SEARCH_PROVIDER,
            "query": query, "request_url": request_url, "retrieved_at": _now(),
            "records": records, "rejected_unsafe_results": rejected, "cached": False,
        }
        self._cache_write("search", cache_key, payload)
        return payload

    def fetch_page(
        self,
        url: str,
        *,
        max_bytes: int = 2_000_000,
        max_chars: int = 20_000,
        respect_robots: bool = True,
    ) -> dict[str, Any]:
        normalized, _ = self.validate_url(url)
        cache_key = f"{normalized}:{max_bytes}:{max_chars}:{respect_robots}"
        cached = self._cache_read("page", cache_key, 86_400)
        if cached is not None:
            try:
                self.validate_url(str(cached.get("final_url", "")))
                self.validate_url(str(cached.get("canonical_url", "")))
            except WebPolicyError:
                cached = None
            else:
                return {**cached, "cached": True}

        robots_allowed, crawl_delay, robots_status = True, None, "not_requested"
        if respect_robots:
            robots_allowed, crawl_delay, robots_status = self._robots(normalized)
            if not robots_allowed:
                raise WebPolicyError("robots_denied", f"robots.txt does not allow fetching {normalized}")
        hostname = urlsplit(normalized).hostname or ""
        self.rate_limiter.wait(hostname, crawl_delay=crawl_delay)
        response = self._request(normalized, max_bytes=max_bytes, respect_rate_limit=False)
        if response.status != 200:
            raise WebPolicyError("http_error", f"Webpage returned HTTP {response.status}")
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise WebPolicyError("content_type_denied", f"Unsupported webpage content type: {content_type or 'missing'}")

        raw_sha256 = hashlib.sha256(response.body).hexdigest()
        if content_type == "text/plain":
            title = urlsplit(response.url).path.rsplit("/", 1)[-1] or urlsplit(response.url).hostname or "Web page"
            text = response.body.decode("utf-8", errors="replace")
            canonical = response.url
            headings: list[str] = []
            language = None
            published = None
        else:
            extracted = extract_html(response.body, response.url, max_chars=max_chars)
            title = extracted["title"]
            text = extracted["text"]
            canonical = extracted["canonical_url"]
            headings = extracted["headings"]
            language = extracted["language"]
            published = extracted["published"]
        text = "\n".join(line for line in text.splitlines() if line.strip())[:max_chars]
        if len(text) < 80:
            raise WebPolicyError("insufficient_content", "Webpage did not contain enough extractable text")
        title, title_redacted = redact_secrets(title)
        text, text_redacted = redact_secrets(text)
        injection = detect_prompt_injection({"title": title, "text": text})
        payload = {
            "status": "success", "tool": "web_fetch", "requested_url": normalized,
            "final_url": response.url, "canonical_url": canonical, "title": title,
            "published": published, "language": language, "headings": headings,
            "text": text, "characters": len(text), "bytes": len(response.body),
            "content_type": content_type, "raw_sha256": raw_sha256,
            "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "retrieved_at": _now(), "robots_allowed": robots_allowed,
            "robots_status": robots_status, "prompt_injection_detected": injection,
            "untrusted_content": True, "secrets_redacted": title_redacted or text_redacted,
            "cached": False,
        }
        self._cache_write("page", cache_key, payload)
        return payload


def extract_html(body: bytes, base_url: str, *, max_chars: int = 20_000) -> dict[str, Any]:
    """Extract main readable text and provenance fields from bounded HTML."""
    soup = BeautifulSoup(body, "html.parser")
    for tag in soup(("script", "style", "noscript", "svg", "canvas", "template", "form", "nav", "footer", "aside", "dialog")):
        tag.decompose()
    title_tag = soup.find("meta", attrs={"property": "og:title"})
    title = ""
    if title_tag and title_tag.get("content"):
        title = str(title_tag["content"])
    elif soup.title:
        title = soup.title.get_text(" ", strip=True)
    title = " ".join(title.split())[:500] or (urlsplit(base_url).hostname or "Web page")

    canonical = base_url
    canonical_tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    if canonical_tag and canonical_tag.get("href"):
        candidate = urljoin(base_url, str(canonical_tag["href"]))
        try:
            parsed = urlsplit(candidate)
            same_host = parsed.hostname and parsed.hostname.casefold() == (urlsplit(base_url).hostname or "").casefold()
            if (
                parsed.scheme.lower() == "https" and same_host and parsed.port in {None, 443}
                and not parsed.username and not parsed.password
                and not ({key.casefold() for key, _ in parse_qsl(parsed.query)} & _SENSITIVE_QUERY_PARAMS)
            ):
                canonical = canonicalize_url(candidate)
        except ValueError:
            pass

    published = None
    for attrs in (
        {"property": "article:published_time"}, {"name": "date"}, {"itemprop": "datePublished"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            published = str(tag["content"])[:100]
            break
    language = str(soup.html.get("lang"))[:32] if soup.html and soup.html.get("lang") else None
    main = soup.find("article") or soup.find("main") or soup.find(attrs={"role": "main"}) or soup.body or soup
    headings = [" ".join(tag.get_text(" ", strip=True).split())[:300] for tag in main.find_all(("h1", "h2", "h3"))[:30]]
    lines: list[str] = []
    seen: set[str] = set()
    used = 0
    for line in main.get_text("\n", strip=True).splitlines():
        cleaned = " ".join(line.split())
        key = cleaned.casefold()
        if len(cleaned) < 2 or key in seen:
            continue
        seen.add(key)
        lines.append(cleaned)
        used += len(cleaned) + 1
        if used >= max_chars:
            break
    return {
        "title": title, "canonical_url": canonical, "published": published,
        "language": language, "headings": headings, "text": "\n".join(lines)[:max_chars],
    }


_DEFAULT_CLIENT: WebResearchClient | None = None
_DEFAULT_CLIENT_LOCK = threading.Lock()


def get_default_web_client() -> WebResearchClient:
    """Return one process-wide client so pacing applies across tool calls."""
    global _DEFAULT_CLIENT
    with _DEFAULT_CLIENT_LOCK:
        if _DEFAULT_CLIENT is None:
            _DEFAULT_CLIENT = WebResearchClient()
        return _DEFAULT_CLIENT


def search_web(arguments: dict[str, Any], *, client: WebResearchClient | None = None) -> dict[str, Any]:
    denied = _network_error()
    if denied:
        return denied
    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"status": "error", "error_type": "invalid_arguments", "message": "web_search requires a query"}
    if len(query) > 500:
        return {"status": "error", "error_type": "invalid_arguments", "message": "web_search query cannot exceed 500 characters"}
    max_results = arguments.get("max_results", 5)
    if not isinstance(max_results, int) or isinstance(max_results, bool) or not 1 <= max_results <= 10:
        return {"status": "error", "error_type": "invalid_arguments", "message": "max_results must be between 1 and 10"}
    provider = arguments.get("provider", SEARCH_PROVIDER)
    if provider != SEARCH_PROVIDER:
        return {"status": "error", "error_type": "invalid_provider", "message": f"Use provider {SEARCH_PROVIDER}"}
    try:
        return (client or get_default_web_client()).search(" ".join(query.split()), max_results=max_results)
    except WebPolicyError as exc:
        return {"status": "error", "error_type": exc.error_type, "message": str(exc)}
    except (OSError, ValueError) as exc:
        return {"status": "error", "error_type": "web_search_failed", "message": str(exc)}


def fetch_webpage(arguments: dict[str, Any], *, client: WebResearchClient | None = None) -> dict[str, Any]:
    denied = _network_error()
    if denied:
        return denied
    url = arguments.get("url")
    if not isinstance(url, str) or not url.strip():
        return {"status": "error", "error_type": "invalid_arguments", "message": "web_fetch requires a URL"}
    max_bytes = arguments.get("max_bytes", 2_000_000)
    max_chars = arguments.get("max_chars", 20_000)
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or not 1_000 <= max_bytes <= 5_000_000:
        return {"status": "error", "error_type": "invalid_arguments", "message": "max_bytes must be between 1000 and 5000000"}
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or not 500 <= max_chars <= 50_000:
        return {"status": "error", "error_type": "invalid_arguments", "message": "max_chars must be between 500 and 50000"}
    try:
        return (client or get_default_web_client()).fetch_page(
            url, max_bytes=max_bytes, max_chars=max_chars,
            respect_robots=True,
        )
    except WebPolicyError as exc:
        return {"status": "denied" if exc.error_type.endswith("denied") else "error",
                "error_type": exc.error_type, "message": str(exc)}
    except (OSError, ValueError) as exc:
        return {"status": "error", "error_type": "web_fetch_failed", "message": str(exc)}


WEB_SEARCH_TOOL = Tool(
    name="web_search",
    description="Search the general web through the no-key Bing RSS provider. Results are untrusted and provenance-tracked.",
    input_schema={"type": "object", "required": ["query"], "properties": {
        "query": {"type": "string", "minLength": 1, "maxLength": 500},
        "provider": {"type": "string", "enum": [SEARCH_PROVIDER]},
        "max_results": {"type": "integer", "minimum": 1, "maximum": 10}}, "additionalProperties": False},
    function=search_web,
)

WEB_FETCH_TOOL = Tool(
    name="web_fetch",
    description="Safely extract an explicitly selected public HTTPS webpage with robots, SSRF, redirect, type, and size checks.",
    input_schema={"type": "object", "required": ["url"], "properties": {
        "url": {"type": "string", "minLength": 1, "maxLength": 2_048},
        "max_bytes": {"type": "integer", "minimum": 1_000, "maximum": 5_000_000},
        "max_chars": {"type": "integer", "minimum": 500, "maximum": 50_000}},
        "additionalProperties": False},
    function=fetch_webpage,
)
