'use strict';
// ---------- RECONOCIMIENTO: prismáticos y marcado (B o clic derecho), distracción (Z) y modo reflejo.
// Son las tres piezas del GDD que faltaban para que «observar, planear y ejecutar» sea el bucle del juego.

// ----- PRISMÁTICOS Y MARCADO
let scopeKey=false, scopeBtn=false, scopeK=0, scopeAim=null;   // scopeK: 0..1, cuánto zoom hay ahora mismo
const SCOPE_FOV=18, BASE_FOV=70, MARK_T=0.45;
function scopeOn(){ return (scopeKey||scopeBtn)&&started&&!uiOpen&&!cut&&!S.over&&!S.lying&&!S.traveling&&!(S.smoke>0); }
function lookK(){ return camera.fov/BASE_FOV; }                 // con zoom el ratón gira más despacio
function camDir(){ const cp=Math.cos(pitch); return {x:-Math.sin(yaw)*cp,y:Math.sin(pitch),z:-Math.cos(yaw)*cp}; }
function scopeTick(dt){ const on=scopeOn(), goal=on?1:0, k0=scopeK; scopeK+=(goal-scopeK)*Math.min(1,dt*14); if(Math.abs(goal-scopeK)<0.01)scopeK=goal;
  if(scopeK!==k0){ camera.fov=BASE_FOV-(BASE_FOV-SCOPE_FOV)*scopeK; camera.updateProjectionMatrix(); }
  scopeAim=null; if(!on||scopeK<0.6||!S.guards)return;
  if(!S.flashSeen.scope){ S.flashSeen.scope=true; flash('PRISMÁTICOS','Deja la mira un instante sobre un guardia y queda marcado: lo verás a través de las paredes, con su distancia, aunque la alarma te deje sin radar.',7); }
  const P=S.p, d=camDir(), ey=S.camH||1.6; let best=null, ba=0.05;
  S.guards.forEach(g=>{ if(g.dead)return; const vx=g.x-P.x, vy=(g.down>0?0.3:1.3)-ey, vz=g.z-P.z, L=Math.hypot(vx,vy,vz)||1; if(L>70)return; const a=Math.acos(Math.max(-1,Math.min(1,(vx*d.x+vy*d.y+vz*d.z)/L))); if(a<ba&&los(P,g)){ ba=a; best=g; } });
  S.guards.forEach(g=>{ if(g!==best)g.markT=0; });
  if(best){ scopeAim=best; if(!best.marked){ best.markT=(best.markT||0)+dt; if(best.markT>=MARK_T)markGuard(best); } } }
function markGuard(g){ if(g.marked)return; g.marked=true; S.marks=(S.marks||0)+1; beep(1300,0.05,'square',0.04); setTimeout(()=>beep(1750,0.07,'square',0.04),70);
  if(!S.flashSeen.mark){ S.flashSeen.mark=true; flash('RECUERDO · EL PROGRAMA','Contar antes de entrar: cuántos, por dónde, cada cuánto. Lo haces sin pensarlo, como quien se ata los cordones. Alguien te examinó de esto.',7); } }

// ----- DISTRACCIÓN: un cargador vacío contra el suelo
let decoyCd=0; const decoysAir=[], pings=[];
const decoyGeo=new THREE.BoxGeometry(0.07,0.17,0.05);
function flowTo(tx,ty){ const fl=new Int16Array(COLS*ROWS).fill(-1); if(tx<0||ty<0||tx>=COLS||ty>=ROWS)return fl; const q=[tx+ty*COLS]; fl[q[0]]=0; let h=0;
  while(h<q.length){ const c=q[h++], cx=c%COLS, cy=(c/COLS)|0; for(const d of [[1,0],[-1,0],[0,1],[0,-1]]){ const nx=cx+d[0], ny=cy+d[1]; if(nx<0||ny<0||nx>=COLS||ny>=ROWS)continue; const n=nx+ny*COLS; if(fl[n]!==-1||solidT(nx,ny))continue; fl[n]=fl[c]+1; q.push(n); } } return fl; }
function flowStepIn(fl,ent){ const cx=tile(ent.x), cy=tile(ent.z); if(cx<0||cy<0||cx>=COLS||cy>=ROWS)return null; let best=null, bd=fl[cx+cy*COLS]; if(bd<0)return null;
  for(const d of [[1,0],[-1,0],[0,1],[0,-1]]){ const nx=cx+d[0], ny=cy+d[1]; if(nx<0||ny<0||nx>=COLS||ny>=ROWS)continue; const v=fl[nx+ny*COLS]; if(v>=0&&v<bd){ bd=v; best={x:wx(nx),z:wx(ny)}; } } return best; }
// dónde caería: mirando al suelo cae cerca, al horizonte a unos diez metros, hacia arriba hasta dieciséis; una pared lo para
function decoyLanding(){ const P=S.p, f=fwd(), range=Math.max(4,Math.min(16,10+pitch*12)); let lx=P.x, lz=P.z;
  for(let d=0.5;d<=range;d+=0.5){ const nx=P.x+f.x*d, nz=P.z+f.z*d; if(solidT(tile(nx),tile(nz)))break; lx=nx; lz=nz; } return {x:lx,z:lz}; }
function throwDecoy(){ if(!started||uiOpen||S.over||cut||S.lying||S.traveling||decoyCd>0)return false; const P=S.p;
  if(S.inCell){ flash('CARGADOR VACÍO','Aquí dentro no hay a quién engañar.',3); return false; }
  if(P.carry){ flash('CARGADOR VACÍO','Con un cuerpo a cuestas no tienes manos.',3); return false; }
  const to=decoyLanding(), d=Math.hypot(to.x-P.x,to.z-P.z); const m=new THREE.Mesh(decoyGeo,M.dark); m.position.set(P.x,1.4,P.z); scene.add(m);
  decoysAir.push({m,x0:P.x,z0:P.z,x1:to.x,z1:to.z,t:0,dur:0.3+d*0.045,from:{x:P.x,z:P.z}}); decoyCd=1.6; S.decoys=(S.decoys||0)+1; noiseBurst(0.06,0.03);
  if(!S.flashSeen.decoy){ S.flashSeen.decoy=true; flash('RECUERDO · EL PROGRAMA','Un cargador vacío contra el hormigón. El oído manda más que el ojo: van hacia el ruido y dejan libre lo que guardaban. Al que se lo hagas tres veces ya no mirará el ruido: mirará de dónde vino.',8); }
  return true; }
// ruido en (x,z): los guardias que lo oyen dejan la ronda y van a mirar, sin dar la alarma
function makeNoise(x,z,rad,from){ noiseBurst(0.05,0.22); beep(1900,0.05,'square',0.05,900); setTimeout(()=>beep(1500,0.04,'square',0.03,700),90); pings.push({x,z,t:0});
  let field=null, heard=0, wise=0;
  S.guards.forEach(g=>{ if(g.dead||g.down>0||g.held||g.state==='alert'||g.fixing)return; const d=Math.hypot(g.x-x,g.z-z); if(d>rad)return; heard++; g.decoy=(g.decoy||0)+1;
    const w=g.decoy>=3&&from; if(w)wise++; const t=w?{x:from.x,z:from.z}:{x,z}; g.state='suspect'; g.target=t; g.heardN=t; g.doubtT=0; g.searchT=6+Math.hypot(g.x-t.x,g.z-t.z)/2.6;
    if(w)g.heardF=flowTo(tile(t.x),tile(t.z)); else g.heardF=field||(field=flowTo(tile(x),tile(z))); });
  if(wise&&!S.flashSeen.wise){ S.flashSeen.wise=true; flash('YA NO PICA','A este se lo has hecho demasiadas veces. No mira el ruido: viene a ver quién lo tira.',5); }
  return heard; }
function decoyTick(dt){ if(decoyCd>0)decoyCd-=dt;
  for(let i=decoysAir.length-1;i>=0;i--){ const p=decoysAir[i]; p.t+=dt; const k=Math.min(1,p.t/p.dur); p.m.position.set(p.x0+(p.x1-p.x0)*k,1.4*(1-k)+0.05+3.2*k*(1-k),p.z0+(p.z1-p.z0)*k); p.m.rotation.x+=dt*14; p.m.rotation.z+=dt*9;
    if(k>=1){ scene.remove(p.m); decoysAir.splice(i,1); makeNoise(p.x1,p.z1,10,p.from); } }
  for(let i=pings.length-1;i>=0;i--){ pings[i].t+=dt; if(pings[i].t>1.6)pings.splice(i,1); } }

// ----- MODO REFLEJO: cuando un guardia va a dar la alarma, el tiempo se frena unos segundos. Una sola oportunidad.
const REFLEX_T=2.6, REFLEX_SLOW=0.2, REFLEX_CD=30;
function timeScale(){ return S.reflex?REFLEX_SLOW:1; }
function reflexTry(g,V){ if(S.reflex)return S.reflex.g===g; if(S.alertT>0||(S.reflexCd||0)>0||S.over||S.inCell||S.capturing)return false;
  S.reflex={g,t:REFLEX_T,V}; S.reflexN=(S.reflexN||0)+1; beep(520,1.1,'sine',0.07,60); noiseBurst(0.5,0.05);
  if(!S.flashSeen.reflex){ S.flashSeen.reflex=true; flash('REFLEJO','Te ha visto y aún no ha gritado. El cuerpo se te adelanta: tienes un instante para tumbarlo (F) o callarlo con el silenciador. Solo uno.',6); }
  return true; }
function reflexEnd(){ if(S.reflex){ S.reflex=null; S.reflexCd=REFLEX_CD; } }
// raw: segundos reales del fotograma; running: si el juego corre (sin diálogo, cinemática ni pausa)
function reflexTick(raw,running){ const R=S.reflex; if(!R)return; const g=R.g;
  if(g.dead||g.down>0||g.held){ reflexEnd(); g.susp=0; S.reflexSaved=(S.reflexSaved||0)+1; if(!uiOpen)flash('REFLEJO','Cae antes de coger aire. Nadie ha gritado.',4); return; }
  if(!running)return; R.t-=raw; if(R.t<=0){ const V=R.V; reflexEnd(); raiseAlarm(V); g.target={x:V.x,z:V.z}; } }

// ----- ciclo de vida
function reconReset(){ S.reflex=null; S.reflexCd=0; S.reflexN=0; S.reflexSaved=0; S.marks=0; S.decoys=0; reconZone(); }
function reconZone(){ decoysAir.forEach(p=>scene.remove(p.m)); decoysAir.length=0; pings.length=0; decoyCd=0; scopeAim=null; if(S.reflex)S.reflex=null; }
function reconUpdate(dt){ decoyTick(dt); if(S.reflexCd>0&&!S.reflex)S.reflexCd-=dt; }

// ----- HUD
function scr(x,y,z,w,h){ const v=new THREE.Vector3(x,y,z).project(camera); if(v.z>1||v.z<-1)return null; return {x:(v.x*0.5+0.5)*w,y:(-v.y*0.5+0.5)*h}; }
const ST_TXT={patrol:'DE RONDA',suspect:'SOSPECHA',search:'BUSCANDO',alert:'EN ALERTA'};
// máscara de los prismáticos: va debajo del resto del HUD
function reconHudUnder(w,h){ if(scopeK<=0.02)return; const cx=w/2, cy=h/2, R=Math.min(h*0.44,w*0.3), off=R*0.55;
  hctx.save(); hctx.fillStyle='rgba(2,5,4,'+(0.96*scopeK)+')'; hctx.fillRect(0,0,w,h); hctx.globalCompositeOperation='destination-out'; hctx.fillStyle='#000';
  hctx.beginPath(); hctx.arc(cx-off,cy,R,0,6.283); hctx.fill(); hctx.beginPath(); hctx.arc(cx+off,cy,R,0,6.283); hctx.fill(); hctx.restore();
  if(scopeK<0.6)return; hctx.save(); hctx.strokeStyle='rgba(120,230,170,.55)'; hctx.lineWidth=1; hctx.beginPath();
  hctx.moveTo(cx-off-R+12,cy); hctx.lineTo(cx-26,cy); hctx.moveTo(cx+26,cy); hctx.lineTo(cx+off+R-12,cy); hctx.moveTo(cx,cy-R+16); hctx.lineTo(cx,cy-26); hctx.moveTo(cx,cy+26); hctx.lineTo(cx,cy+R-16);
  for(let i=-4;i<=4;i++){ if(!i)continue; hctx.moveTo(cx+i*34,cy-(i%2?4:7)); hctx.lineTo(cx+i*34,cy+(i%2?4:7)); } hctx.stroke();
  hctx.font='8px "Press Start 2P",monospace'; hctx.textAlign='center'; hctx.fillStyle='#78e6aa'; hctx.fillText('PRISMÁTICOS ×4',cx,cy-R+34);
  const g=scopeAim; if(g){ const d=Math.round(dist(g,S.p)); hctx.fillStyle=g.state==='alert'?'#e0483a':'#ffe066'; hctx.fillText((g.name||'GUARDIA').toUpperCase()+' · '+d+' m',cx,cy+58); hctx.fillStyle='#78e6aa'; hctx.fillText(g.down>0?'DORMIDO':(ST_TXT[g.state]||''),cx,cy+74);
    if(g.marked){ hctx.fillStyle='#ffb040'; hctx.fillText('▼ MARCADO',cx,cy+92); } else { hctx.fillStyle='rgba(120,230,170,.25)'; hctx.fillRect(cx-40,cy+86,80,4); hctx.fillStyle='#78e6aa'; hctx.fillRect(cx-40,cy+86,80*Math.min(1,(g.markT||0)/MARK_T),4); } }
  else { hctx.fillStyle='rgba(120,230,170,.7)'; hctx.fillText('DEJA LA MIRA SOBRE UN GUARDIA PARA MARCARLO',cx,cy+R-30); }
  hctx.restore(); }
// marcas a través de las paredes, eco del ruido en el radar y aviso de reflejo: van encima
function reconHud(w,h){ const P=S.p; hctx.save(); hctx.font='7px "Press Start 2P",monospace'; hctx.textAlign='center';
  S.guards.forEach(g=>{ if(!g.marked||g.dead)return; const s=scr(g.x,g.down>0?0.9:2.2,g.z,w,h); if(!s||s.x<-20||s.x>w+20||s.y<-20||s.y>h+20)return; const col=g.down>0?'#7d948a':g.state==='alert'?'#e0483a':g.state==='patrol'?'#ffb040':'#ffe066';
    hctx.fillStyle=col; hctx.strokeStyle='rgba(0,0,0,.8)'; hctx.lineWidth=2; hctx.beginPath(); hctx.moveTo(s.x-6,s.y-9); hctx.lineTo(s.x+6,s.y-9); hctx.lineTo(s.x,s.y); hctx.closePath(); hctx.stroke(); hctx.fill();
    hctx.fillText(Math.round(dist(g,P))+' m',s.x,s.y-14); });
  if(S.reflex){ const k=Math.max(0,S.reflex.t/REFLEX_T), cx=w/2; const gr=hctx.createRadialGradient(cx,h/2,h*0.25,cx,h/2,h*0.75); gr.addColorStop(0,'rgba(79,185,214,0)'); gr.addColorStop(1,'rgba(79,185,214,.42)'); hctx.fillStyle=gr; hctx.fillRect(0,0,w,h);
    hctx.fillStyle='#bfefff'; hctx.font='14px "Press Start 2P",monospace'; hctx.fillText('REFLEJO',cx,h*0.24); hctx.fillStyle='rgba(191,239,255,.25)'; hctx.fillRect(cx-90,h*0.24+12,180,5); hctx.fillStyle='#bfefff'; hctx.fillRect(cx-90,h*0.24+12,180*k,5);
    const s=scr(S.reflex.g.x,2.5,S.reflex.g.z,w,h); if(s){ hctx.font='22px "Press Start 2P",monospace'; hctx.fillStyle='#ff4a3a'; hctx.fillText('!',s.x,s.y); } }
  hctx.restore(); }
function reconRadar(ox,oy,sc){ pings.forEach(p=>{ const k=p.t/1.6; hctx.strokeStyle='rgba(120,230,170,'+(1-k)+')'; hctx.lineWidth=1.5; hctx.beginPath(); hctx.arc(ox+p.x/T*sc,oy+p.z/T*sc,2+k*10/T*sc,0,6.283); hctx.stroke(); });
  S.guards.forEach(g=>{ if(!g.marked||g.dead||g.down>0)return; hctx.strokeStyle='#ffb040'; hctx.lineWidth=1; hctx.strokeRect(ox+g.x/T*sc-4,oy+g.z/T*sc-4,8,8); }); }
