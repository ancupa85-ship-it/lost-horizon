'use strict';
// ---------- EQUIPO: la compañera (Roig) sigue, se esconde y dispara sola; X intercambia el control
function entHidden(c){ return (c===S.p&&S.spotlit)?false:(shadowT(tile(c.x),tile(c.z))&&c.crouch); }
function downEnt(c,secs){ c.down=secs; c.hp=0; c.moving=false; c.fig.g.rotation.z=Math.PI/2; c.fig.g.position.y=0.26; flash(c.name+' HERIDA','Cae. Tardará un rato en levantarse; hasta entonces no la puedes controlar.',5); beep(90,0.4,'sawtooth',0.08); }
function teamThreat(C){ let best=null,bd=1e9;
  S.guards.forEach(g=>{ if(g.dead||g.down>0||g.held)return; const d=dist(g,C); if(d>T*9)return; const hostile=g.state==='alert'||(g.state==='search'&&d<T*1.6&&S.base!=='calma'); if(!hostile)return; if(!los(C,g))return; if(d<bd){bd=d;best=g;} });
  S.dogs.forEach(d=>{ if(d.dead)return; const dd=dist(d,C); if(dd>T*8||!los(C,d))return; if(dd<bd){bd=dd;best=d; best.isDog=true;} });
  return best; }
function teamShoot(C,t){ C.ammo--; C.shotT=1.4; S.muzzleC=0.06; beep(420,0.05,'square',0.03,200); noiseBurst(0.05,0.06); const dd=dist(C,t)||1; C.fx=(t.x-C.x)/dd; C.fz=(t.z-C.z)/dd;
  if(Math.random()<0.7){ if(t.isDog){ t.dead=true; S.dogKills++; t.fig.g.rotation.z=Math.PI/2; t.fig.g.position.y=0.15; bark(); } else { knock(t,false); S.teamKO++; C.ko=(C.ko||0)+1; } }
  if(!S.flashSeen.team){ S.flashSeen.team=true; flash(C.name,'Dispara con silenciador: duerme, no mata. Cuenta sus balas: no tiene más que las que lleva.',5); } }
function updateTeam(dt){ const C=S.c, P=S.p; if(!C)return;
  if(C.hurtT>0)C.hurtT-=dt;
  if(C.down>0){ C.down-=dt; C.fig.g.position.set(C.x,0.26,C.z); if(C.down<=0){ C.hp=2; C.fig.g.rotation.z=0; C.fig.g.position.y=0; flash(C.name,'Se levanta. Dos corazones y mala cara.',3); } return; }
  const threat=teamThreat(C); const d=dist(C,P);
  if(threat){ C.shotT-=dt; const td=dist(C,threat);
    if(C.ammo>0){ if(C.shotT<=0)teamShoot(C,threat); }
    else if(td<1.5&&C.shotT<=0){ C.shotT=1.2; if(threat.isDog){ threat.stun=5; threat.biteT=1; } else if(Math.random()<0.8){ knock(threat,false); S.teamKO++; } beep(220,0.08,'square',0.06); } }
  // movimiento: seguir al controlado, buscar sombra si él se esconde, aguantar posición si hay amenaza cerca
  C.crouch=P.crouch; let tgt=null; const hold=threat&&d<T*6;
  if(!hold){ if(d>2.6){ if(los(C,P))tgt={x:P.x,z:P.z}; else { S.flowC=(S.flowC||0)-dt; if(!flow||S.flowC<=0){ buildFlow(); S.flowC=0.5; } tgt=flowStep(C)||{x:P.x,z:P.z}; } }
    else if(entHidden(P)&&!entHidden(C)){ let best=null,bd=1e9; const cx=tile(C.x),cz=tile(C.z); for(let y=-2;y<=2;y++)for(let x=-2;x<=2;x++){ const tx=cx+x,tz=cz+y; if(solidT(tx,tz)||!shadowT(tx,tz))continue; const dd=Math.hypot(x,y); if(dd<bd){bd=dd;best={x:wx(tx),z:wx(tz)};} } if(best&&Math.hypot(best.x-C.x,best.z-C.z)>0.2)tgt=best; } }
  C.moving=false;
  if(tgt){ const dx=tgt.x-C.x,dz=tgt.z-C.z,L=Math.hypot(dx,dz)||1; const sp=(C.crouch?2.4:(P.run&&d>4?6.8:4.0))*dt; const ox=C.x,oz=C.z; move(C,dx/L*Math.min(sp,L),dz/L*Math.min(sp,L),0.36); C.moving=Math.abs(C.x-ox)+Math.abs(C.z-oz)>0.003; if(C.moving){ C.fx=dx/L; C.fz=dz/L; } }
  else if(!threat&&d<5){ const dd=d||1; C.fx=(P.x-C.x)/dd; C.fz=(P.z-C.z)/dd; }
  const f=C.fig; f.g.visible=true; f.g.position.set(C.x,0,C.z); f.g.rotation.y=Math.atan2(C.fx,C.fz); f.g.scale.y=C.crouch?0.7:1; animFig(f,C.moving,dt,!!threat); if(threat)f.armR.rotation.x=-1.4; }
function swapChar(){ if(!started||uiOpen||S.over||cut||!S.c)return; if(S.c.down>0){ flash(S.c.name,'Está herida en el suelo. Hasta que se levante no puedes cambiar.',3); return; }
  const a=S.p, b=S.c; b.key=a.key; b.file=a.file; a.key=false; a.file=false; if(a.carry){a.carry.carried=false;a.carry=null;} b.carry=null; a.moving=false; a.run=false;
  S.p=b; S.c=a; S.swaps++; S.smoke=0; yaw=Math.atan2(-b.fx,-b.fz); pitch=0; S.camH=undefined; S.swapT=0.4; beep(1500,0.05,'sine',0.04); setTimeout(()=>beep(1100,0.08,'sine',0.04),70);
  updHud(); if(!S.flashSeen.swap){ S.flashSeen.swap=true; flash('CAMBIO','Ahora controlas a '+b.name+'. '+a.name+' te sigue y dispara si os ven. X para volver.',5); } }
