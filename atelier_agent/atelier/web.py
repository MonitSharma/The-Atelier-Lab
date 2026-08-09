"""Dependency-free local web workbench shell."""

from __future__ import annotations


def render_index() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Atelier Workbench</title>
<style>
:root{color-scheme:dark;font:15px system-ui,sans-serif;background:#111827;color:#e5e7eb}body{max-width:1200px;margin:0 auto;padding:24px}h1{margin-bottom:4px}small{color:#9ca3af}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-top:20px}.card{background:#1f2937;border:1px solid #374151;border-radius:12px;padding:16px;min-height:120px}.card h2{font-size:17px;margin-top:0;color:#c4b5fd}pre{white-space:pre-wrap;max-height:260px;overflow:auto;color:#d1d5db}input,button{border-radius:7px;border:1px solid #4b5563;background:#111827;color:#e5e7eb;padding:8px}button{cursor:pointer;background:#4c1d95}.row{display:flex;gap:8px}.wide{grid-column:1/-1}
</style></head><body>
<h1>✦ Atelier Workbench</h1><small>Local research workbench · loopback service · evidence before synthesis</small>
<div class="grid">
<section class="card"><h2>Workspace & privacy</h2><pre id="health">Loading…</pre></section>
<section class="card"><h2>Models</h2><pre id="models">Loading…</pre></section>
<section class="card"><h2>Library</h2><pre id="library">Loading…</pre></section>
<section class="card"><h2>Workflows</h2><pre id="workflows">Loading…</pre></section>
<section class="card"><h2>Recent traces</h2><pre id="tasks">Loading…</pre></section>
<section class="card"><h2>Approvals</h2><pre id="approvals">No pending approvals.</pre></section>
<section class="card wide"><h2>Route a task</h2><div class="row"><input id="route-input" size="70" placeholder="e.g. inspect this repository and run tests"><button onclick="routeTask()">Route</button></div><pre id="route-result"></pre></section>
<section class="card wide"><h2>Search local research library</h2><div class="row"><input id="search-input" size="70" placeholder="search your indexed papers and notes"><button onclick="searchLibrary()">Search</button></div><pre id="search-result"></pre></section>
</div>
<script>
const get=async path=>(await fetch(path)).json();
const show=(id,value)=>document.getElementById(id).textContent=JSON.stringify(value,null,2);
async function refresh(){for(const [id,path] of [['health','/health'],['models','/models'],['library','/library'],['workflows','/workflows'],['tasks','/tasks']]){try{show(id,await get(path))}catch(e){show(id,{error:String(e)})}}}
async function routeTask(){const task=document.getElementById('route-input').value;show('route-result',await (await fetch('/route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task})})).json())}
async function searchLibrary(){const query=document.getElementById('search-input').value;show('search-result',await (await fetch('/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query})})).json())}
refresh();
</script></body></html>"""
