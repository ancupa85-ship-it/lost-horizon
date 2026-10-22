// Capturas de referencia: guardia de cerca, jugador en 3ª persona, perros y Vidal en la celda.
// Uso: node tests/shots.js  → tests/shots/*.png
const {chromium}=require('playwright'); const path=require('path'); const fs=require('fs');
(async()=>{ const out=path.resolve(__dirname,'shots'); fs.mkdirSync(out,{recursive:true});
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')); await p.waitForTimeout(1500);
  await p.click('#btnStart'); await p.waitForTimeout(800); await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(400);
  for(let i=0;i<9;i++)await p.evaluate(()=>window.__LH.codecNext());
  const shot=async(n)=>{ await p.waitForTimeout(700); await p.screenshot({path:path.join(out,n+'.png')}); console.log('captura',n); };
  // 1) guardia Ibarra de frente, a 3 m
  await p.evaluate(()=>{ const L=window.__LH; const g=L.S.guards.find(g=>g.name.includes('Ibarra')); g.state='patrol'; L.S.p.x=g.x; L.S.p.z=g.z+3; g.fx=0; g.fz=1; L.yaw=0; L.pitch=-0.05; L.S.freezeAI=true; });
  await shot('guardia');
  // 2) jugador en tercera persona
  await p.evaluate(()=>{ window.__LH.third=true; }); await shot('tercera');
  // 3) perros
  await p.evaluate(()=>{ const L=window.__LH; L.third=false; L.releaseDogs(); }); await p.waitForTimeout(300); for(let i=0;i<9;i++)await p.evaluate(()=>window.__LH.codecNext());
  await p.evaluate(()=>{ const L=window.__LH; L.S.p.x=L.wx?L.wx(22):45; L.S.p.z=L.wx?L.wx(6):13; L.yaw=0; L.pitch=-0.1; L.S.dogs.forEach((d,i)=>{ d.x=L.S.p.x+(i-3)*0.9; d.z=L.S.p.z-3.2; d.fx=0; d.fz=1; }); }); await p.waitForTimeout(120); await p.screenshot({path:path.join(out,'perros.png')}); console.log('captura perros');
  // 4) Vidal en la celda
  await p.evaluate(()=>window.__LH.captured()); await p.waitForTimeout(5500); for(let i=0;i<9;i++)await p.evaluate(()=>window.__LH.codecNext()); await p.waitForTimeout(300);
  await p.evaluate(()=>{ const L=window.__LH; L.yaw=0.33; L.pitch=0.02; }); await shot('vidal');
  console.log('errores',errs); await b.close(); })();
