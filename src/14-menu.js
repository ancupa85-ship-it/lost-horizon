'use strict';
// ---------- MENÚ, OPCIONES, PAUSA Y GUÍA
const OPT={sens:1,invY:false,view:'1',post:true,shadows:true,vol:0.8,music:0.6,hints:true,simpleFig:false};
let GFX_PRESET=''; if(WEAK_GPU){ OPT.shadows=false; OPT.post=false; OPT.simpleFig=true; GFX_PRESET='ligero'; } else if(MOBILE_GPU){ OPT.shadows=false; GFX_PRESET='medio'; }
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
  {k:'order',t:'Roig espera donde está. G hace que te siga (y G otra vez, que espere)',ok:()=>S.orders>0},
  {k:'swap',t:'X cambia a Roig. Ella solo dispara si os descubren',ok:()=>S.swaps>0},
  {k:'uniform',t:'E junto a un guardia dormido le quita el uniforme: de lejos eres uno más',ok:()=>S.disguises>0},
  {k:'vault',t:'La clave del archivo sale de juntar pistas. Dos fallos: alarma',ok:()=>W.vaultOpen},
];
function guideTick(){ if(entHidden(S.p))S.guide.hidden=true; if(!OPT.hints||!started||cut){ guideEl.hidden=true; return; }
  const items=GUIDE.map(g=>{ const done=S.guide[g.k]||(S.guide[g.k]=!!g.ok()); return {g,done}; }); const firstOpen=items.findIndex(i=>!i.done);
  if(firstOpen<0){ guideEl.hidden=true; return; } guideEl.hidden=false;
  const html=items.slice(0,Math.min(items.length,firstOpen+2)).map((i,n)=>'<li class="'+(i.done?'ok':(n===firstOpen?'now':''))+'">'+(i.done?'✓ ':'› ')+i.g.t+'</li>').join('');
  if(guideEl.dataset.html!==html){ guideEl.dataset.html=html; guideEl.innerHTML='<h4>GUÍA <span>H oculta</span></h4><ul>'+html+'</ul>'; } }
// menú principal / pausa
let paused=false;
function showMenu(pane){ ov.hidden=false; el('end').hidden=true; const m=el('menu'); m.hidden=false; const sv=hasSave(); el('btnContinue').hidden=!sv||paused; if(sv)el('btnContinue').innerHTML='CONTINUAR <small>'+sv.tag+'</small>'; m.querySelectorAll('[data-pane]').forEach(p=>{ p.hidden=p.dataset.pane!==pane; }); m.classList.toggle('paused',paused); el('mTitle').textContent=paused?'PAUSA':'PROJECT LOST HORIZON'; syncOptUI(); }
function syncOptUI(){ el('oSens').value=OPT.sens; el('oSensV').textContent=OPT.sens.toFixed(1); el('oInv').checked=OPT.invY; el('oView').value=OPT.view; el('oPost').checked=OPT.post; el('oShadow').checked=OPT.shadows; el('oSimple').checked=!!OPT.simpleFig; el('oVol').value=OPT.vol; el('oVolV').textContent=Math.round(OPT.vol*100)+'%'; el('oMusic').value=OPT.music; el('oMusicV').textContent=Math.round(OPT.music*100)+'%'; el('oHints').checked=OPT.hints; }
function readOptUI(){ OPT.sens=+el('oSens').value; OPT.invY=el('oInv').checked; OPT.view=el('oView').value; OPT.post=el('oPost').checked; OPT.shadows=el('oShadow').checked; OPT.simpleFig=el('oSimple').checked; OPT.vol=+el('oVol').value; OPT.music=+el('oMusic').value; OPT.hints=el('oHints').checked; el('oSensV').textContent=OPT.sens.toFixed(1); el('oVolV').textContent=Math.round(OPT.vol*100)+'%'; el('oMusicV').textContent=Math.round(OPT.music*100)+'%'; saveOpt(); applyOpt(); if(AC)beep(900,0.05,'sine',0.04); }
function startGame(withIntro,silent){ initAudio(); applyOpt(); if(GFX_PRESET&&!S.flashSeen.gfx){ S.flashSeen.gfx=true; setTimeout(()=>flash('MODO '+GFX_PRESET.toUpperCase(),'Gráfica modesta detectada ('+(GPU_INFO||'desconocida').slice(0,40)+'): '+(GFX_PRESET==='ligero'?'sin sombras ni contornos y personajes sencillos.':'sin sombras.')+' Puedes cambiarlo en Opciones.',8),6000); } if(!silent)setPower(true); started=true; paused=false; uiOpen=false; ov.hidden=true; el('end').hidden=true; third=OPT.view==='3'; try{gl.requestPointerLock();}catch(e){} if(withIntro)intro(); else if(!silent)codec(CODEC.start); }
// guardado automático en puntos clave; CONTINUAR en el menú
const pickEnt=e=>({name:e.name,x:e.x,z:e.z,hp:e.hp,ammo:e.ammo,key:e.key,file:e.file,crouch:e.crouch,down:e.down,disguise:!!e.disguise});
function saveGame(tag){ if(!started||S.over)return; try{ const d={v:1,tag,when:Date.now(),t:S.t,ctrl:S.p.name,yaw,p:pickEnt(S.p),c:pickEnt(S.c),W:Object.assign({},W),
  guards:S.guards.map(g=>({x:g.x,z:g.z,fx:g.fx,fz:g.fz,wi:g.wi,dead:g.dead,down:g.down,fear:g.fear,hasKey:g.hasKey,stripped:!!g.stripped})),clues:S.clues.slice(),kill:S.kill,ko:S.ko,alarms:S.alarms,interro:S.interro,base:S.base,cigs:S.cigs,inCell:S.inCell,dogsDone:S.dogsDone,capturedOnce:!!S.capturedOnce,swaps:S.swaps,cOrder:S.cOrder,orders:S.orders,silencer:!!S.silencer,disguises:S.disguises,teamKO:S.teamKO,ammoTaken:S.ammoTaken,wrongCode:S.wrongCode,halloTalked:S.halloTalked,codecSeen:S.codecSeen,flashSeen:S.flashSeen,guide:S.guide,vidal:S.vidal,reinforced:S.reinforced,dogKills:S.dogKills,cellEscaped:!!S.cellEscaped,cellKey:!!S.cellKey,calls:S.calls||null};
  localStorage.setItem('lh-save',JSON.stringify(d)); S.savedT=2.5; }catch(e){} }
function hasSave(){ try{ return JSON.parse(localStorage.getItem('lh-save')||'null'); }catch(e){ return null; } }
function loadGame(){ const d=hasSave(); if(!d)return null; reset();
  if(d.reinforced){ S.reinforced=true; S.guards.push(mkGuard(REFDEF,true)); }
  d.guards.forEach((sg,i)=>{ const g=S.guards[i]; if(!g)return; Object.assign(g,{x:sg.x,z:sg.z,fx:sg.fx,fz:sg.fz,wi:sg.wi,dead:sg.dead,down:sg.down,fear:sg.fear,hasKey:sg.hasKey,stripped:!!sg.stripped}); g.state='patrol'; g.susp=0;
    if(g.dead||g.down>0){ S.bodies.push({x:g.x,z:g.z,dead:g.dead,g,carried:false,hidden:false,stripped:!!g.stripped}); g.fall=1; g.fig.g.rotation.z=Math.PI/2; g.fig.g.position.y=0.26; g.mark.visible=false; } g.fig.g.position.x=g.x; g.fig.g.position.z=g.z; });
  const byName={CUTTLAS:S.p,ROIG:S.c}; [d.p,d.c].forEach(e=>{ const t=byName[e.name]; if(t){ Object.assign(t,e); setDisguise(t,!!e.disguise); } }); if(d.ctrl==='ROIG'){ const a=S.p; S.p=S.c; S.c=a; }
  Object.assign(W,d.W); dynamicDoors.office.visible=!W.officeOpen; dynamicDoors.vault.visible=!W.vaultOpen; dynamicDoors.yard.visible=!!W.yardDoorClosed; setPower(W.power!==false);
  ['clues','kill','ko','alarms','interro','base','cigs','inCell','dogsDone','capturedOnce','swaps','cOrder','orders','silencer','disguises','teamKO','ammoTaken','wrongCode','halloTalked','codecSeen','flashSeen','guide','vidal','dogKills','cellEscaped','cellKey','t'].forEach(k=>{ if(d[k]!==undefined)S[k]=d[k]; }); if(d.calls)S.calls=d.calls;
  if(barsMesh)barsMesh.visible=!W.cellOpen; vidalFig.g.visible=!!S.inCell; yaw=d.yaw||yaw; pitch=0; S.camH=undefined; updHud(); renderNote(); el('hCig').textContent=S.cigs;
  el('hObj').textContent=S.inCell?(S.cellKey?'OBJETIVO: ABRE LA REJA CON LA LLAVE':S.vidal.gone?'OBJETIVO: BUSCA OTRA SALIDA DE LA CELDA':'OBJETIVO: HABLA CON HALLORAN Y CONVENCE A VIDAL'):(S.p.file||S.c.file)?'OBJETIVO: SAL POR LA PUERTA SURESTE':W.vaultOpen?'OBJETIVO: COGE EL EXPEDIENTE':'OBJETIVO: ENTRA EN EL ARCHIVO';
  S.c.fig.g.position.set(S.c.x,0,S.c.z); S.c.fig.g.rotation.z=0; return d; }
function continueGame(){ const d=loadGame(); if(!d){ showMenu('main'); return; } startGame(false,true); flash('CONTINUAR · '+clockStr(),d.tag+'. '+(S.p.name==='ROIG'?'Controlas a Roig.':'Controlas a Cuttlas.')+' R abre la radio si no sabes seguir.',6); }
function pauseGame(){ if(paused||!started)return; paused=true; uiOpen=true; unlockPtr(); showMenu('pause'); }
function resumeGame(){ if(!paused)return; paused=false; uiOpen=false; ov.hidden=true; try{gl.requestPointerLock();}catch(e){} }
el('menu').addEventListener('click',e=>{ const b=e.target.closest('button'); if(!b)return; const go=b.dataset.go; if(AC)beep(700,0.04,'square',0.03);
  if(go==='main')showMenu(paused?'pause':'main'); else if(go)showMenu(go);
  else if(b.id==='btnStart'){ reset(); try{localStorage.removeItem('lh-save');}catch(e){} startGame(true); }
  else if(b.id==='btnContinue')continueGame();
  else if(b.id==='btnResume')resumeGame();
  else if(b.id==='btnRestart'){ reset(); paused=false; uiOpen=false; ov.hidden=true; el('end').hidden=true; try{gl.requestPointerLock();}catch(e){} codec(CODEC.start); }
  else if(b.id==='btnQuit'){ reset(); paused=false; started=false; uiOpen=false; showMenu('main'); } });
el('menu').addEventListener('input',e=>{ if(e.target.closest('[data-pane="opt"]'))readOptUI(); });
el('menu').addEventListener('change',e=>{ if(e.target.closest('[data-pane="opt"]'))readOptUI(); });
showMenu('main');
