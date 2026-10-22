'use strict';
// ---------- UI
const el=id=>document.getElementById(id);
const promptEl=el('prompt'), flashEl=el('flash'), dlg=el('dlg'), noteEl=el('note'), ov=el('ov'), app=el('app');
let flashT=0; function flash(label,text,secs){ flashEl.innerHTML='<small>'+label+'</small>'+text; flashEl.hidden=false; flashT=secs||6; }
function addClue(k){ if(!CLUES[k]||S.clues.includes(k))return; S.clues.push(k); renderNote(); beep(1200,0.08,'sine',0.04); }
function renderNote(){ el('noteList').innerHTML=S.clues.length?S.clues.map(k=>'<li>'+CLUES[k]+'</li>').join(''):'<li class="e">Nada todavía. Lee, escucha, aprieta.</li>'; }
let dlgOpts=[];
function openDialog(title,html,opts){ uiOpen=true; try{document.exitPointerLock();}catch(e){} el('dlgTitle').textContent=title; el('dlgTxt').innerHTML=html; dlgOpts=opts; const box=el('dlgOpts'); box.innerHTML=''; box.className='opts';
  opts.forEach((o,i)=>{ const b=document.createElement('button'); b.innerHTML='<span class="n">'+(i+1)+'</span>'+o.t; if(o.cls)b.classList.add(o.cls); b.onclick=()=>o.f(); box.appendChild(b); }); dlg.hidden=false; }
function closeDialog(){ uiOpen=false; dlg.hidden=true; dlgOpts=[]; keypadMode=false; }
function updHud(){ const st=el('hState'); st.textContent=S.base.toUpperCase(); st.className='st-'+S.base; el('hHp').textContent='♥'.repeat(Math.max(0,S.p.hp))+'·'.repeat(5-Math.max(0,S.p.hp)); el('hAmmo').textContent=S.p.ammo; }
