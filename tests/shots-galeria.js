// Capturas de la galería de acceso (zona 2) con calidad completa: tests/shots/galeria-*.png
const {chromium}=require('playwright'); const path=require('path');
(async()=>{ const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}});
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')+'?gfx=full'); await p.waitForTimeout(1500);
  await p.click('[data-go="brief"]'); await p.click('#btnStart'); await p.waitForTimeout(800); await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(300);
  const closeCodec=async()=>{ for(let i=0;i<24;i++){ if(!(await p.evaluate(()=>!!window.__LH.codecQ)))break; await p.evaluate(()=>window.__LH.codecNext()); await p.waitForTimeout(60);} }; await closeCodec();
  await p.evaluate(()=>{ const L=window.__LH; L.S.p.key=true; L.W.hatchOpen=true; L.ZONE.sync(); L.S.p.x=L.wx(20); L.S.p.z=L.wx(24); L.yaw=Math.PI; L.third=true; L.locked=true; }); await p.waitForTimeout(600);
  await p.screenshot({path:path.resolve(__dirname,'shots','galeria-compuerta.png')});
  await p.evaluate(()=>window.__LH.travel('galeria',[3,2],-Math.PI/2)); await p.waitForTimeout(1500);
  await p.screenshot({path:path.resolve(__dirname,'shots','galeria-carga.png')}); await p.waitForTimeout(1500); await closeCodec();
  await p.evaluate(()=>{ const L=window.__LH; L.locked=true; L.third=true; }); await p.waitForTimeout(400);
  await p.screenshot({path:path.resolve(__dirname,'shots','galeria-escalera.png')});
  await p.evaluate(()=>{ const L=window.__LH; L.S.p.x=L.wx(7); L.S.p.z=L.wx(10); L.yaw=Math.PI; L.S.c.x=L.wx(6); L.S.c.z=L.wx(9); L.third=true; }); await p.waitForTimeout(500);
  await p.screenshot({path:path.resolve(__dirname,'shots','galeria-sala.png')});
  await p.evaluate(()=>{ const L=window.__LH; L.S.p.x=L.wx(7); L.S.p.z=L.wx(13); L.yaw=Math.PI; L.third=false; }); await p.waitForTimeout(500);
  await p.screenshot({path:path.resolve(__dirname,'shots','galeria-blindada.png')});
  await b.close(); })();
