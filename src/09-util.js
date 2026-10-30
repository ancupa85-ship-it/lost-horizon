'use strict';
// ---------- UTILIDADES
function fwd(){ return {x:-Math.sin(yaw),z:-Math.cos(yaw)}; }
function dist(a,b){ return Math.hypot(a.x-b.x,a.z-b.z); }
function los(a,b){ let x0=tile(a.x),y0=tile(a.z),x1=tile(b.x),y1=tile(b.z); const sx0=x0,sy0=y0; const dx=Math.abs(x1-x0),dy=-Math.abs(y1-y0),sx=x0<x1?1:-1,sy=y0<y1?1:-1; let err=dx+dy;
  for(let i=0;i<80;i++){ if(x0===x1&&y0===y1)return true; if(!(x0===sx0&&y0===sy0)&&sightT(x0,y0))return false; const e2=2*err; if(e2>=dy){err+=dy;x0+=sx;} if(e2<=dx){err+=dx;y0+=sy;} } return false; }
function move(ent,dx,dz,r){ const ok=(nx,nz)=>{ const pts=[[nx-r,nz-r],[nx+r,nz-r],[nx-r,nz+r],[nx+r,nz+r]]; return !pts.some(p=>solidT(tile(p[0]),tile(p[1]))); }; if(dx&&ok(ent.x+dx,ent.z))ent.x+=dx; if(dz&&ok(ent.x,ent.z+dz))ent.z+=dz; }
function sees(g,p,range,half){ const d=dist(g,p); if(d>range)return false; const ang=Math.atan2(p.z-g.z,p.x-g.x),fa=Math.atan2(g.fz,g.fx); let da=Math.abs(ang-fa); if(da>Math.PI)da=2*Math.PI-da; if(da>half&&(d>T*1.1||(da>Math.PI*0.5&&!p.run)))return false; return los(g,p); } // de cerca nota a quien tiene delante o al lado; por la espalda solo si corre
function playerHidden(){ const P=S.p; return S.spotlit?false:(shadowT(tile(P.x),tile(P.z))&&P.crouch); }
const REFDEF={name:'Refuerzo',role:'puerta',nerve:3,loyal:2,wps:[[26,26],[33,26],[33,23],[26,23]],q:{}};
function clockStr(){ const mins=10+Math.floor((S.t||0)/60); return '0'+(2+Math.floor(mins/60))+':'+String(mins%60).padStart(2,'0'); }
function setBase(st){ if(S.base===st)return; const o={calma:0,sospecha:1,cierre:2}; if(o[st]<o[S.base])return; S.base=st; updHud();
  if(st==='cierre'&&!S.reinforced){ S.reinforced=true; W.yardDoorClosed=true; if(S.zone==='base'){ if(dynamicDoors.yard)dynamicDoors.yard.visible=true; S.guards.push(mkGuard(REFDEF,true)); } else S.refPending=true; flash('BASE EN CIERRE','Se cierra la puerta entre los patios. Un refuerzo cubre la salida. Ya solo se sale por abajo o por la fuerza.',7); beep(110,0.8,'sawtooth',0.08); } }
const ALARM_D=7.5, DISG_D=3; // metros: de más lejos dudan y se acercan; con uniforme solo te calan a menos de 3
function raiseAlarm(where){ [S.p,S.c].forEach(e=>{ if(e&&e.disguise){ setDisguise(e,false); flash('TE HAN CALADO','El uniforme ya no engaña a nadie. Vuelves a ser el intruso.',5); } });
  if(S.alertT<=0){S.alarms++; alertJingle(); S.freeze=0.5; app.classList.add('cine'); setTimeout(()=>{ if(!cut)app.classList.remove('cine'); },900);
    if(!S.codecSeen.alarm){ S.codecSeen.alarm=true; setTimeout(()=>{ if(!S.over&&!uiOpen)codec(CODEC.alarm); },1200); } }
  S.alertT=10; setBase(S.alarms>=2?'cierre':'sospecha'); S.guards.forEach(g=>{ if(!g.dead&&g.down<=0&&!g.held){g.state='alert';g.target={x:where.x,z:where.z};g.fixing=false;} }); }
