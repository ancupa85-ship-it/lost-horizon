// Prueba corta en tiempo real del nivel con teclado de verdad (sin bot): node tests/nivel-smoke.js
const {chromium}=require('playwright'); const path=require('path');
(async()=>{ const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message)); p.on('console',m=>{ if(m.type()==='error')errs.push(m.text()); });
  let fails=0; const ok=(c,m)=>{ console.log((c?'ok   ':'FALLO ')+m); if(!c){ fails++; process.exitCode=1; } };
  await p.goto('file://'+path.resolve(__dirname,'..','nivel','index.html')+'?test'); await p.waitForTimeout(800);
  ok(await p.evaluate(()=>!!window.__T&&__T.NAV.nodes.length>5000),'nivel cargado y rejilla de navegación construida');
  await p.click('#btnGo'); await p.waitForTimeout(300);
  ok(await p.evaluate(()=>__T.S.mode==='dialog'),'briefing de Control al empezar');
  for(let i=0;i<12;i++){ await p.keyboard.press('e'); await p.waitForTimeout(60); }
  ok(await p.evaluate(()=>__T.S.mode==='play'),'E pasa el códec y empieza la partida');
  const z0=await p.evaluate(()=>__T.P.z); await p.keyboard.down('w'); await p.waitForTimeout(1500); await p.keyboard.up('w'); const z1=await p.evaluate(()=>__T.P.z);
  ok(z1<z0-1,'W hace avanzar a Cuttlas por el embarcadero ('+z0.toFixed(1)+' → '+z1.toFixed(1)+')');
  await p.keyboard.press('q'); await p.waitForTimeout(100); ok(await p.evaluate(()=>__T.S.lethal&&document.getElementById('mode').textContent.startsWith('LETAL')),'Q cambia a letal y el HUD lo muestra');
  await p.keyboard.press('q'); await p.keyboard.press('c'); await p.waitForTimeout(100); ok(await p.evaluate(()=>__T.P.crouch),'C agacha');
  await p.keyboard.press('c'); await p.keyboard.press('Tab'); await p.waitForTimeout(100); ok(await p.evaluate(()=>!document.getElementById('notes').hidden),'Tab abre el cuaderno');
  await p.keyboard.press('Tab'); await p.waitForTimeout(100); ok(await p.evaluate(()=>__T.S.mode==='play'),'Tab lo cierra');
  const fps=await p.evaluate(()=>new Promise(r=>{ let n=0; const t0=performance.now(); const f=()=>{ n++; if(performance.now()-t0<2000)requestAnimationFrame(f); else r(n/2); }; requestAnimationFrame(f); }));
  console.log('     fps sin GPU (SwiftShader):',fps.toFixed(1));
  // teclado de la caja fuerte con teclas reales
  await p.evaluate(()=>{ __T.S.flags.inside=1; __T.S.objective=2; const P=__T.P; P.x=0; P.y=4; P.z=-20.2; }); await p.waitForTimeout(200); await p.keyboard.press('e'); await p.waitForTimeout(150);
  ok(await p.evaluate(()=>__T.S.mode==='keypad'),'E junto a la caja fuerte abre el teclado');
  for(const k of ['0','1','0','3','Enter']){ await p.keyboard.press(k); await p.waitForTimeout(40); }
  await p.waitForTimeout(200); ok(await p.evaluate(()=>__T.S.hasFile),'0103 + Enter abre la caja');
  for(let i=0;i<14;i++){ await p.keyboard.press('e'); await p.waitForTimeout(60); }
  ok(await p.evaluate(()=>__T.S.mode==='play'&&__T.S.objective===3),'tras leer el expediente, el objetivo es salir');
  // muerte y reintento desde el último punto (guardado al coger el expediente)
  await p.evaluate(()=>__T.hurt(500,'disparo')); await p.waitForTimeout(100);
  ok(await p.evaluate(()=>__T.S.mode==='dead'&&!document.getElementById('over').hidden),'sin vida: pantalla de misión fallida');
  await p.click('#btnRetry'); await p.waitForTimeout(200);
  ok(await p.evaluate(()=>__T.S.mode==='play'&&__T.S.hasFile&&__T.P.hp>=60),'ÚLTIMO PUNTO vuelve con el expediente y vida');
  await p.screenshot({path:path.resolve(__dirname,'shots-nivel','smoke.png')});
  ok(errs.length===0,'sin errores de JavaScript '+errs.slice(0,3).join(' | '));
  await b.close(); })();
