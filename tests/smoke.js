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
  const dump=()=>p.evaluate(()=>{ const L=window.__LH, g=L.S.guards[0]; return JSON.stringify({g0:[g.state,+g.susp.toFixed(2),+g.x.toFixed(1),+g.z.toFixed(1),g.down,g.dead],alarms:L.S.alarms,alertT:+(L.S.alertT||0).toFixed(1),ui:L.uiOpen,cut:!!L.cut,codec:!!L.codecQ,p:[+L.S.p.x.toFixed(1),+L.S.p.z.toFixed(1),L.S.p.disguise],prompt:document.getElementById('prompt').textContent}); });
  const ok=async(c,msg)=>{ if(!c){ console.error('FALLO:',msg,await dump()); process.exitCode=1; } else console.log('ok  ',msg); };
  ok(await p.evaluate(()=>!!window.__LH),'motor cargado y estado expuesto');
  await p.click('[data-go="brief"]'); await p.click('#btnStart'); await p.waitForTimeout(800);
  await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(400);
  const closeCodec=async()=>{ for(let i=0;i<24;i++){ if(!(await p.evaluate(()=>!!window.__LH.codecQ)))break; await p.evaluate(()=>window.__LH.codecNext()); await p.waitForTimeout(60);} };
  const settle=async()=>{ for(let i=0;i<30;i++){ await closeCodec(); if(await p.evaluate(()=>!window.__LH.uiOpen&&!window.__LH.cut&&!window.__LH.codecQ))break; await p.waitForTimeout(150);} };
  await settle();
  ok(await p.evaluate(()=>window.__LH.S.guards.length>0),'guardias creados');
  // vigilante de rendimiento: con frames lentos baja la calidad por pasos
  ok(await p.evaluate(()=>{ const L=window.__LH; for(let i=0;i<60;i++)L.perfWatch(0.1); const a=L.perfStep; for(let i=0;i<60;i++)L.perfWatch(0.1); return a===1&&L.perfStep===2&&L.OPT.shadows===false; }),'si va lento, baja la resolución y luego quita las sombras solo');
  ok(await p.evaluate(()=>{ const L=window.__LH; const M=L.MAPSRC.map(r=>r.split('')); const solid=c=>'#WTcg'.includes(c); const seen=new Set(); const q=[[2,2]]; seen.add('2,2'); while(q.length){ const [x,y]=q.shift(); [[1,0],[-1,0],[0,1],[0,-1]].forEach(([dx,dy])=>{ const nx=x+dx,ny=y+dy; const k=nx+','+ny; if(nx<0||ny<0||ny>=M.length||nx>=M[0].length||seen.has(k)||solid(M[ny][nx]))return; seen.add(k); q.push([nx,ny]); }); }
    return L.INTER.every(it=>seen.has(it.x+','+it.y)||[[1,0],[-1,0],[0,1],[0,-1]].some(([dx,dy])=>seen.has((it.x+dx)+','+(it.y+dy)))); }),'todos los puntos de interacción (teclado, puertas, pistas) son alcanzables: ninguna caja los tapa');
  await p.evaluate(()=>{window.__LH.third=true;}); await p.waitForTimeout(300);
  // órdenes a Roig: por defecto espera; G la hace seguir
  const frames=async(n)=>{ for(let i=0;i<n;i++)await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>r()))); };
  await p.evaluate(()=>{ const L=window.__LH; L.locked=true; L.S.guards.forEach(g=>{ g.state='patrol'; g.susp=0; g.wps=[[Math.floor(g.x/2),Math.floor(g.z/2)]]; g.wi=0; }); L.S.c.x=L.wx(2); L.S.c.z=L.wx(8); L.S.c.crouch=false; });
  await frames(30);
  ok(await p.evaluate(()=>{ const L=window.__LH; return L.S.cOrder==='wait'&&Math.abs(L.S.c.z-L.wx(8))<0.05&&L.S.c.crouch===true; }),'Roig espera agachada donde está si no se le ordena nada');
  await p.keyboard.press('g'); await frames(30);
  ok(await p.evaluate(()=>{ const L=window.__LH; return L.S.cOrder==='follow'&&L.S.orders===1&&L.S.c.z<L.wx(8)-0.5; }),'G ordena seguir y Roig se acerca');
  await p.keyboard.press('g'); await frames(2); ok(await p.evaluate(()=>window.__LH.S.cOrder==='wait'),'G otra vez: vuelve a esperar');
  // distancias: visto de lejos duda y se acerca, de cerca alarma; silenciador; uniforme
  const setup=async(gd)=>{ await settle(); await p.evaluate((gd)=>{ const L=window.__LH; L.S.codecSeen.alarm=true; L.S.p.hp=5; L.S.alertT=0; L.S.guards.forEach(g=>{ g.shotT=999; }); L.S.alarms=0; L.S.base='calma'; L.S.c.x=L.wx(2); L.S.c.z=L.wx(26); L.S.c.crouch=true; L.S.c.ammo=0; L.S.guards.forEach(g=>{ g.state='patrol'; g.susp=0; g.doubtT=0; g.down=0; g.held=false; g.wps=[[Math.floor(g.x/2),Math.floor(g.z/2)]]; g.wi=0; });
    L.S.guards.forEach((g,i)=>{ if(i===0)return; g.x=L.wx(24+(i%8)); g.z=L.wx(29); g.fx=0; g.fz=1; g.wps=[[24+(i%8),29]]; g.wi=0; g.fig.g.position.set(g.x,0,g.z); });
    const g=L.S.guards[0]; g.x=L.wx(2); g.z=L.wx(2)+gd; g.fx=0; g.fz=-1; g.wps=[[2,Math.floor(g.z/2)]]; g.state='patrol'; L.S.p.x=L.wx(2); L.S.p.z=L.wx(2); L.S.p.crouch=false; L.yaw=Math.PI; },gd); };
  await setup(10); await frames(12);
  ok(await p.evaluate(()=>{ const L=window.__LH; const g=L.S.guards[0]; return g.state==='suspect'&&L.S.alarms===0&&g.doubtT>0; }),'visto a 10 m: el guardia duda, sin alarma');
  await frames(60);
  ok(await p.evaluate(()=>{ const L=window.__LH; const g=L.S.guards[0]; return g.z<L.wx(2)+9.5; }),'tras dudar, se acerca a mirar');
  await setup(6); await frames(70);
  ok(await p.evaluate(()=>{ const L=window.__LH; return L.S.alarms===1; }),'visto a 6 m: alarma');
  ok(await p.evaluate(()=>document.getElementById('hState').textContent.startsWith('ALARMA')),'el HUD muestra la cuenta atrás de la alarma');
  // escondido: la alarma caduca, buscan un poco y la base vuelve a la calma
  await p.evaluate(()=>{ const L=window.__LH; L.S.p.x=L.wx(2); L.S.p.z=L.wx(26); L.S.p.crouch=true; L.S.alertT=0.6; }); await frames(240);
  ok(await p.evaluate(()=>{ const L=window.__LH; return L.S.alertT<=0&&L.S.base==='calma'&&L.S.guards.every(g=>g.dead||g.down>0||g.state==='patrol')&&document.getElementById('hState').textContent==='CALMA'; }),'sin que te vean, la alarma se apaga y la base vuelve a la calma');
  // silenciador: disparo sin alarma
  await setup(6); await p.evaluate(()=>{ const L=window.__LH; const g=L.S.guards[0]; g.fx=0; g.fz=1; L.S.p.ammo=8; L.S.silencer=false; L.keys&&(L.keys.length=0); }); await p.keyboard.press('t'); await frames(1);
  ok(await p.evaluate(()=>window.__LH.S.silencer===true&&document.getElementById('hAmmo').textContent.includes('SIL')),'T pone el silenciador y lo marca el HUD');
  await p.evaluate(()=>{ const L=window.__LH; L.yaw=Math.PI; L.pitch=0.8; const g=L.S.guards[0]; g.fx=0; g.fz=1; g.susp=0; g.state='patrol'; L.shoot(); });
  ok(await p.evaluate(()=>{ const L=window.__LH; return L.S.alarms===0&&L.S.p.ammo===7; }),'disparo con silenciador: nadie da la alarma');
  await p.evaluate(()=>{ const L=window.__LH; L.S.silencer=false; L.S.p.ammo=8; L.shoot(); });
  ok(await p.evaluate(()=>window.__LH.S.alarms===1),'disparo sin silenciador: alarma');
  // uniforme: dormir a un guardia, quitárselo, y comprobar la distancia de 3 m
  await setup(2); await p.evaluate(()=>{ const L=window.__LH; L.S.bodies.forEach(b=>{ b.x=L.wx(2); b.z=L.wx(26); }); const g=L.S.guards[2]; g.x=L.wx(2); g.z=L.wx(2)+2; g.wps=[[2,Math.floor(g.z/2)]]; g.wi=0; L.knock(g,false); L.S.p.x=g.x; L.S.p.z=g.z+1; L.S.alertT=0; L.S.alarms=0; });
  await frames(40); ok(await p.evaluate(()=>document.getElementById('prompt').textContent.includes('UNIFORME')),'aviso E · QUITARLE EL UNIFORME junto al caído');
  await p.evaluate(()=>window.__LH.doUse()); await frames(1);
  ok(await p.evaluate(()=>{ const L=window.__LH; return L.S.p.disguise===true&&L.S.p.fig===L.S.p.figU&&L.S.p.figBase.g.visible===false&&!document.getElementById('hDis').hidden; }),'uniforme puesto: figura de tropa y HUD');
  await p.evaluate(()=>{ const L=window.__LH; L.S.alertT=0; L.S.alarms=0; const g=L.S.guards[1]; g.x=L.wx(2); g.z=L.wx(2)+5; g.fx=0; g.fz=-1; g.wps=[[2,Math.floor(g.z/2)]]; g.wi=0; g.state='patrol'; g.susp=0; L.S.p.x=L.wx(2); L.S.p.z=L.wx(2); L.S.p.crouch=false; }); await frames(30);
  ok(await p.evaluate(()=>{ const L=window.__LH; return L.S.alarms===0&&L.S.guards[1].state==='patrol'; }),'con uniforme a 5 m: ni se inmuta');
  await p.evaluate(()=>{ const L=window.__LH; const g=L.S.guards[1]; g.z=L.wx(2)+2.5; g.wps=[[2,Math.floor(g.z/2)]]; }); await frames(70);
  ok(await p.evaluate(()=>{ const L=window.__LH; return L.S.alarms===1&&L.S.p.disguise===false; }),'con uniforme a 2,5 m: alarma y te calan');
  await settle(); await p.evaluate(()=>{ const L=window.__LH; L.S.alertT=0; L.S.alarms=0; L.S.base='calma'; L.S.guards.forEach(g=>{ g.state='patrol'; g.susp=0; }); L.S.guards[0].down=0; L.S.p.hp=5; });
  ok(await p.evaluate(()=>{ const L=window.__LH; const g=L.S.guards.find(g=>!g.dead&&g.down<=0); const ox=g.x,oz=g.z; g.state='search'; g.x=L.S.c.x+1.5; g.z=L.S.c.z; const t=L.teamThreat(L.S.c); g.state='alert'; const t2=L.teamThreat(L.S.c); g.state='patrol'; g.x=ox; g.z=oz; return !t&&t2===g; }),'solo considera amenaza a un guardia en alerta, no a uno que busca');
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
  ok(await p.evaluate(()=>{ const L=window.__LH; L.music.init(); L.S.alertT=5; L.music.tick(0.1); const a=L.music.cur==='accion'; L.S.alertT=0; L.music.tick(0.1); return a&&L.music.cur==='sigilo'&&!!L.music.tracks.accion&&!!document.getElementById('oMusic'); }),'música: tema de acción con la alarma, sigilo al calmarse, control de volumen en opciones');
  // guardado y continuar
  await p.evaluate(()=>{ const L=window.__LH; L.S.p.x=L.wx(20); L.S.p.z=L.wx(20); L.saveGame('Prueba'); L.S.p.x=0; L.S.p.z=0; L.S.clues.length=0; });
  ok(await p.evaluate(()=>{ const L=window.__LH; const d=L.loadGame(); return !!d&&d.tag==='Prueba'&&Math.abs(L.S.p.x-L.wx(20))<0.01&&L.S.clues.includes('fuente')&&L.W.cellOpen&&!L.S.inCell; }),'cargar la partida recupera posición, pistas y celda abierta');
  await p.evaluate(()=>window.__LH.showMenu('main')); ok(await p.evaluate(()=>!document.getElementById('btnContinue').hidden&&document.getElementById('btnContinue').textContent.includes('Prueba')),'CONTINUAR aparece en el menú con la etiqueta del guardado');
  await p.click('#btnContinue'); await p.waitForTimeout(400); ok(await p.evaluate(()=>document.getElementById('ov').hidden&&window.__LH.started),'CONTINUAR reanuda la partida');
  // segunda derrota: fin de partida con continuidad
  await p.evaluate(()=>window.__LH.defeat('guards')); await p.waitForTimeout(400);
  ok(await p.evaluate(()=>window.__LH.S.over&&!document.getElementById('end').hidden&&document.getElementById('end').textContent.includes('CUARTA SESIÓN')&&document.getElementById('end').textContent.includes('CUTTLAAAAAS')),'segunda captura: pantalla de derrota CUARTA SESIÓN con el grito del códec');
  ok(await p.evaluate(()=>!document.getElementById('btnAgain').hidden),'botón ÚLTIMO PUNTO disponible');
  // nueva partida tras la derrota: la celda vuelve a estar disponible
  await p.evaluate(()=>document.getElementById('btnRestart2').click()); await p.waitForTimeout(300); await settle();
  ok(await p.evaluate(()=>!window.__LH.S.capturedOnce&&!window.__LH.S.over&&!window.__LH.S.inCell),'DESDE EL PRINCIPIO limpia la marca de captura');
  await p.evaluate(()=>window.__LH.defeat('guards')); await p.waitForTimeout(300);
  ok(await p.evaluate(()=>!!window.__LH.cut&&!window.__LH.S.over),'en la nueva partida la primera captura vuelve a llevar a la celda, no a CUARTA SESIÓN');
  await p.evaluate(()=>window.__LH.cutSkip()); await p.waitForTimeout(2900); await settle(); await p.waitForTimeout(300);
  ok(await p.evaluate(()=>window.__LH.S.inCell===true&&!window.__LH.S.over),'nueva partida: de nuevo en la celda');
  // Vidal sin espera: tres fallos no acaban la partida; la llave de la losa abre la reja
  const vid=()=>p.evaluate(()=>{const it=window.__LH.INTER.find(i=>i.x===31&&i.y===12);it.f();});
  await vid(); await p.waitForTimeout(300); await press('1'); await press('1');
  ok(await p.evaluate(()=>window.__LH.S.vidal.fail===1&&!window.__LH.S.vidal.cool&&document.getElementById('dlg').hidden),'fallar con Vidal no impone espera');
  await vid(); await p.waitForTimeout(300); await press('1'); await press('1'); await vid(); await p.waitForTimeout(300); await press('1'); await press('1');
  ok(await p.evaluate(()=>window.__LH.S.vidal.fail===3&&window.__LH.S.vidal.gone&&!window.__LH.S.over&&window.__LH.S.inCell),'tres fallos: Vidal deja de escuchar pero no es fin de partida');
  await p.evaluate(()=>{const it=window.__LH.INTER.find(i=>i.x===30&&i.y===13);it.f();}); await p.waitForTimeout(300); await press('1');
  ok(await p.evaluate(()=>window.__LH.S.cellKey===true),'la losa suelta esconde la llave');
  await vid(); await p.waitForTimeout(400);
  ok(await p.evaluate(()=>window.__LH.W.cellOpen&&!window.__LH.S.inCell&&window.__LH.S.p.ammo===0&&!window.__LH.S.over),'la llave abre la reja y se vuelve a la misión (sin balas)');
  ok(await p.evaluate(()=>{ const t=document.getElementById('hObj').textContent; return t.includes('2/6')&&t.includes('IBARRA'); }),'el HUD arranca con el objetivo 2/6: la llave de Ibarra');
  ok(await p.evaluate(()=>{ const it=window.__LH.INTER.find(i=>i.x===20&&i.y===26); if(!it)return false; it.f(); const ok=!document.getElementById('dlg').hidden&&document.getElementById('dlgTxt').textContent.includes('siguiente misión'); return ok; }),'la compuerta de la excavación existe y explica que es la misión 2');
  await p.keyboard.press('1'); await p.waitForTimeout(200);
  ok(await p.evaluate(()=>typeof WEAK_GPU!=='undefined'&&WEAK_GPU===true&&window.__LH.OPT.shadows===false&&window.__LH.OPT.post===false&&typeof SIMPLE_FIG!=='undefined'&&SIMPLE_FIG===true),'gráfica por software detectada: arranca en modo ligero con personajes sencillos');
  ok(await p.evaluate(()=>!!document.getElementById('oSimple')&&typeof figureBox==='function'&&'simpleFig' in window.__LH.OPT),'opción de personajes sencillos disponible');
  await p.screenshot({path:path.resolve(__dirname,'last.png')});
  ok(errs.length===0,'sin errores de consola '+(errs.length?JSON.stringify(errs):''));
  await b.close();
})();
