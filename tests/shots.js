// Capturas de referencia: guardia de cerca, jugador en 3ª persona, perros y Vidal en la celda.
// Uso: node tests/shots.js  → tests/shots/*.png
const {chromium}=require('playwright'); const path=require('path'); const fs=require('fs');
(async()=>{ const out=path.resolve(__dirname,'shots'); fs.mkdirSync(out,{recursive:true});
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  const ev=(f,a)=>p.evaluate(f,a); const frames=async(n)=>{ for(let i=0;i<n;i++)await ev(()=>new Promise(r=>requestAnimationFrame(()=>r()))); };
  const closeCodec=async()=>{ for(let i=0;i<24;i++){ if(!(await ev(()=>!!window.__LH.codecQ)))break; await ev(()=>window.__LH.codecNext()); await p.waitForTimeout(60);} };
  const calm=()=>ev(()=>{ const L=window.__LH; L.locked=true; L.S.c.ammo=0; L.S.alertT=0; L.S.guards.forEach(g=>{ g.state='patrol'; g.susp=0; g.wps=[[Math.floor(g.x/2),Math.floor(g.z/2)]]; g.wi=0; }); });
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')+'?gfx=full'); await p.waitForTimeout(1500);
  await p.waitForTimeout(400); await p.screenshot({path:path.join(out,'menu.png')}); console.log('captura menu');
  await p.click('[data-go="how"]'); await p.waitForTimeout(300); await p.screenshot({path:path.join(out,'como.png')}); await p.click('[data-pane="how"] [data-go="main"]');
  await p.click('[data-go="brief"]'); await p.click('#btnStart'); await p.waitForTimeout(800); await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(400);
  await closeCodec(); await calm(); await frames(2);
  const shot=async(n)=>{ await closeCodec(); await calm(); await frames(3); await p.screenshot({path:path.join(out,n+'.png')}); console.log('captura',n); };
  // 1) guardia Ibarra de frente, a 3 m
  await p.evaluate(()=>{ const L=window.__LH; const g=L.S.guards.find(g=>g.name.includes('Ibarra')); g.state='patrol'; L.S.p.x=g.x; L.S.p.z=g.z+3; g.fx=0; g.fz=1; L.yaw=0; L.pitch=-0.05; L.S.freezeAI=true; });
  await shot('guardia');
  // 2) jugador en tercera persona con Roig detrás
  await p.evaluate(()=>{ const L=window.__LH; L.third=true; L.S.c.x=L.S.p.x+1.2; L.S.c.z=L.S.p.z+1.6; L.S.c.crouch=false; }); await shot('tercera');
  // 2b) Roig de frente
  await p.evaluate(()=>{ const L=window.__LH; L.third=false; L.S.c.x=L.S.p.x; L.S.c.z=L.S.p.z-2.6; L.S.c.fx=0; L.S.c.fz=1; L.yaw=0; L.pitch=-0.05; }); await shot('roig');
  // 3) perros
  await p.evaluate(()=>{ const L=window.__LH; L.third=false; L.releaseDogs(); }); await p.waitForTimeout(1200); await p.screenshot({path:path.join(out,'perrera.png')}); console.log('captura perrera');
  await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(1200); await closeCodec();
  await p.evaluate(()=>{ const L=window.__LH; L.S.p.x=L.wx?L.wx(22):45; L.S.p.z=L.wx?L.wx(6):13; L.yaw=0; L.pitch=-0.1; L.S.dogs.forEach((d,i)=>{ d.x=L.S.p.x+(i-3)*0.9; d.z=L.S.p.z-3.2; d.fx=0; d.fz=1; }); }); await p.waitForTimeout(120); await p.screenshot({path:path.join(out,'perros.png')}); console.log('captura perros');
  // 4) Vidal en la celda
  await p.evaluate(()=>window.__LH.captured('guards')); await p.waitForTimeout(1500); await p.screenshot({path:path.join(out,'captura.png')}); console.log('captura captura');
  await p.waitForTimeout(4200); await p.screenshot({path:path.join(out,'alarcon.png')}); console.log('captura alarcon');
  await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(2900); await closeCodec(); await frames(2);
  await p.evaluate(()=>{ const L=window.__LH; L.yaw=0.33; L.pitch=0.02; }); await shot('vidal');
  // 5) radio y pantalla de derrota
  await p.evaluate(()=>window.__LH.radioMenu()); await p.waitForTimeout(200); await p.screenshot({path:path.join(out,'radio.png')}); console.log('captura radio');
  await p.keyboard.press('1'); await p.waitForTimeout(400); await p.screenshot({path:path.join(out,'codec-control.png')}); console.log('captura codec-control'); await closeCodec();
  await p.evaluate(()=>window.__LH.defeat('guards')); await p.waitForTimeout(900); await p.screenshot({path:path.join(out,'derrota.png')}); console.log('captura derrota');
  console.log('errores',errs); await b.close(); })();
