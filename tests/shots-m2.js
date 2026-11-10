// Capturas de la misión 2 con calidad completa: tests/shots/m2-*.png (excavación, laboratorio, compuerta, templo)
const {chromium}=require('playwright'); const path=require('path');
(async()=>{ const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}});
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')+'?gfx=full'); await p.waitForTimeout(1500);
  const closeCodec=async()=>{ for(let i=0;i<24;i++){ if(!(await p.evaluate(()=>!!window.__LH.codecQ)))break; await p.evaluate(()=>window.__LH.codecNext()); await p.waitForTimeout(60);} };
  const settle=async()=>{ for(let i=0;i<40;i++){ if(await p.evaluate(()=>!!window.__LH.cut))await p.evaluate(()=>window.__LH.cutSkip()); await closeCodec(); if(await p.evaluate(()=>!window.__LH.uiOpen&&!window.__LH.cut&&!window.__LH.codecQ&&!window.__LH.S.traveling))break; await p.waitForTimeout(150);} };
  const shot=async(name,x,y,yaw,pitch)=>{ await settle(); await p.evaluate(([x,y,yaw,pitch])=>{ const L=window.__LH; L.S.p.x=L.wx(x); L.S.p.z=L.wx(y); L.S.c.x=L.S.p.x+0.8; L.S.c.z=L.S.p.z+0.8; L.yaw=yaw; L.pitch=pitch||0; L.third=true; L.locked=true; L.S.alertT=0; L.S.guards.forEach(g=>{ g.state='patrol'; g.susp=0; g.shotT=999; }); },[x,y,yaw,pitch]); await p.waitForTimeout(700); await p.screenshot({path:path.resolve(__dirname,'shots','m2-'+name+'.png')}); };
  await p.click('#btnM2'); await p.waitForTimeout(600); await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(300); await closeCodec(); await settle();
  await shot('excavacion',14,3,Math.PI,0.05); await shot('canal',12,11,Math.PI*0.75,0.1); await shot('laboratorio',21,12,-Math.PI/2,0.05); await shot('compuerta',14,17,Math.PI,0.05);
  await p.evaluate(()=>{ const L=window.__LH; [0,1,2].forEach(i=>L.toggleGen(i)); L.S.fixTimer=9999; }); await shot('compuerta-caida',14,17,Math.PI,0.05);
  await p.evaluate(()=>window.__LH.travel('templo',[3,17],-Math.PI/2)); await p.waitForTimeout(1400); await p.screenshot({path:path.resolve(__dirname,'shots','m2-carga.png')}); await p.waitForTimeout(1600); await settle(); await p.waitForTimeout(1500); await settle();
  await shot('templo',6,12,-Math.PI*0.75,0.05); await shot('alberca',11,10,0,0.15); await shot('montacargas',15,4,-Math.PI/2,0);
  await b.close(); console.log('capturas m2 listas'); })();
