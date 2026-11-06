// Bot de pruebas para nivel/: juega con la física y la IA reales, paso fijo de 1/30 s.
// Se inyecta en la página (?test) y expone window.BOT.
window.BOT=(function(){ const T=window.__T, S=T.S, P=T.P, IN=T.IN, DT=1/30; const log=[];
  IN.manual=true; IN.bot=true;
  const tick=(n=1)=>{ for(let i=0;i<n;i++){ T.step(DT); if(S.mode==='dialog'){ T.dlgNext(); T.dlgNext(); } } };
  const st=()=>({mode:S.mode,P:[+P.x.toFixed(2),+P.y.toFixed(2),+P.z.toFixed(2)],hp:Math.round(P.hp),alarm:S.alarm,alarms:S.alarms,base:S.base,lad:P.ladder&&P.ladder.name,la:S.lastAlarm,
    G:T.G.map(g=>g.active?g.id+':'+g.state+(g.alive?'':'†')+'@'+g.x.toFixed(1)+','+g.y.toFixed(1)+','+g.z.toFixed(1)+' m'+g.meter.toFixed(2):'-')});
  const face=(x,z)=>{ S.yaw=Math.atan2(-(x-P.x),-(z-P.z)); };
  function crouch(on){ if(P.crouch!==on){ IN.press.add('crouch'); tick(1); } }
  function go(x,z,o={}){ crouch(!!o.crouch); IN.run=!!o.run; let t=0; const max=o.max||60;
    while(Math.hypot(P.x-x,P.z-z)>(o.tol||0.3)){ if(S.mode==='dead')throw new Error('muerto yendo a '+x+','+z+' '+JSON.stringify(st())); if(S.mode!=='play'){ tick(1); continue; }
      face(x,z); IN.f=1; IN.s=0; tick(1); t+=DT; if(t>max)throw new Error('atascado yendo a '+x+','+z+' '+JSON.stringify(st())); }
    IN.f=0; IN.run=false; tick(1); return st(); }
  function jumpTo(x,z){ face(x,z); IN.f=1; IN.press.add('jump'); tick(1); let t=0; while(t<1.2){ face(x,z); tick(1); t+=DT; if(P.onGround&&t>0.3&&Math.hypot(P.x-x,P.z-z)<0.4)break; } IN.f=0; tick(2); return st(); }
  function use(){ IN.press.add('use'); tick(2); }
  function climb(dir){ use(); if(!P.ladder)throw new Error('no agarró la escalera '+JSON.stringify(st())+' prompt='+document.getElementById('prompt').textContent); IN.f=dir; let t=0; while(P.ladder&&t<12){ tick(1); t+=DT; } IN.f=0; tick(2); if(P.ladder)throw new Error('sigue en la escalera'); return st(); }
  function wait(s,cond){ let t=0; while(t<s){ if(cond&&cond())return true; IN.f=0; tick(1); t+=DT; if(S.mode==='dead')throw new Error('muerto esperando '+JSON.stringify(st())); } return false; }
  function aimAt(x,y,z){ IN.aim=true; for(let k=0;k<4;k++){ tick(1); const c=T.camera.position; const dx=x-c.x, dy=y-c.y, dz=z-c.z; S.yaw=Math.atan2(-dx,-dz); S.pitch=Math.atan2(dy,Math.hypot(dx,dz)); } T.updateCamera(DT); }
  function shootGuard(id,head=true,lethal=false){ const g=T.G.find(g=>g.id===id); if(S.lethal!==lethal){ IN.press.add('mode'); tick(1); }
    for(let k=0;k<6&&g.alive&&!g.sleep;k++){ const y=g.y+(head?1.66:1.1); aimAt(g.x,y,g.z); IN.press.add('shoot'); tick(1); if(!head&&g.tranq>0)wait(1.5); }
    IN.aim=false; tick(2); return g.alive&&!g.sleep?'FALLÓ':'abatido'; }
  function takedown(id,lethal=false){ const g=T.G.find(g=>g.id===id); if(S.lethal!==lethal){ IN.press.add('mode'); tick(1); } IN.press.add('takedown'); tick(1); wait(1.3); return g.alive&&!g.sleep?'FALLÓ':'ok'; }
  function fight(ids,maxT=40,lethal=true){ if(S.lethal!==lethal){ IN.press.add('mode'); tick(1); } let t=0; const log=[];
    while(t<maxT){ const live=T.G.filter(g=>ids.includes(g.id)&&g.active&&g.alive&&!g.sleep); if(!live.length)break;
      const c=T.camera.position; const vis=live.filter(g=>Math.hypot(g.x-P.x,g.z-P.z)<32&&T.los(c.x,c.y,c.z,g.x,g.y+(g.y-P.y>2?1.66:1.1),g.z)).sort((a,b)=>Math.hypot(a.x-P.x,a.z-P.z)-Math.hypot(b.x-P.x,b.z-P.z));
      if(vis.length){ const g=vis[0]; aimAt(g.x,g.y+(g.y-P.y>2?1.66:1.1),g.z); IN.press.add('shoot'); tick(1); if(!g.alive)log.push(g.id+'@'+t.toFixed(1)); wait(0.25); t+=0.4; } else { IN.aim=false; wait(0.3); t+=0.3; }
      if(S.mode==='dead')throw new Error('muerto en el tiroteo '+JSON.stringify(st())); }
    IN.aim=false; tick(1); return log.join(' ')+' hp='+Math.round(P.hp)+' balas='+P.ammoL; }
  function guard(id){ return T.G.find(g=>g.id===id); }
  return {fight,tick,st,go,jumpTo,use,climb,wait,aimAt,shootGuard,takedown,guard,face,crouch,log};
})();
