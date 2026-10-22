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
  await p.click('[data-go="brief"]'); await p.click('#btnStart'); await p.waitForTimeout(800);
  await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(400);
  const closeCodec=async()=>{ for(let i=0;i<24;i++){ if(!(await p.evaluate(()=>!!window.__LH.codecQ)))break; await p.evaluate(()=>window.__LH.codecNext()); await p.waitForTimeout(60);} };
  const settle=async()=>{ for(let i=0;i<30;i++){ await closeCodec(); if(await p.evaluate(()=>!window.__LH.uiOpen&&!window.__LH.cut&&!window.__LH.codecQ))break; await p.waitForTimeout(150);} };
  await settle();
  ok(await p.evaluate(()=>window.__LH.S.guards.length>0),'guardias creados');
  await p.evaluate(()=>{window.__LH.third=true;}); await p.waitForTimeout(300);
  // órdenes a Roig: por defecto espera; G la hace seguir
  const frames=async(n)=>{ for(let i=0;i<n;i++)await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>r()))); };
  await p.evaluate(()=>{ const L=window.__LH; L.locked=true; L.S.guards.forEach(g=>{ g.state='patrol'; g.susp=0; g.wps=[[Math.floor(g.x/2),Math.floor(g.z/2)]]; g.wi=0; }); L.S.c.x=L.wx(2); L.S.c.z=L.wx(8); L.S.c.crouch=false; });
  await frames(30);
  ok(await p.evaluate(()=>{ const L=window.__LH; return L.S.cOrder==='wait'&&Math.abs(L.S.c.z-L.wx(8))<0.05&&L.S.c.crouch===true; }),'Roig espera agachada donde está si no se le ordena nada');
  await p.keyboard.press('g'); await frames(30);
  ok(await p.evaluate(()=>{ const L=window.__LH; return L.S.cOrder==='follow'&&L.S.orders===1&&L.S.c.z<L.wx(8)-0.5; }),'G ordena seguir y Roig se acerca');
  await p.keyboard.press('g'); await frames(2); ok(await p.evaluate(()=>window.__LH.S.cOrder==='wait'),'G otra vez: vuelve a esperar');
  ok(await p.evaluate(()=>{ const L=window.__LH; const g=L.S.guards[0]; const ox=g.x,oz=g.z; g.state='search'; g.x=L.S.c.x+1.5; g.z=L.S.c.z; const t=L.teamThreat(L.S.c); g.state='alert'; const t2=L.teamThreat(L.S.c); g.state='patrol'; g.x=ox; g.z=oz; return !t&&t2===g; }),'solo considera amenaza a un guardia en alerta, no a uno que busca');
  await p.evaluate(()=>window.__LH.startSmoke()); ok(await p.evaluate(()=>window.__LH.S.smoke>0),'fumar arranca el contador de 8 s');
  await p.evaluate(()=>window.__LH.releaseDogs()); await p.waitForTimeout(300);
  ok(await p.evaluate(()=>!!window.__LH.cut),'la perrera arranca con cinemática');
  await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(1200); await settle();
  ok(await p.evaluate(()=>window.__LH.S.dogs.length===7),'salen 7 perros');
  // radio
  await p.evaluate(()=>window.__LH.radioMenu()); await p.waitForTimeout(200);
  ok(await p.evaluate(()=>!document.getElementById('dlg').hidden&&document.getElementById('dlg').textContent.includes('141.12')),'R abre la radio con la frecuencia de Control');
  await p.keyboard.press('1'); await p.waitForTimeout(300); ok(await p.evaluate(()=>!!window.__LH.codecQ&&window.__LH.S.calls.control===1),'llamar a Control abre el códec'); await settle();
  // derrota por los guardias → cinemática de captura → celda
  await p.evaluate(()=>window.__LH.defeat('guards')); await p.waitForTimeout(300);
  ok(await p.evaluate(()=>!!window.__LH.cut&&window.__LH.S.lying===true),'la captura tiene cinemática y el jugador cae');
  await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(2900); await settle(); await p.waitForTimeout(300);
  ok(await p.evaluate(()=>window.__LH.S.inCell===true&&window.__LH.S.p.ammo===0&&!window.__LH.S.over),'captura por los guardias: en la celda y sin balas, no es fin de partida');
  ok(await p.evaluate(()=>{ const sv=JSON.parse(localStorage.getItem('lh-save')||'null'); return sv&&sv.inCell===true; }),'la celda guarda la partida');
  await p.evaluate(()=>{window.__LH.S.clues.push('fuente','peris');});
  const press=async(k)=>{await p.keyboard.press(k);await p.waitForTimeout(250);};
  await p.evaluate(()=>{const it=window.__LH.INTER.find(i=>i.x===31&&i.y===12);it.f();}); await p.waitForTimeout(300);
  await press('2'); await press('1'); await press('2'); await press('1'); await press('2'); await press('1');
  ok(await p.evaluate(()=>window.__LH.W.cellOpen&&window.__LH.S.p.ammo===4&&!window.__LH.S.inCell),'Vidal convencido: celda abierta y 4 balas');
  // guardado y continuar
  await p.evaluate(()=>{ const L=window.__LH; L.S.p.x=L.wx(20); L.S.p.z=L.wx(20); L.saveGame('Prueba'); L.S.p.x=0; L.S.p.z=0; L.S.clues.length=0; });
  ok(await p.evaluate(()=>{ const L=window.__LH; const d=L.loadGame(); return !!d&&d.tag==='Prueba'&&Math.abs(L.S.p.x-L.wx(20))<0.01&&L.S.clues.includes('fuente')&&L.W.cellOpen&&!L.S.inCell; }),'cargar la partida recupera posición, pistas y celda abierta');
  await p.evaluate(()=>window.__LH.showMenu('main')); ok(await p.evaluate(()=>!document.getElementById('btnContinue').hidden&&document.getElementById('btnContinue').textContent.includes('Prueba')),'CONTINUAR aparece en el menú con la etiqueta del guardado');
  await p.click('#btnContinue'); await p.waitForTimeout(400); ok(await p.evaluate(()=>document.getElementById('ov').hidden&&window.__LH.started),'CONTINUAR reanuda la partida');
  // segunda derrota: fin de partida con continuidad
  await p.evaluate(()=>window.__LH.defeat('guards')); await p.waitForTimeout(400);
  ok(await p.evaluate(()=>window.__LH.S.over&&!document.getElementById('end').hidden&&document.getElementById('end').textContent.includes('CUARTA SESIÓN')&&document.getElementById('end').textContent.includes('CUTTLAAAAAS')),'segunda captura: pantalla de derrota CUARTA SESIÓN con el grito del códec');
  ok(await p.evaluate(()=>!document.getElementById('btnAgain').hidden),'botón ÚLTIMO PUNTO disponible');
  await p.screenshot({path:path.resolve(__dirname,'last.png')});
  ok(errs.length===0,'sin errores de consola '+(errs.length?JSON.stringify(errs):''));
  await b.close();
})();
