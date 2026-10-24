// Captura de los guardias en fila, de frente, para revisar caras y peinados. Uso: node tests/shots-guards.js → tests/shots/guardias.png
const {chromium}=require('playwright'); const path=require('path');
(async()=>{ const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}});
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')+'?gfx=full'); await p.waitForTimeout(1500);
  await p.click('[data-go="brief"]'); await p.click('#btnStart'); await p.waitForTimeout(800); await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(400);
  for(let i=0;i<24;i++){ if(!(await p.evaluate(()=>!!window.__LH.codecQ)))break; await p.evaluate(()=>window.__LH.codecNext()); await p.waitForTimeout(60);} 
  await p.evaluate(()=>{ const L=window.__LH; L.locked=true; L.S.freezeAI=true; L.S.c.x=L.wx(2); L.S.c.z=L.wx(26); L.S.c.ammo=0; L.S.alertT=0; const px=L.wx(25),pz=L.wx(23.2); L.S.p.x=px; L.S.p.z=pz; L.yaw=0; L.pitch=-0.08; L.S.codecSeen.alarm=true;
    L.S.guards.forEach((g,i)=>{ g.state='patrol'; g.susp=0; g.x=px+(i-2.5)*0.8; g.z=pz-2.8; g.fx=0; g.fz=1; g.shotT=999; g.held=true; g.wps=[[Math.floor(g.x/2),Math.floor(g.z/2)]]; g.wi=0; g.fig.g.position.set(g.x,0,g.z); g.fig.g.rotation.y=Math.atan2(g.fx,g.fz); }); });
  for(let i=0;i<2;i++)await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>r()))); await p.evaluate(()=>{ const L=window.__LH; L.S.alertT=0; L.S.guards.forEach(g=>{ g.state='patrol'; g.susp=0; }); }); await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>r())));
  await p.screenshot({path:path.resolve(__dirname,'shots','guardias.png')}); console.log('captura guardias'); await b.close(); })();
