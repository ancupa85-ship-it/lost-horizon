// Capturas de la misión 3 con calidad completa: tests/shots/m3-*.png (patio de la torre, archivo, radio, depósito, incendio, perímetro, embarcadero, carretera)
const {chromium}=require('playwright'); const path=require('path');
(async()=>{ const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}});
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')+'?gfx=full'); await p.waitForTimeout(1500);
  const closeCodec=async()=>{ for(let i=0;i<24;i++){ if(!(await p.evaluate(()=>!!window.__LH.codecQ)))break; await p.evaluate(()=>window.__LH.codecNext()); await p.waitForTimeout(60);} };
  const settle=async()=>{ for(let i=0;i<40;i++){ if(await p.evaluate(()=>!!window.__LH.cut))await p.evaluate(()=>window.__LH.cutSkip()); await closeCodec(); if(await p.evaluate(()=>!window.__LH.uiOpen&&!window.__LH.cut&&!window.__LH.codecQ&&!window.__LH.S.traveling))break; await p.waitForTimeout(150);} };
  const shot=async(name,x,y,yaw,pitch)=>{ await settle(); await p.evaluate(([x,y,yaw,pitch])=>{ const L=window.__LH; L.S.p.x=L.wx(x); L.S.p.z=L.wx(y); L.S.c.x=L.S.p.x+0.8; L.S.c.z=L.S.p.z+0.8; L.yaw=yaw; L.pitch=pitch||0; L.third=true; L.locked=true; L.S.alertT=0; L.S.guards.forEach(g=>{ g.state='patrol'; g.susp=0; g.shotT=999; }); },[x,y,yaw,pitch]); await p.waitForTimeout(700); await p.screenshot({path:path.resolve(__dirname,'shots','m3-'+name+'.png')}); console.log('m3-'+name); };
  await p.click('#btnM3'); await p.waitForTimeout(600); await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(300); await closeCodec(); await settle();
  await shot('patio',3,18,-Math.PI/4,0.12); await shot('torre',13,12,0,0.25); await shot('archivo',9,5,0,0.05); await shot('radio',17,5,0,0.05); await shot('deposito',23,8,0,0.05);
  await p.evaluate(()=>{ const L=window.__LH; L.S.gas=true; L.burnArchive(); L.S.alertT=0; L.S.burnT=0.01; }); await p.waitForTimeout(1800); await settle(); await p.waitForTimeout(300); await settle(); await shot('incendio',9,7,0,0.05); await shot('oscuridad',20,14,Math.PI/2,0.05);
  await p.evaluate(()=>window.__LH.travel('perimetro',[1,8],-Math.PI/2)); await p.waitForTimeout(1400); await p.screenshot({path:path.resolve(__dirname,'shots','m3-carga.png')}); await p.waitForTimeout(1600); await settle(); await p.waitForTimeout(1500); await settle();
  await p.evaluate(()=>window.__LH.setPower(true));
  await shot('perimetro',2,8,-Math.PI/2,0.05); await shot('valla-rota',3,13,-Math.PI/2,0.05); await shot('marisma',10,8,-Math.PI/2,0.08); await shot('embarcadero',25,9,-Math.PI/2,0.05); await shot('carretera',27,4,0,0.08);
  await b.close(); console.log('capturas m3 listas'); })();
