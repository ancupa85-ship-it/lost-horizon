'use strict';
// ---------- UI
const el=id=>document.getElementById(id);
const promptEl=el('prompt'), flashEl=el('flash'), dlg=el('dlg'), noteEl=el('note'), ov=el('ov'), app=el('app');
let flashT=0; function flash(label,text,secs){ flashEl.innerHTML='<small>'+label+'</small>'+text; flashEl.hidden=false; flashT=secs||6; }
function addClue(k){ if(!CLUES[k]||S.clues.includes(k))return; S.clues.push(k); renderNote(); beep(1200,0.08,'sine',0.04); el('hClue').textContent=S.clues.length+'/'+Object.keys(CLUES).length; flash('PISTA NUEVA · CUADERNO (Tab)',CLUES[k],7); }
// cadena de objetivos de la misión 1: texto, paso y casilla destino (para el radar y la brújula)
function objective(){ const P=S.p, C=S.c; const file=!!(P.file||(C&&C.file));
  if(S.inCell){ if(S.cellKey)return {step:0,text:'ABRE LA REJA CON LA LLAVE',x:31,y:12}; if(S.vidal&&S.vidal.gone)return {step:0,text:'BUSCA OTRA SALIDA DE LA CELDA',x:30,y:13}; return {step:0,text:'HABLA CON HALLORAN Y CONVENCE A VIDAL',x:31,y:12}; }
  if(file)return {step:6,text:'SAL POR LA PUERTA SURESTE',x:34,y:26};
  if(W.vaultOpen)return {step:5,text:'COGE EL EXPEDIENTE LH-07 DEL ARCHIVADOR',x:8,y:17};
  if(W.officeOpen){ const hasCode=S.clues.some(k=>['c130','peris','vulgata','roma','hallo','c1983'].includes(k)); return {step:4,text:hasCode?'ABRE EL ARCHIVO: TECLADO, 4 CIFRAS (CRUZA LAS PISTAS)':'AVERIGUA LA CLAVE DEL ARCHIVO: LEE EL ESCRITORIO, INTERROGA',x:hasCode?11:3,y:17}; }
  if(P.key||(C&&C.key))return {step:3,text:'ABRE EL DESPACHO DE ALARCÓN (EDIFICIO OESTE)',x:4,y:15};
  const ib=S.guards.find(g=>g.hasKey); if(ib&&!ib.dead)return {step:2,text:'CONSIGUE LA LLAVE DEL DESPACHO: EL CABO IBARRA LA LLEVA',gx:ib.x,gz:ib.z,x:Math.floor(ib.x/T),y:Math.floor(ib.z/T)};
  return {step:2,text:'SIN LLAVE: VUELA LA CERRADURA DEL DESPACHO (1 BALA, RUIDO)',x:4,y:15}; }
// fuera de la base, el objetivo apunta a la salida que lleva de vuelta
function objectiveHere(){ const o=objective(); if(!o||!ZONE||ZONE.id==='base'||!ZONE.exitTo)return o; const ex=ZONE.exitTo.base; if(!ex)return o; return {step:o.step,text:'SUBE A LA BASE · '+o.text,x:ex[0],y:ex[1]}; }
let lastObj=''; function updObj(){ const o=objectiveHere(); const t=(o.step?'OBJETIVO '+o.step+'/6: ':'OBJETIVO: ')+o.text; if(t!==lastObj){ lastObj=t; el('hObj').textContent=t; } return o; }
function renderNote(){ el('noteList').innerHTML=S.clues.length?S.clues.map(k=>'<li>'+CLUES[k]+'</li>').join(''):'<li class="e">Nada todavía. Lee, escucha, aprieta.</li>'; }
let dlgOpts=[];
function openDialog(title,html,opts){ uiOpen=true; unlockPtr(); el('dlgTitle').textContent=title; el('dlgTxt').innerHTML=html; dlgOpts=opts; const box=el('dlgOpts'); box.innerHTML=''; box.className='opts';
  opts.forEach((o,i)=>{ const b=document.createElement('button'); b.innerHTML='<span class="n">'+(i+1)+'</span>'+o.t; if(o.cls)b.classList.add(o.cls); b.onclick=()=>o.f(); box.appendChild(b); }); dlg.hidden=false; }
function closeDialog(){ uiOpen=false; dlg.hidden=true; dlgOpts=[]; keypadMode=false; }
function updHud(){ el('hClue').textContent=(S.clues?S.clues.length:0)+'/'+Object.keys(CLUES).length; const st=el('hState'); st.textContent=S.base.toUpperCase(); st.className='st-'+S.base; el('hHp').textContent='♥'.repeat(Math.max(0,S.p.hp))+'·'.repeat(Math.max(0,5-Math.max(0,S.p.hp))); el('hAmmo').textContent=S.p.ammo+(S.silencer?' · SIL':''); const hd=el('hDis'); if(hd)hd.hidden=!S.p.disguise; }
