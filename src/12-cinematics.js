'use strict';
// ---------- CINEMÁTICAS (cámara guiada, bandas, títulos)
const titleEl=el('title'), skipEl=el('skip'), fadeEl=el('fade');
function lerp(a,b,t){return a+(b-a)*t;} function ease(t){return t<0.5?2*t*t:1-Math.pow(-2*t+2,2)/2;}
function startCut(shots,done){ cut={shots,i:0,t:0,done}; app.classList.add('cine'); skipEl.hidden=false; el('top').style.opacity=0; promptEl.hidden=true; arms.visible=false; applyShot(); }
function applyShot(){ const s=cut.shots[cut.i]; titleEl.hidden=!s.title; if(s.title)titleEl.innerHTML=s.title; fadeEl.style.opacity=s.fade?1:0; }
function cutTick(dt){ if(!cut)return; cut.t+=dt; const s=cut.shots[cut.i]; const k=ease(Math.min(1,cut.t/s.dur));
  if(s.from){ camera.position.set(lerp(s.from[0],s.to[0],k),lerp(s.from[1],s.to[1],k),lerp(s.from[2],s.to[2],k)); const la=s.look2?[lerp(s.look[0],s.look2[0],k),lerp(s.look[1],s.look2[1],k),lerp(s.look[2],s.look2[2],k)]:s.look; camera.lookAt(la[0],la[1],la[2]); }
  if(cut.t>=s.dur){ cut.i++; cut.t=0; if(cut.i>=cut.shots.length)endCut(); else applyShot(); } }
function cutSkip(){ if(!cut)return; endCut(); }
function endCut(){ const d=cut.done; cut=null; app.classList.remove('cine'); skipEl.hidden=true; titleEl.hidden=true; fadeEl.style.opacity=0; el('top').style.opacity=1; arms.visible=!third; camera.rotation.set(pitch,yaw,0); if(d)d(); }
function intro(){ const px=wx(start.x),pz=wx(start.y);
  startCut([
   {dur:4.5,fade:true,title:'<span class="s">DOCUMENTO DESCLASIFICADO · 2026</span>LAURA SOROLLA, PERIODISTA:<br>«LO QUE SIGUE LO RECONSTRUÍ A PARTIR DEL EXPEDIENTE LH-07.»'},
   {dur:7,from:[wx(18),26,wx(30)],to:[wx(14),14,wx(18)],look:[wx(14),0,wx(12)],title:'<span class="s">TARSIS · 21 DE NOVIEMBRE DE 1983 · 02:10</span>CENTRO DE COMUNICACIONES Y ARCHIVO<span class="big">PROJECT LOST HORIZON</span>'},
   {dur:5,from:[wx(8),9,wx(10)],to:[px+6,3.5,pz+4],look:[px,1,pz],title:'<span class="s">ANDREW CUTTLAS · SUJETO LH-07</span>MISIÓN 1<span class="big">DE PROFUNDIS</span>'},
   {dur:3,from:[px+6,3.5,pz+4],to:[px,1.6,pz],look:[px+8,1.4,pz],look2:[px+8,1.6,pz]},
  ],()=>{ codec(CODEC.start); }); }
function intro2(){ const px=wx(start.x),pz=wx(start.y);
  startCut([
   {dur:4,fade:true,title:'<span class="s">DOCUMENTO DESCLASIFICADO · 2026</span>LAURA SOROLLA, PERIODISTA:<br>«DE LO QUE PASÓ DEBAJO NO HAY EXPEDIENTE. HAY UNA LISTA.»'},
   {dur:6,from:[px,2.2,pz+22],to:[px,1.8,pz+6],look:[px,1.2,pz],title:'<span class="s">TARSIS · 21 DE NOVIEMBRE DE 1983 · 03:10</span>EXCAVACIÓN · LABORATORIO DEL PROGRAMA<span class="big">PROJECT LOST HORIZON</span>'},
   {dur:4.5,from:[px+5,3,pz+3],to:[px+1.5,1.7,pz+1.5],look:[px,1.3,pz],title:'<span class="s">ANDREW CUTTLAS · SUJETO LH-07</span>MISIÓN 2<span class="big">DESCENSO</span>'},
   {dur:2.5,from:[px+1.5,1.7,pz+1.5],to:[px,1.6,pz],look:[px,1.4,pz+8],look2:[px,1.6,pz+8]},
  ],()=>{ codec(CODEC.m2start); }); }
function intro3(){ const px=wx(start.x),pz=wx(start.y);
  startCut([
   {dur:4,fade:true,title:'<span class="s">DOCUMENTO DESCLASIFICADO · 2026</span>LAURA SOROLLA, PERIODISTA:<br>«DE LA TORRE HAY CUATRO VERSIONES. NINGUNA ES LA MISMA DOS VECES.»'},
   {dur:6,from:[wx(13),22,wx(26)],to:[wx(13),9,wx(12)],look:[wx(13),4,wx(4)],title:'<span class="s">TARSIS · 21 DE NOVIEMBRE DE 1983 · 03:40</span>CENTRO DE COMUNICACIONES · LA TORRE<span class="big">PROJECT LOST HORIZON</span>'},
   {dur:4.5,from:[px+6,4,pz-4],to:[px+1.5,1.7,pz-1.5],look:[px,1.3,pz],title:'<span class="s">ANDREW CUTTLAS · SUJETO LH-07</span>MISIÓN 3<span class="big">TARSIS</span>'},
   {dur:2.5,from:[px+1.5,1.7,pz-1.5],to:[px,1.6,pz],look:[px+6,1.4,pz-6],look2:[px+6,1.6,pz-6]},
  ],()=>{ codec(CODEC.m3start); }); }
function outro3(kind){ const P=S.p; unlockPtr(); const t=kind==='radio'?'LA RADIO · '+clockStr():kind==='bote'?'EL EMBARCADERO · '+clockStr():'LA CARRETERA DE ROTA · '+clockStr();
  startCut([
   {dur:5,from:[P.x-3,1.6,P.z+3],to:[P.x-2,3,P.z+2],look:[P.x,1.2,P.z],title:'<span class="s">'+t+'</span>FIN DE LA MISIÓN 3'},
   {dur:3.5,from:[P.x-2,3,P.z+2],to:[P.x-6,14,P.z-6],look:[P.x,1,P.z]},
  ],()=>showEnd(true)); }
function outro2(){ const P=S.p; unlockPtr();
  startCut([
   {dur:5,from:[P.x-3,1.6,P.z+3],to:[P.x-2,2.6,P.z+2],look:[P.x,1.2,P.z],title:'<span class="s">MONTACARGAS · '+clockStr()+'</span>FIN DE LA MISIÓN 2'},
   {dur:3.5,from:[P.x-2,2.6,P.z+2],to:[P.x,2.9,P.z],look:[P.x,0.5,P.z],look2:[P.x,-4,P.z]},
  ],()=>showEnd(true)); }
function outro(){ const P=S.p; unlockPtr();
  startCut([
   {dur:5,from:[P.x,1.6,P.z],to:[P.x-6,9,P.z-6],look:[P.x,1,P.z],title:'<span class="s">SALIDA SURESTE · 03:0'+(((S.t/60)|0)%10)+'</span>FIN DE LA MISIÓN 1'},
   {dur:3,from:[P.x-6,9,P.z-6],to:[P.x-6,22,P.z-6],look:[P.x,1,P.z]},
  ],()=>showEnd(true)); }
