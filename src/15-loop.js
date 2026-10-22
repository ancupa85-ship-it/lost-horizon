'use strict';
// ---------- BUCLE
let last=0;
function loop(ts){ requestAnimationFrame(loop); const dt=Math.min(0.05,(ts-last)/1000||0.016); last=ts; if(started&&!uiOpen&&!S.over&&!cut)update(dt); else if(started){ S.t+=dt; } cutTick(dt); codecTick(dt); rainUpdate(dt); render(dt); }
function update(dt){ const P=S.p; S.t+=dt;
  S.spotlit=false; spots.forEach(s=>{ const a=S.t*0.35+s.ph; const tx=s.cx+Math.cos(a)*s.rad, tz=s.cz+Math.sin(a)*s.rad; s.tg.position.set(tx,0,tz); if(W.power&&Math.hypot(tx-P.x,tz-P.z)<2.4&&!interior(tile(P.x),tile(P.z)))S.spotlit=true; });
  if(S.freeze>0){ S.freeze-=dt; return; }
  // reloj de misión y perrera
  { const mins=10+Math.floor(S.t/60); el('hClock').textContent='0'+(2+Math.floor(mins/60))+':'+String(mins%60).padStart(2,'0'); }
  if(!S.dogsDone&&!S.inCell){ if(S.t>420&&!S.codecSeen.warn){S.codecSeen.warn=true; codec(CODEC.warn); return;} if(S.t>540&&!S.dogs.length)releaseDogs(); }
  flowT-=dt; if(flowT<=0&&(S.dogs.some(d=>!d.dead)||S.guards.some(g=>g.state==='alert'))){ flowT=0.3; buildFlow(); }
  let dx=0,dz=0; const f=fwd(); const r={x:Math.cos(yaw),z:-Math.sin(yaw)};
  if(keys.w||keys.ArrowUp){dx+=f.x;dz+=f.z;} if(keys.s||keys.ArrowDown){dx-=f.x;dz-=f.z;} if(keys.d||keys.ArrowRight){dx+=r.x;dz+=r.z;} if(keys.a||keys.ArrowLeft){dx-=r.x;dz-=r.z;}
  P.run=!!keys.Shift&&!P.crouch&&!P.carry; const spd=(P.crouch?2.2:P.run?7.5:4.2)*(P.carry?0.6:1)*dt; const l=Math.hypot(dx,dz); P.moving=l>0;
  if(l>0){ move(P,dx/l*spd,dz/l*spd,0.38); S.bob=(S.bob||0)+dt*(P.run?14:9); S.stepT+=dt; const per=P.crouch?0.6:P.run?0.3:0.45; if(S.stepT>per){S.stepT=0; noiseBurst(0.04,P.crouch?0.012:P.run?0.07:0.035);} }
  // fumar
  if(S.smoke>0){ if(P.moving){ S.smoke=0; flash('TABACO','Lo apagas con la bota. Medio cigarro perdido.',3); } else { S.smoke-=dt; S.puffT=(S.puffT||0)+dt; if(S.puffT>0.5){ S.puffT=0; const pf=puffs.find(q=>q.t>=2.5)||puffs[0]; pf.t=0; pf.sp.position.set(P.x+f.x*0.35,S.camH-0.1,P.z+f.z*0.35); } if(Math.floor(S.smoke*2)!==Math.floor((S.smoke+dt)*2)&&Math.floor(S.smoke)%2===0)noiseBurst(0.3,0.015); if(S.smoke<=0){ S.cigs--; el('hCig').textContent=S.cigs; P.hp=Math.min(5,P.hp+2); updHud(); flash('TABACO','Respiras. Dos corazones, y el patio huele a ti.',4); } } }
  puffs.forEach(q=>{ if(q.t<2.5){ q.t+=dt; q.sp.position.y+=dt*0.35; q.sp.scale.setScalar(0.3+q.t*0.5); q.sp.material.opacity=0.5*(1-q.t/2.5); } else q.sp.material.opacity=0; });
  // perros
  S.dogs.forEach(d=>{ if(d.dead)return; if(d.stun>0){ d.stun-=dt; d.fig.g.rotation.z=Math.PI/2; d.fig.g.position.set(d.x,0.2,d.z); return; } d.fig.g.rotation.z=0;
    let tgt=null; const dd=dist(d,P); if(dd<T*3&&los(d,P))tgt={x:P.x,z:P.z}; else tgt=flowStep(d)||{x:P.x,z:P.z};
    const dx2=tgt.x-d.x,dz2=tgt.z-d.z,L2=Math.hypot(dx2,dz2)||1;
    if(dd>1.0){ const ox=d.x,oz=d.z; move(d,dx2/L2*6.2*dt,dz2/L2*6.2*dt,0.3); if(Math.abs(d.x-ox)+Math.abs(d.z-oz)<0.005){ move(d,(Math.random()-0.5)*0.4,(Math.random()-0.5)*0.4,0.3); } d.fx=dx2/L2; d.fz=dz2/L2; d.fig.phase+=dt*16; }
    else { d.biteT-=dt; if(d.biteT<=0){ d.biteT=1.0; bark(); P.hp--; P.hurtT=0.5; updHud(); if(P.hp<=0){ defeat('dogs'); } } }
    if(Math.random()<dt*0.25)bark();
    d.fig.g.position.set(d.x,0,d.z); d.fig.g.rotation.y=Math.atan2(d.fx,d.fz); animDog(d.fig,dt,dd>1.0); });
  if(S.vidal.cool>0)S.vidal.cool-=dt;
  if(P.hurtT>0)P.hurtT-=dt; if(P.carry){P.carry.x=P.x+f.x*0.6;P.carry.z=P.z+f.z*0.6;}
  const hidden=playerHidden()&&S.smoke<=0;
  if(hidden&&!S.flashSeen.shadow){S.flashSeen.shadow=true; flash('RECUERDO','Alguien te enseñó a quedarte quieto en la oscuridad. No recuerdas su cara. Recuerdas que no te dejó respirar hasta que pasó la ronda.',6);}
  S.bodies.forEach(b=>{ b.hidden=shadowT(tile(b.x),tile(b.z)); b.g.fig.g.position.x=b.x; b.g.fig.g.position.z=b.z; if(!b.dead){b.g.x=b.x;b.g.z=b.z;} });
  if(!W.power){ S.fixTimer-=dt; if(S.fixTimer<=0&&!S.guards.some(g=>g.fixing)){ let best=null,bd=1e9; S.guards.forEach(g=>{ if(g.dead||g.down>0||g.held||g.state==='alert')return; const d=Math.hypot(g.x-wx(21),g.z-wx(8)); if(d<bd){bd=d;best=g;} }); if(best){best.fixing=true;best.state='search';best.target={x:wx(22),z:wx(9)};best.searchT=60;} } }
  if(S.alertT>0)S.alertT-=dt; siren(dt);
  S.guards.forEach(g=>{ if(g.fall!==undefined&&g.fall<1){ g.fall=Math.min(1,g.fall+dt*3.5); const k=g.fall; g.fig.g.rotation.z=Math.PI/2*k; g.fig.g.position.y=0.26*k; }
    if(g.dead||g.held)return;
    if(g.down>0){ g.down-=dt; if(g.down<=0){ g.fall=undefined; const b=S.bodies.find(b=>b.g===g); if(b){ if(b.carried)P.carry=null; S.bodies.splice(S.bodies.indexOf(b),1);} g.fig.g.rotation.z=0; g.fig.g.position.y=0; g.state='search'; g.searchT=8; g.target={x:P.x,z:P.z}; setBase('sospecha'); flash('AVISO','Un guardia derribado despierta y da la voz de sospecha.',4);} return; }
    let visRange=hidden?T*1.3:S.spotlit?T*13:!W.power?T*3:P.crouch?T*5.5:T*8; if(S.smoke>0)visRange=Math.max(visRange,T*9); const half=Math.PI/180*42;
    const C=S.c; const cAlive=C&&C.down<=0; const visC=cAlive?(entHidden(C)?T*1.3:!W.power?T*3:C.crouch?T*5.5:T*8):0;
    const seeP0=sees(g,P,visRange,half), seeC=cAlive&&sees(g,C,visC,half); const seeP=seeP0||seeC; const V=(seeP0&&seeC)?(dist(g,P)<=dist(g,C)?P:C):(seeP0?P:C);
    if(seeP){ g.susp+=dt*(dist(g,V)<T*3?3.5:1.4)*(P.run?1.5:1); if(g.susp>=1){ raiseAlarm(V); g.target={x:V.x,z:V.z}; } else if(g.state==='patrol'){ g.state='suspect'; g.target={x:V.x,z:V.z}; g.searchT=4; } }
    else g.susp=Math.max(0,g.susp-dt*0.7);
    if(P.run&&!seeP&&dist(g,P)<T*4&&g.state==='patrol'){ g.state='suspect'; g.target={x:P.x,z:P.z}; g.searchT=3; }
    if(g.state!=='alert'){ const b=S.bodies.find(b=>!b.hidden&&!b.carried&&sees(g,b,T*6,half)); if(b){ if(b.dead)raiseAlarm(b); else { g.state='search'; g.target={x:b.x,z:b.z}; g.searchT=6; setBase('sospecha'); } } }
    let tx,tz,sp;
    if(g.state==='alert'){ if(S.alertT<=0){g.state='search';g.searchT=9;} sp=4.2; if(seeP)g.target={x:V.x,z:V.z}; tx=g.target.x;tz=g.target.z; if(!seeP){ const fs=flowStep(g); if(fs){tx=fs.x;tz=fs.z;} }
      if(seeP&&dist(g,V)<T*9){ g.shotT-=dt; if(g.shotT<=0){ g.shotT=1.3; beep(60,0.1,'square',0.1); noiseBurst(0.12,0.25); const hitP=0.55*(V.crouch?0.7:1)*(V.moving?0.8:1); if(Math.random()<hitP){ V.hp--; V.hurtT=0.5; updHud(); if(V.hp<=0){ if(V===P)defeat('guards'); else downEnt(V,40); } } } } }
    else if(g.state==='suspect'||g.state==='search'){ sp=2.6; g.searchT-=dt; tx=g.target.x;tz=g.target.z;
      if(g.fixing&&Math.hypot(g.x-wx(21),g.z-wx(8))<T*1.6){ g.fixing=false; setPower(true); g.state='patrol'; flash('AVISO','Un guardia ha vuelto a arrancar el generador.',4); }
      else if(Math.hypot(g.x-tx,g.z-tz)<T*0.7||g.searchT<=0){ if(g.searchT<=0){g.state='patrol';g.fixing=false;} else g.target={x:tx+(Math.random()-0.5)*T*4,z:tz+(Math.random()-0.5)*T*4}; } }
    else { sp=1.7; const w=g.wps[g.wi]; tx=wx(w[0]); tz=wx(w[1]); if(Math.hypot(g.x-tx,g.z-tz)<0.15)g.wi=(g.wi+1)%g.wps.length; }
    const ddx=tx-g.x,ddz=tz-g.z,L=Math.hypot(ddx,ddz)||1; g.moving=false;
    if(L>0.12){ const ox=g.x,oz=g.z; move(g,ddx/L*sp*dt,ddz/L*sp*dt,0.4); const mv=Math.abs(g.x-ox)+Math.abs(g.z-oz); g.moving=mv>0.004; if(mv<0.004){ if(g.state==='patrol')g.wi=(g.wi+1)%g.wps.length; else g.target={x:g.x+(Math.random()-0.5)*T*3,z:g.z+(Math.random()-0.5)*T*3}; } g.fx=ddx/L; g.fz=ddz/L; }
    if(g.state==='alert'&&seeP){ const dd=dist(g,V)||1; g.fx=(V.x-g.x)/dd; g.fz=(V.z-g.z)/dd; }
    g.fig.g.position.set(g.x,0,g.z); g.fig.g.rotation.y=Math.atan2(g.fx,g.fz); animFig(g.fig,g.moving,dt,g.state==='alert');
    g.mark.visible=g.state!=='patrol'; g.mark.material.map=g.state==='alert'?MK.ex:MK.q; g.mark.position.set(g.x,2.3,g.z);
  });
  updateTeam(dt); if(S.swapT>0)S.swapT-=dt; if(S.muzzleC>0)S.muzzleC-=dt;
  const it=currentInter(); let lab=it?(typeof it.label==='function'?it.label():it.label):''; const ng=nearestGuard(2.0); const ngFar=ng?null:nearestGuard(4.5);
  if(!lab&&ng)lab=ng.state==='alert'?'F · FORCEJEAR':'F · AGARRAR E INTERROGAR'; if(!lab&&ngFar&&ngFar.state!=='alert')lab=(P.crouch?'':'CTRL · AGÁCHATE · ')+'ACÉRCATE POR DETRÁS Y PULSA F';
  fMark.visible=!!(ng&&ng.state!=='alert'); if(ng)fMark.position.set(ng.x,2.25,ng.z);
  guideTick(); if(!lab&&nearestDog(1.8))lab='F · PATADA'; if(!lab&&!P.carry&&S.bodies.some(b=>dist(b,P)<2.2))lab='C · CARGAR EL CUERPO'; if(!lab&&P.carry)lab='C · SOLTAR EL CUERPO';
  if(!locked)lab='CLIC PARA CAPTURAR EL RATÓN'; promptEl.hidden=!lab; promptEl.textContent=lab;
  if(flashT>0){flashT-=dt; if(flashT<=0)flashEl.hidden=true;}
  if(S.recoil>0)S.recoil=Math.max(0,S.recoil-dt*5); if(S.muzzle>0)S.muzzle-=dt;
}
function render(dt){ const P=S.p||{x:wx(start.x),z:wx(start.y),crouch:false};
  if(!cut){ const targetH=P.crouch?0.95:1.6; S.camH=S.camH===undefined?targetH:S.camH+(targetH-S.camH)*Math.min(1,dt*10);
    const bob=P.moving?Math.sin(S.bob||0)*0.04:0;
    if(third){ const f=fwd(); const r={x:Math.cos(yaw),z:-Math.sin(yaw)}; const d=3.4, cp=Math.cos(pitch), sp=Math.sin(pitch);
      let cx=P.x-f.x*d*cp+r.x*0.7, cz=P.z-f.z*d*cp+r.z*0.7, cy=S.camH+0.6-sp*d;
      for(let k=1;k<=12;k++){ const t=k/12; const sx=P.x+(cx-P.x)*t, sz=P.z+(cz-P.z)*t, sy=S.camH+(cy-S.camH)*t; if(solidT(tile(sx),tile(sz))||sy<0.3||(sy>2.85&&interior(tile(sx),tile(sz)))){ const tt=Math.max(0.12,(k-1)/12); cx=P.x+(cx-P.x)*tt; cz=P.z+(cz-P.z)*tt; cy=S.camH+(cy-S.camH)*tt; break; } }
      camera.position.set(cx,Math.max(0.3,cy),cz); camera.lookAt(P.x+f.x*2.5+r.x*0.7,S.camH+0.1+sp*2.5,P.z+f.z*2.5+r.z*0.7); }
    else { camera.position.set(P.x,S.camH+bob,P.z); camera.rotation.set(pitch,yaw,0); } }
  arms.visible=!third&&!cut; const pf=S.p?S.p.fig:playerFig; pf.g.visible=third||!!cut;
  if(S.p){ pf.g.position.set(P.x,S.lying?0.26:0,P.z); pf.g.rotation.y=yaw+Math.PI; pf.g.rotation.z=S.lying?Math.PI/2:0; pf.g.scale.y=P.crouch&&!S.lying?0.7:1; animFig(pf,P.moving&&!S.lying,dt,false); pf.armR.rotation.x=S.lying?0:(S.smoke>0?-2.5:-1.25); }
  ember.intensity=S.smoke>0?0.45+Math.sin((S.t||0)*7)*0.25:0; if(S.smoke>0){ const f=fwd(); ember.position.set(P.x+f.x*0.4,S.camH-0.05,P.z+f.z*0.4); }
  arms.position.set(P.moving?Math.sin((S.bob||0)*0.5)*0.01:0,(P.moving?Math.abs(Math.sin(S.bob||0))*0.015:0)+(P.crouch?-0.03:0),S.recoil*0.07); arms.rotation.set(S.recoil*0.3,0,0);
  spots.forEach(s=>{ const a=s.s.position,b=s.tg.position; const mid=a.clone().add(b).multiplyScalar(0.5); const len=a.distanceTo(b); s.beam.position.copy(mid); s.beam.scale.set(1,len,1); s.beam.quaternion.setFromUnitVectors(new THREE.Vector3(0,-1,0),b.clone().sub(a).normalize()); });
  muzzle.position.set(P.x,1.4,P.z); muzzle.intensity=S.muzzle>0?3:0; if(S.muzzleC>0&&S.c){ muzzle.position.set(S.c.x,1.4,S.c.z); muzzle.intensity=1.2; }
  if(usePost&&rt){ renderer.setRenderTarget(rt); renderer.render(scene,camera); renderer.setRenderTarget(null); post.uniforms.hurt.value=P.hurtT>0?P.hurtT:0; post.uniforms.time.value=S.t||0; renderer.render(postScene,postCam); } else renderer.render(scene,camera);
  drawHud(); }
function drawHud(){ const w=hud.width,h=hud.height; hctx.clearRect(0,0,w,h); if(!started||cut)return; const P=S.p;
  hctx.strokeStyle='rgba(214,228,220,.8)'; hctx.lineWidth=2; const cx=w/2,cy=h/2,g=P.crouch?5:9; hctx.beginPath(); hctx.moveTo(cx-g-6,cy);hctx.lineTo(cx-g,cy);hctx.moveTo(cx+g,cy);hctx.lineTo(cx+g+6,cy);hctx.moveTo(cx,cy-g-6);hctx.lineTo(cx,cy-g);hctx.moveTo(cx,cy+g);hctx.lineTo(cx,cy+g+6); hctx.stroke();
  hctx.font='9px "Press Start 2P",monospace'; hctx.textAlign='left';
  const hidden=playerHidden(); if(hidden){ hctx.fillStyle='#4fb9d6'; hctx.fillText('OCULTO',16,h-20); } else if(S.spotlit){ hctx.fillStyle='#e0483a'; hctx.fillText('¡EN EL FOCO!',16,h-20); } else if(P.crouch){ hctx.fillStyle='#7d948a'; hctx.fillText('AGACHADO',16,h-20); }
  if(P.key){ hctx.fillStyle='#f0b240'; hctx.fillText('LLAVE',16,h-38); } if(P.file){ hctx.fillStyle='#4fc77a'; hctx.fillText('EXPEDIENTE',16,h-56); }
  if(S.smoke>0){ hctx.fillStyle='#f0b240'; hctx.textAlign='center'; hctx.fillText('FUMANDO · '+Math.ceil(S.smoke)+' s · QUIETO',cx,cy+40); hctx.fillStyle='rgba(240,178,64,.25)'; hctx.fillRect(cx-60,cy+52,120,4); hctx.fillStyle='#f0b240'; hctx.fillRect(cx-60,cy+52,120*(1-S.smoke/8),4); }
  if(S.dogs.some(d=>!d.dead)){ hctx.fillStyle='#e0483a'; hctx.textAlign='left'; hctx.fillText('PERROS: '+S.dogs.filter(d=>!d.dead).length,16,h-74); }
  if(S.c){ const C=S.c; hctx.textAlign='right'; hctx.fillStyle=C.down>0?'#e0483a':'#4fb9d6'; hctx.fillText(C.name+(C.down>0?' · HERIDA '+Math.ceil(C.down)+' s':' · '+'♥'.repeat(Math.max(0,C.hp))+'·'.repeat(5-Math.max(0,C.hp))+' · '+C.ammo+' · X CAMBIAR'),w-16,h-20); if(C.hurtT>0){ hctx.fillStyle='rgba(224,72,58,.5)'; hctx.fillRect(w-140,h-14,124,3); } }
  if(S.swapT>0){ hctx.fillStyle='rgba(79,185,214,'+(S.swapT*0.8)+')'; hctx.fillRect(0,0,w,h); hctx.fillStyle='#fff'; hctx.font='12px "Press Start 2P",monospace'; hctx.textAlign='center'; hctx.fillText(P.name,cx,cy-60); }
  if(S.freeze>0){ hctx.fillStyle='#ff4a3a'; hctx.font='48px "Press Start 2P",monospace'; hctx.textAlign='center'; hctx.fillText('!',cx,cy-40); }
  if(S.savedT>0){ S.savedT-=0.016; hctx.fillStyle='#f0b240'; hctx.font='8px "Press Start 2P",monospace'; hctx.textAlign='right'; hctx.fillText('● GUARDADO',w-16,h-40); }
  if(!cut)radar(w,h); }
function radar(w,h){ const sc=3.4, rw=COLS*sc, rh=ROWS*sc, ox=w-rw-16, oy=44; hctx.save(); hctx.globalAlpha=0.85; hctx.fillStyle='rgba(4,10,8,.8)'; hctx.fillRect(ox-4,oy-4,rw+8,rh+8); hctx.strokeStyle='#2a5a3a'; hctx.strokeRect(ox-4,oy-4,rw+8,rh+8);
  if(S.alertT>0){ for(let i=0;i<120;i++){ hctx.fillStyle=Math.random()<0.5?'#1a3a2a':'#0a1a12'; hctx.fillRect(ox+Math.random()*rw,oy+Math.random()*rh,3,2); } hctx.fillStyle='#e0483a'; hctx.font='7px "Press Start 2P",monospace'; hctx.textAlign='center'; hctx.fillText('INTERFERENCIA',ox+rw/2,oy+rh/2); hctx.restore(); return; }
  for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++){ const c=cell(x,y); if(c==='#'||c==='W'||c==='T'||c==='c'||c==='g'){ hctx.fillStyle='#2f5a44'; hctx.fillRect(ox+x*sc,oy+y*sc,sc,sc); } else if(interior(x,y)){ hctx.fillStyle='#0f2a1c'; hctx.fillRect(ox+x*sc,oy+y*sc,sc,sc); } }
  const P=S.p; S.guards.forEach(g=>{ if(g.dead||g.down>0)return; const gx=ox+g.x/T*sc, gz=oy+g.z/T*sc; const a=Math.atan2(g.fz,g.fx), half=Math.PI/180*42, r=(g.state==='alert'?8:6.5)*sc; hctx.fillStyle=g.state==='alert'?'rgba(224,72,58,.35)':'rgba(240,178,64,.3)'; hctx.beginPath(); hctx.moveTo(gx,gz); hctx.arc(gx,gz,r,a-half,a+half); hctx.closePath(); hctx.fill(); hctx.fillStyle=g.state==='alert'?'#e0483a':'#f0b240'; hctx.fillRect(gx-2,gz-2,4,4); });
  S.dogs.forEach(d=>{ if(d.dead)return; hctx.fillStyle='#ff6a5a'; hctx.fillRect(ox+d.x/T*sc-1.5,oy+d.z/T*sc-1.5,3,3); });
  if(S.c){ hctx.fillStyle=S.c.down>0?'#e0483a':'#4fb9d6'; hctx.fillRect(ox+S.c.x/T*sc-2,oy+S.c.z/T*sc-2,4,4); }
  const px=ox+P.x/T*sc, pz=oy+P.z/T*sc, f=fwd(); hctx.fillStyle='#4fc77a'; hctx.beginPath(); hctx.moveTo(px+f.x*5,pz+f.z*5); hctx.lineTo(px-f.z*3-f.x*3,pz+f.x*3-f.z*3); hctx.lineTo(px+f.z*3-f.x*3,pz-f.x*3-f.z*3); hctx.closePath(); hctx.fill(); hctx.restore(); }

window.__LH={releaseDogs,captured,defeat,saveGame,loadGame,radioMenu,startSmoke,wx,swapChar,los,teamThreat,entHidden,get uiOpen(){return uiOpen},get paused(){return paused},get codecQ(){return codecQ},get started(){return started},doGrab,doUse,ask,squeeze,knock:knock,shoot,get locked(){return locked},set locked(v){locked=v},keys,showMenu,startGame,OPT,get third(){return third},set third(v){third=v},S,W,camera,get yaw(){return yaw},set yaw(v){yaw=v},set pitch(v){pitch=v},setPower,keypadIn,openKeypad,knock,raiseAlarm,INTER,codec,CODEC,cutSkip,codecNext,get cut(){return cut}};
resize(); reset(); requestAnimationFrame(loop);
