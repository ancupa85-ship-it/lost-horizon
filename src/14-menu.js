'use strict';
// ---------- MENÚ, OPCIONES, PAUSA Y GUÍA
const OPT={sens:1,invY:false,view:'1',post:true,shadows:true,vol:0.8,hints:true};
try{ Object.assign(OPT,JSON.parse(localStorage.getItem('lh-opt')||'{}')); }catch(e){}
function saveOpt(){ try{ localStorage.setItem('lh-opt',JSON.stringify(OPT)); }catch(e){} }
function applyOpt(){ usePost=!!OPT.post&&!!rt; if(renderer.shadowMap.enabled!==!!OPT.shadows){ renderer.shadowMap.enabled=!!OPT.shadows; scene.traverse(o=>{ if(o.isMesh){ (Array.isArray(o.material)?o.material:[o.material]).forEach(m=>m.needsUpdate=true); } }); }
  if(master)master.gain.value=OPT.vol; guideEl.hidden=!OPT.hints||!started; }
const guideEl=el('guide');
const GUIDE=[
  {k:'crouch',t:'Agáchate (Ctrl) en una sombra hasta leer OCULTO',ok:()=>S.guide.hidden},
  {k:'grab',t:'Acércate a un guardia por la espalda y pulsa F',ok:()=>S.interro>0},
  {k:'ask',t:'Pregúntale; si calla, APRIETA, y luego duérmelo',ok:()=>S.clues.some(k=>['peris','c130','c1983','roma','llave','fuente'].includes(k))&&S.ko>0},
  {k:'read',t:'Lee lo que encuentres (E). Tab abre el cuaderno de pistas',ok:()=>S.clues.length>=2},
  {k:'swap',t:'X cambia a Roig. Ella dispara sola si os descubren',ok:()=>S.swaps>0},
  {k:'vault',t:'La clave del archivo sale de juntar pistas. Dos fallos: alarma',ok:()=>W.vaultOpen},
];
function guideTick(){ if(entHidden(S.p))S.guide.hidden=true; if(!OPT.hints||!started||cut){ guideEl.hidden=true; return; }
  const items=GUIDE.map(g=>{ const done=S.guide[g.k]||(S.guide[g.k]=!!g.ok()); return {g,done}; }); const firstOpen=items.findIndex(i=>!i.done);
  if(firstOpen<0){ guideEl.hidden=true; return; } guideEl.hidden=false;
  const html=items.slice(0,Math.min(items.length,firstOpen+2)).map((i,n)=>'<li class="'+(i.done?'ok':(n===firstOpen?'now':''))+'">'+(i.done?'✓ ':'› ')+i.g.t+'</li>').join('');
  if(guideEl.dataset.html!==html){ guideEl.dataset.html=html; guideEl.innerHTML='<h4>GUÍA <span>H oculta</span></h4><ul>'+html+'</ul>'; } }
// menú principal / pausa
let paused=false;
function showMenu(pane){ ov.hidden=false; el('end').hidden=true; const m=el('menu'); m.hidden=false; m.querySelectorAll('[data-pane]').forEach(p=>{ p.hidden=p.dataset.pane!==pane; }); m.classList.toggle('paused',paused); el('mTitle').textContent=paused?'PAUSA':'PROJECT LOST HORIZON'; syncOptUI(); }
function syncOptUI(){ el('oSens').value=OPT.sens; el('oSensV').textContent=OPT.sens.toFixed(1); el('oInv').checked=OPT.invY; el('oView').value=OPT.view; el('oPost').checked=OPT.post; el('oShadow').checked=OPT.shadows; el('oVol').value=OPT.vol; el('oVolV').textContent=Math.round(OPT.vol*100)+'%'; el('oHints').checked=OPT.hints; }
function readOptUI(){ OPT.sens=+el('oSens').value; OPT.invY=el('oInv').checked; OPT.view=el('oView').value; OPT.post=el('oPost').checked; OPT.shadows=el('oShadow').checked; OPT.vol=+el('oVol').value; OPT.hints=el('oHints').checked; el('oSensV').textContent=OPT.sens.toFixed(1); el('oVolV').textContent=Math.round(OPT.vol*100)+'%'; saveOpt(); applyOpt(); if(AC)beep(900,0.05,'sine',0.04); }
function startGame(withIntro){ initAudio(); applyOpt(); setPower(true); started=true; paused=false; uiOpen=false; ov.hidden=true; third=OPT.view==='3'; try{gl.requestPointerLock();}catch(e){} if(withIntro)intro(); else codec(CODEC.start); }
function pauseGame(){ if(paused||!started)return; paused=true; uiOpen=true; try{document.exitPointerLock();}catch(e){} showMenu('pause'); }
function resumeGame(){ if(!paused)return; paused=false; uiOpen=false; ov.hidden=true; try{gl.requestPointerLock();}catch(e){} }
el('menu').addEventListener('click',e=>{ const b=e.target.closest('button'); if(!b)return; const go=b.dataset.go; if(AC)beep(700,0.04,'square',0.03);
  if(go==='main')showMenu(paused?'pause':'main'); else if(go)showMenu(go);
  else if(b.id==='btnStart'){ reset(); startGame(true); }
  else if(b.id==='btnResume')resumeGame();
  else if(b.id==='btnRestart'){ reset(); paused=false; uiOpen=false; ov.hidden=true; el('end').hidden=true; try{gl.requestPointerLock();}catch(e){} codec(CODEC.start); }
  else if(b.id==='btnQuit'){ reset(); paused=false; started=false; uiOpen=false; showMenu('main'); } });
el('menu').addEventListener('input',e=>{ if(e.target.closest('[data-pane="opt"]'))readOptUI(); });
el('menu').addEventListener('change',e=>{ if(e.target.closest('[data-pane="opt"]'))readOptUI(); });
showMenu('main');
