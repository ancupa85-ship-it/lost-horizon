// Partida completa sin cabeza: menú → intro → interrogar a Ibarra (llave) → despacho → escritorio → teletipo
// → teclado 0129 → expediente → cambio a Roig y vuelta → salida sureste → final. Comprueba cada requisito.
const {chromium}=require('playwright'); const path=require('path');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  const ok=(c,m)=>{ if(!c){console.error('FALLO:',m);process.exitCode=1;} else console.log('ok  ',m); };
  const ev=(f,a)=>p.evaluate(f,a); const wait=(ms)=>p.waitForTimeout(ms);
  const frames=async(n)=>{ for(let i=0;i<n;i++)await ev(()=>new Promise(r=>requestAnimationFrame(()=>r()))); };
  const closeCodec=async()=>{ for(let i=0;i<24;i++){ if(!(await ev(()=>!!window.__LH.codecQ)))break; await ev(()=>window.__LH.codecNext()); await wait(60);} };
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')); await wait(1500);
  // menú
  ok(await ev(()=>!document.getElementById('ov').hidden&&!document.querySelector('[data-pane="main"]').hidden),'menú principal visible');
  await p.click('[data-go="opt"]'); ok(await ev(()=>!document.querySelector('[data-pane="opt"]').hidden),'panel de opciones');
  await p.click('[data-pane="opt"] [data-go="main"]'); await p.click('[data-go="how"]'); ok(await ev(()=>!document.querySelector('[data-pane="how"]').hidden),'panel cómo se juega');
  await p.click('[data-pane="how"] [data-go="main"]'); await p.click('[data-go="brief"]'); await p.click('#btnStart'); await frames(3);
  ok(await ev(()=>document.getElementById('ov').hidden),'la partida arranca y el menú se cierra');
  await ev(()=>window.__LH.cutSkip()); await frames(2); await closeCodec(); await ev(()=>{window.__LH.locked=true;}); await frames(3);
  ok(await ev(()=>window.__LH.S.c&&window.__LH.S.c.name==='ROIG'&&window.__LH.S.c.fig.g.visible),'Roig existe y es visible');
  // guía
  ok(await ev(()=>!document.getElementById('guide').hidden&&document.getElementById('guide').textContent.includes('Agáchate')),'guía en pantalla con el primer paso');
  // pausa
  await p.keyboard.press('Escape'); await frames(1); ok(await ev(()=>!document.getElementById('ov').hidden&&!document.querySelector('[data-pane="pause"]').hidden),'Esc abre la pausa');
  await p.keyboard.press('Escape'); await frames(1); ok(await ev(()=>document.getElementById('ov').hidden),'Esc reanuda');
  await ev(()=>{ if(document.pointerLockElement)document.exitPointerLock(); else { window.__LH.locked=true; document.dispatchEvent(new Event('pointerlockchange')); } }); await wait(300); await frames(2); ok(await ev(()=>window.__LH.paused&&!document.querySelector('[data-pane="pause"]').hidden),'perder el ratón pausa sola la partida');
  await p.click('#btnResume'); await frames(1); await ev(()=>{window.__LH.locked=true;}); ok(await ev(()=>!window.__LH.paused&&document.getElementById('ov').hidden),'REANUDAR cierra la pausa');
  // interrogatorio a Ibarra por la espalda
  await ev(()=>{ const L=window.__LH; L.S.c.ammo=0; L.S.bodies.length=0; L.S.guards.forEach(g=>{ g.state='patrol'; g.susp=0; g.down=0; g.held=false; }); const g=L.S.guards.find(g=>g.name.includes('Ibarra')); g.x=L.wx(13); g.z=L.wx(5); g.wps=[[13,5]]; g.wi=0; g.state='patrol'; g.fx=0; g.fz=-1; L.S.p.x=g.x; L.S.p.z=g.z+1.2; L.yaw=0; L.S.c.x=g.x+1; L.S.c.z=g.z+2; });
  await frames(4);
  ok(await ev(()=>document.getElementById('prompt').textContent.includes('INTERROGAR')),'aviso F · AGARRAR E INTERROGAR al estar detrás');
  await ev(()=>window.__LH.doGrab()); await frames(1);
  ok(await ev(()=>!document.getElementById('dlg').hidden&&document.getElementById('dlgTitle').textContent.includes('Ibarra')),'diálogo de interrogatorio abierto');
  await p.keyboard.press('2'); await frames(1); await p.keyboard.press('4'); await frames(1); await p.keyboard.press('2'); await frames(1);
  ok(await ev(()=>window.__LH.S.p.key===true),'Ibarra suelta la llave tras apretar'); await frames(2);
  ok(await ev(()=>document.getElementById('hObj').textContent.includes('3/6')&&document.getElementById('hObj').textContent.includes('DESPACHO')),'objetivo 3/6: abrir el despacho');
  ok(await ev(()=>window.__LH.S.clues.includes('llave')),'pista de la llave en el cuaderno');
  await p.keyboard.press('5'); await frames(2); ok(await ev(()=>window.__LH.S.ko===1&&document.getElementById('dlg').hidden),'guardia dormido y diálogo cerrado');
  // despacho: puerta, escritorio y teletipo
  const use=async(x,y,yaw)=>{ await ev(([x,y,yaw])=>{ const L=window.__LH; L.S.p.x=L.wx(x); L.S.p.z=L.wx(y); L.yaw=yaw; },[x,y,yaw]); await frames(2); await ev(()=>window.__LH.doUse()); await frames(1); };
  await use(4,16,0); ok(await ev(()=>window.__LH.W.officeOpen),'despacho abierto con la llave'); await frames(2); ok(await ev(()=>document.getElementById('hObj').textContent.includes('4/6')),'objetivo 4/6: la clave del archivo');
  await use(3,18,0); ok(await ev(()=>window.__LH.S.clues.includes('vulgata')),'escritorio leído: pista Vulgata'); await p.keyboard.press('1'); await frames(1);
  await use(2,12,Math.PI/2); ok(await ev(()=>window.__LH.S.clues.includes('tele')),'teletipo leído'); await p.keyboard.press('1'); await frames(1);
  ok(await ev(()=>document.getElementById('hClue').textContent.startsWith('3/')),'contador de pistas en el HUD');
  // teclado
  await ev(()=>window.__LH.openKeypad()); for(const k of ['0','1','2','9'])await ev((k)=>window.__LH.keypadIn(k),k); await ev(()=>window.__LH.keypadIn('ok')); await frames(1);
  ok(await ev(()=>window.__LH.W.vaultOpen),'archivo abierto con 0129'); await frames(2); ok(await ev(()=>document.getElementById('hObj').textContent.includes('5/6')&&document.getElementById('hObj').textContent.includes('EXPEDIENTE')),'objetivo 5/6: coger el expediente');
  ok(await ev(()=>!!window.__LH.cut),'cinemática al abrir el archivo'); await ev(()=>window.__LH.cutSkip()); await wait(1500); await frames(2); await closeCodec(); await frames(1);
  await use(8,18,0); ok(await ev(()=>window.__LH.S.p.file),'expediente recogido'); await frames(2); ok(await ev(()=>document.getElementById('hObj').textContent.includes('6/6')&&document.getElementById('hObj').textContent.includes('SURESTE')),'objetivo 6/6: salir por la puerta sureste'); await p.keyboard.press('1'); await wait(1300); await frames(2); await closeCodec(); await frames(1);
  // cambio a Roig y vuelta: el inventario viaja con el control
  await ev(()=>window.__LH.swapChar()); await frames(2);
  ok(await ev(()=>window.__LH.S.p.name==='ROIG'&&window.__LH.S.p.file&&!window.__LH.S.c.file),'X cambia a Roig y el expediente va con ella');
  await ev(()=>window.__LH.swapChar()); await frames(2); ok(await ev(()=>window.__LH.S.p.name==='CUTTLAS'&&window.__LH.S.swaps===2),'X devuelve el control a Cuttlas');
  // Roig lucha sola: alarma con un guardia cerca de ella
  await ev(()=>{ const L=window.__LH; const g=L.S.guards.find(g=>g.name.includes('Peris')); L.S.p.x=g.x; L.S.p.z=g.z+5; L.S.c.x=g.x; L.S.c.z=g.z+3; L.S.c.ammo=12; L.raiseAlarm({x:g.x,z:g.z}); });
  await frames(4); await wait(1300); await frames(2); await closeCodec();
  await frames(44);
  ok(await ev(()=>window.__LH.S.teamKO>=1||window.__LH.S.c.ammo<12),'Roig dispara sola en la alerta (derribos de Roig: '+(await ev(()=>window.__LH.S.teamKO))+')');
  // salida
  await ev(()=>{ window.__LH.S.alertT=0; window.__LH.S.guards.forEach(g=>{g.state='patrol';}); }); await use(34,25,Math.PI); await frames(2);
  ok(await ev(()=>window.__LH.S.over===true&&!!window.__LH.cut),'salida sureste: cinemática final');
  await ev(()=>window.__LH.cutSkip()); await frames(2);
  ok(await ev(()=>!document.getElementById('end').hidden&&document.getElementById('end').textContent.includes('Roig')),'pantalla de final con estadísticas');
  await p.screenshot({path:path.resolve(__dirname,'shots','final.png')});
  ok(errs.length===0,'sin errores de consola '+(errs.length?JSON.stringify(errs):''));
  await b.close(); })();
