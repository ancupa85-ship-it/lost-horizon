// Prueba de humo sin cabeza: arranca el juego, salta la intro, suelta a los perros,
// fuerza la captura y recorre la persuasión de Vidal con las pistas correctas.
// Uso: node tests/smoke.js   (requiere `npm i -D playwright` y Chromium)
const {chromium}=require('playwright');
const path=require('path');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}});
  const errs=[]; p.on('pageerror',e=>errs.push(e.message)); p.on('console',m=>{ if(m.type()==='error')errs.push(m.text()); });
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')); await p.waitForTimeout(1500);
  const ok=(c,msg)=>{ if(!c){ console.error('FALLO:',msg); process.exitCode=1; } else console.log('ok  ',msg); };
  ok(await p.evaluate(()=>!!window.__LH),'motor cargado y estado expuesto');
  await p.click('#btnStart'); await p.waitForTimeout(800);
  await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(400);
  for(let i=0;i<9;i++)await p.evaluate(()=>window.__LH.codecNext());
  ok(await p.evaluate(()=>window.__LH.S.guards.length>0),'guardias creados');
  await p.evaluate(()=>{window.__LH.third=true;}); await p.waitForTimeout(300);
  await p.evaluate(()=>window.__LH.startSmoke()); ok(await p.evaluate(()=>window.__LH.S.smoke>0),'fumar arranca el contador de 8 s');
  await p.evaluate(()=>window.__LH.releaseDogs()); await p.waitForTimeout(600);
  for(let i=0;i<9;i++)await p.evaluate(()=>window.__LH.codecNext());
  ok(await p.evaluate(()=>window.__LH.S.dogs.length===7),'salen 7 perros');
  await p.evaluate(()=>window.__LH.captured()); await p.waitForTimeout(5500);
  for(let i=0;i<9;i++)await p.evaluate(()=>window.__LH.codecNext()); await p.waitForTimeout(400);
  ok(await p.evaluate(()=>window.__LH.S.inCell===true&&window.__LH.S.p.ammo===0),'captura: en la celda y sin balas');
  await p.evaluate(()=>{window.__LH.S.clues.push('fuente','peris');});
  const press=async(k)=>{await p.keyboard.press(k);await p.waitForTimeout(250);};
  await p.evaluate(()=>{const it=window.__LH.INTER.find(i=>i.x===31&&i.y===12);it.f();}); await p.waitForTimeout(300);
  await press('2'); await press('1'); await press('2'); await press('1'); await press('2'); await press('1');
  ok(await p.evaluate(()=>window.__LH.W.cellOpen&&window.__LH.S.p.ammo===4&&!window.__LH.S.inCell),'Vidal convencido: celda abierta y 4 balas');
  await p.screenshot({path:path.resolve(__dirname,'last.png')});
  ok(errs.length===0,'sin errores de consola '+(errs.length?JSON.stringify(errs):''));
  await b.close();
})();
