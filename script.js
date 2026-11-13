const themeToggle = document.querySelector('.theme-toggle');
const themeColor = document.querySelector('meta[name="theme-color"]');
const root = document.documentElement;
const systemTheme = matchMedia('(prefers-color-scheme: dark)');
let themeOverride;
try { themeOverride = localStorage.getItem('ms-theme'); } catch {}

const applyTheme = (theme) => {
  root.dataset.theme = theme;
  themeToggle?.setAttribute('aria-pressed', String(theme === 'dark'));
  if (themeColor) themeColor.content = getComputedStyle(root).getPropertyValue('--paper').trim();
};

applyTheme(root.dataset.theme);
if (themeToggle) {
  themeToggle.hidden = false;
  themeToggle.addEventListener('click', () => {
    themeOverride = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('ms-theme', themeOverride); } catch {}
    applyTheme(themeOverride);
  });
}
systemTheme.addEventListener('change', ({ matches }) => {
  if (themeOverride !== 'light' && themeOverride !== 'dark') {
    applyTheme(matches ? 'dark' : 'light');
  }
});

const revealItems = document.querySelectorAll('.reveal');
const progressBar = document.querySelector('#scroll-progress');
const menuToggle = document.querySelector('.menu-toggle');
const mobileNav = document.querySelector('#mobile-nav');
const sectionLinks = document.querySelectorAll('[data-section]');

const updateReadingProgress = () => {
  if (!progressBar) return;
  const scrollable = document.documentElement.scrollHeight - window.innerHeight;
  const progress = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0;
  progressBar.style.width = `${Math.min(progress, 100)}%`;
};

window.addEventListener('scroll', updateReadingProgress, { passive: true });
window.addEventListener('resize', updateReadingProgress);
updateReadingProgress();

const closeMobileNav = () => {
  if (!menuToggle || !mobileNav) return;
  menuToggle.setAttribute('aria-expanded', 'false');
  mobileNav.hidden = true;
};

menuToggle?.addEventListener('click', () => {
  const isOpen = menuToggle.getAttribute('aria-expanded') === 'true';
  menuToggle.setAttribute('aria-expanded', String(!isOpen));
  mobileNav.hidden = isOpen;
});

mobileNav?.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeMobileNav));

const trackedSections = [...document.querySelectorAll('section[id]')].filter((section) => section.id !== 'overview');
if ('IntersectionObserver' in window && trackedSections.length) {
  const navObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      sectionLinks.forEach((link) => link.classList.toggle('is-active', link.dataset.section === entry.target.id));
    });
  }, { rootMargin: '-22% 0px -62% 0px', threshold: 0 });
  trackedSections.forEach((section) => navObserver.observe(section));
}

if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver((entries, currentObserver) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in');
        currentObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08 });

  revealItems.forEach((item) => observer.observe(item));
} else {
  revealItems.forEach((item) => item.classList.add('in'));
}

window.setTimeout(() => {
  document.querySelectorAll('.reveal:not(.in)').forEach((item) => item.classList.add('in'));
}, 1400);
