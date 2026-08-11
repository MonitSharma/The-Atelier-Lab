"""Dependency-free local web workbench shell."""

from __future__ import annotations


def render_index() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Atelier Workbench</title>
<style>
:root{color-scheme:dark;font:15px system-ui,sans-serif;background:#111827;color:#e5e7eb}body{max-width:1200px;margin:0 auto;padding:24px}h1{margin-bottom:4px}small{color:#9ca3af}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-top:20px}.card{background:#1f2937;border:1px solid #374151;border-radius:12px;padding:16px;min-height:120px}.card h2{font-size:17px;margin-top:0;color:#c4b5fd}pre{white-space:pre-wrap;max-height:260px;overflow:auto;color:#d1d5db}input,button,select{border-radius:7px;border:1px solid #4b5563;background:#111827;color:#e5e7eb;padding:8px}button{cursor:pointer;background:#4c1d95}.row{display:flex;gap:8px}.wide{grid-column:1/-1}
</style></head><body>
<h1>✦ Atelier Workbench</h1><small>Local research workbench · loopback service · evidence before synthesis</small>
<div class="grid">
<section class="card"><h2>Workspace & privacy</h2><pre id="health">Loading…</pre></section>
<section class="card"><h2>Models</h2><pre id="models">Loading…</pre></section>
<section class="card"><h2>Library</h2><pre id="library">Loading…</pre></section>
<section class="card"><h2>Workflows</h2><pre id="workflows">Loading…</pre></section>
<section class="card"><h2>Recent traces</h2><pre id="tasks">Loading…</pre></section>
<section class="card"><h2>Approvals</h2><pre id="approvals">No pending approvals.</pre><div id="approval-actions"></div></section>
<section class="card wide"><h2>Route a task</h2><div class="row"><input id="route-input" size="70" placeholder="e.g. inspect this repository and run tests"><button onclick="routeTask()">Route</button></div><pre id="route-result"></pre></section>
<section class="card wide"><h2>Chat / task input</h2><div class="row"><input id="chat-input" size="70" placeholder="ask Atelier to inspect, analyze, or explain"><label><input id="chat-start" type="checkbox"> start workflow</label><button onclick="submitChat()">Send</button></div><pre id="chat-result"></pre></section>
<section class="card wide"><h2>Search local research library</h2><div class="row"><input id="search-input" size="70" placeholder="search your indexed papers and notes"><button onclick="searchLibrary()">Search</button></div><pre id="search-result"></pre></section>
<section class="card wide"><h2>Deep research</h2><div class="row"><input id="research-input" size="70" placeholder="ask a question for iterative scholarly research"><select id="research-depth"><option>quick</option><option selected>standard</option><option>deep</option></select><button onclick="deepResearch()">Research</button></div><pre id="research-result"></pre></section>
<section class="card"><h2>Source viewer</h2><div class="row"><input id="source-input" placeholder="workspace-relative file"><button onclick="viewSource()">Open</button></div><pre id="source-result"></pre></section>
<section class="card"><h2>Upload / drop</h2><input id="upload-file" type="file"><input id="upload-destination" placeholder="destination path"><button onclick="uploadFile()">Upload</button><pre id="upload-result"></pre></section>
<section class="card"><h2>Paper actions</h2><input id="paper-path" placeholder="paper.pdf"><div class="row"><button onclick="paperAction('characterize')">Characterize</button><button onclick="paperAction('deep_read')">Deep read</button></div><pre id="paper-result"></pre></section>
<section class="card"><h2>Repository actions</h2><input id="repo-path" placeholder="repository path"><input id="repo-goal" placeholder="optional fix goal"><div class="row"><button onclick="repoAction('inspect')">Inspect</button><button onclick="repoAction('tests')">Test</button><button onclick="repoAction('fix')">Fix</button></div><pre id="repo-result"></pre></section>
</div>
<script>
const get=async path=>(await fetch(path)).json();
const show=(id,value)=>document.getElementById(id).textContent=JSON.stringify(value,null,2);
async function refresh(){for(const [id,path] of [['health','/health'],['models','/models'],['library','/library'],['workflows','/workflows'],['tasks','/tasks']]){try{show(id,await get(path))}catch(e){show(id,{error:String(e)})}}try{const value=await get('/approvals');show('approvals',value);const actions=document.getElementById('approval-actions');actions.replaceChildren();for(const item of (value.approvals||[])){const row=document.createElement('div');const button=document.createElement('button');button.textContent='Approve '+item.run_id.slice(0,8);button.onclick=async()=>{show('approvals',await (await fetch('/workflow_approve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:item.run_id,approved:true})})).json());refresh()};row.appendChild(button);actions.appendChild(row)}}catch(e){show('approvals',{error:String(e)})}}
async function routeTask(){const task=document.getElementById('route-input').value;show('route-result',await (await fetch('/route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task})})).json())}
async function searchLibrary(){const query=document.getElementById('search-input').value;show('search-result',await (await fetch('/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query})})).json())}
async function deepResearch(){const question=document.getElementById('research-input').value;const depth=document.getElementById('research-depth').value;show('research-result',await (await fetch('/research_deep',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,depth})})).json());refresh()}
async function submitChat(){const task=document.getElementById('chat-input').value;show('chat-result',await (await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task,start:document.getElementById('chat-start').checked})})).json());refresh()}
async function viewSource(){const path=encodeURIComponent(document.getElementById('source-input').value);show('source-result',await get('/source?path='+path))}
async function uploadFile(){const file=document.getElementById('upload-file').files[0];if(!file){show('upload-result',{error:'choose a file'});return}const reader=new FileReader();reader.onload=async()=>{show('upload-result',await (await fetch('/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:document.getElementById('upload-destination').value||file.name,content_base64:String(reader.result).split(',')[1]})})).json())};reader.readAsDataURL(file)}
async function paperAction(action){show('paper-result',await (await fetch('/paper_action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,path:document.getElementById('paper-path').value})})).json());refresh()}
async function repoAction(action){show('repo-result',await (await fetch('/repo_action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,path:document.getElementById('repo-path').value||'.',goal:document.getElementById('repo-goal').value})})).json());refresh()}
refresh();
</script></body></html>"""
