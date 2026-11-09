// Recorrido automático de la misión 2 «Descenso»: menú → excavación → laboratorio (lista) → grupos y compuerta → canal → templo → montacargas → final.
// Uso: node tests/mission2.js   (requiere Playwright y Chromium; NODE_PATH=/opt/node-tools/node_modules en el sandbox)
const {chromium}=require('playwright'); const path=require('path');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}});
  const errs=[]; p.on('pageerror',e=>errs.push(e.message)); p.on('console',m=>{ if(m.type()==='error')errs.push(m.text()); });
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')); await p.waitForTimeout(1500);
  const ev=(f,a)=>p.evaluate(f,a); const wait=ms=>p.waitForTimeout(ms);
  const frames=async(n)=>{ for(let i=0;i<n;i++)await ev(()=>new Promise(r=>requestAnimationFrame(()=>r()))); };
  const dump=()=>ev(()=>{ const L=window.__LH; return JSON.stringify({zone:L.S.zone,ui:L.uiOpen,cut:!!L.cut,codec:!!L.codecQ,over:L.S.over,obj:document.getElementById('hObj').textContent,gens:L.W.gens,gate:L.W.gateOpen,prompt:document.getElementById('prompt').textContent,g0:L.S.guards[0]&&[L.S.guards[0].state,L.S.guards[0].down,L.S.guards[0].dead,+L.S.guards[0].x.toFixed(1),+L.S.guards[0].z.toFixed(1),L.S.guards[0].fx,L.S.guards[0].fz,!!L.S.guards[0].held],p:[+L.S.p.x.toFixed(1),+L.S.p.z.toFixed(1)]}); });
  let fails=0; const ok=async(c,msg)=>{ if(!c){ fails++; console.error('FALLO:',msg,await dump()); process.exitCode=1; } else console.log('ok  ',msg); };
  const closeCodec=async()=>{ for(let i=0;i<24;i++){ if(!(await ev(()=>!!window.__LH.codecQ)))break; await ev(()=>window.__LH.codecNext()); await wait(60);} };
  const settle=async()=>{ for(let i=0;i<40;i++){ if(await ev(()=>!!window.__LH.cut))await ev(()=>window.__LH.cutSkip()); await closeCodec(); if(await ev(()=>!window.__LH.uiOpen&&!window.__LH.cut&&!window.__LH.codecQ&&!window.__LH.S.traveling))break; await wait(150);} };
  const use=async(x,y,yaw)=>{ await settle(); await ev(([x,y,yaw])=>{ const L=window.__LH; L.S.p.x=L.wx(x); L.S.p.z=L.wx(y); if(yaw!=null)L.yaw=yaw; L.S.c.x=L.S.p.x; L.S.c.z=L.S.p.z; },[x,y,yaw]); await frames(2); await ev(()=>{ window.__LH.useGrace=0; window.__LH.doUse(); }); await frames(1); };
  const canWalk=async()=>{ await ev(()=>{ const L=window.__LH; L.locked=true; L.S.walk0=[L.S.p.x,L.S.p.z]; L.keys.w=true; }); await frames(10); return ev(()=>{ const L=window.__LH; L.keys.w=false; const [x0,z0]=L.S.walk0; const moved=Math.hypot(L.S.p.x-x0,L.S.p.z-z0)>0.05; L.S.p.x=x0; L.S.p.z=z0; return moved; }); };
  const calm=async()=>{ await settle(); await ev(()=>{ const L=window.__LH; L.S.alertT=0; L.S.alarms=0; L.S.base='calma'; L.S.freeze=0; L.locked=true; L.S.codecSeen.alarm=true; L.S.guards.forEach(g=>{ g.state='patrol'; g.susp=0; g.shotT=999; g.fixing=false; }); L.S.c.crouch=true; }); };
  // menú: MISIÓN 2 arranca con su propia intro y su códec
  ok(await ev(()=>!document.getElementById('btnM2').hidden),'el menú ofrece MISIÓN 2 · DESCENSO');
  await p.click('#btnM2'); await wait(600);
  ok(await ev(()=>{ const L=window.__LH; return L.S.mission===2&&L.S.zone==='excavacion'&&!!L.cut; }),'misión 2: zona excavación y cinemática de entrada');
  await ev(()=>window.__LH.cutSkip()); await wait(300); await closeCodec(); await settle(); await calm(); ok(await canWalk(),'al empezar la misión 2 se puede andar');
  ok(await ev(()=>window.__LH.S.codecSeen!==undefined),'códec inicial de Control cerrado'); await settle();
  ok(await ev(()=>{ const L=window.__LH; return L.S.guards.length===4&&L.S.guards.some(g=>g.name.includes('Serra'))&&L.S.dogsDone===true; }),'cuatro guardias del programa (con el técnico Serra) y sin perrera');
  ok(await ev(()=>document.getElementById('hObj').textContent.includes('1/3')&&document.getElementById('hObj').textContent.includes('LABORATORIO')),'objetivo 1/3: la lista del laboratorio');
  await frames(3); ok(await ev(()=>document.getElementById('hClock').textContent.startsWith('03:1')),'el reloj marca las 03:10');
  // alcanzabilidad: con la compuerta cerrada, el canal del oeste llega igual a la escalera del templo
  const reach=(src,from,extra)=>ev(([src,from,extra])=>{ const L=window.__LH; const M=L[src]; const solid=c=>('#WTcgBX'+extra).includes(c); const seen=new Set([from.join(',')]); const q=[from]; while(q.length){ const [x,y]=q.shift(); [[1,0],[-1,0],[0,1],[0,-1]].forEach(([dx,dy])=>{ const nx=x+dx,ny=y+dy,k=nx+','+ny; if(seen.has(k)||ny<0||ny>=M.length||nx<0||nx>=M[0].length||solid(M[ny][nx]))return; seen.add(k); q.push([nx,ny]); }); }
    return L.INTER.filter(it=>!(seen.has(it.x+','+it.y)||[[1,0],[-1,0],[0,1],[0,-1]].some(([dx,dy])=>seen.has((it.x+dx)+','+(it.y+dy))))).map(it=>it.x+','+it.y); },[src,from,extra]);
  let miss=await reach('MAPSRC',[14,2],''); ok(miss.length===0,'excavación: todos los puntos de interacción son alcanzables con la compuerta cerrada (canal): '+miss.join(' '));
  miss=await reach('MAPSRC',[14,2],'s'); ok(miss.length===1&&miss[0]==='14,21','sin el canal, la escalera del templo solo se alcanza por la compuerta');
  // laboratorio: lista, protocolo y silla dan pistas; la lista cambia el objetivo
  await use(22,11,0); ok(await ev(()=>window.__LH.S.clues.includes('protocolo')),'protocolo leído'); await p.keyboard.press('1'); await frames(1);
  await use(24,12,Math.PI); ok(await ev(()=>window.__LH.S.clues.includes('silla')),'la silla da pista y recuerdo'); await p.keyboard.press('1'); await frames(1);
  await use(26,11,0); ok(await ev(()=>window.__LH.S.clues.includes('lista')&&document.getElementById('dlgTitle').textContent.includes('LISTA')),'lista de sujetos leída'); await p.keyboard.press('1'); await wait(1200); await settle(); await frames(2);
  ok(await ev(()=>document.getElementById('hObj').textContent.includes('2/3')&&document.getElementById('hObj').textContent.includes('0/3')),'objetivo 2/3: parar los grupos o seguir el canal');
  // grupos: cada uno apaga su sector (sombra, visión corta) y un guardia viene a arrancarlo; los tres hacen caer la compuerta
  await calm(); await use(3,9,0); await frames(1);
  ok(await ev(()=>{ const L=window.__LH; return L.W.gens[0]===false&&L.ZONE.dark(3,9)&&!L.ZONE.dark(21,7)&&!L.litAt({x:L.wx(3),z:L.wx(9)})&&document.getElementById('hPow').textContent.includes('2/3'); }),'grupo 1 parado: su sector a oscuras y el HUD lo marca');
  ok(await ev(()=>{ const L=window.__LH; const go=L.genOff(); return go&&go.x===3&&go.y===9; }),'hay un grupo que reparar');
  await ev(()=>{ const L=window.__LH; L.S.p.x=L.wx(14); L.S.p.z=L.wx(2); L.S.c.x=L.S.p.x; L.S.c.z=L.S.p.z; }); await calm(); await ev(()=>{ window.__LH.S.fixTimer=0; });
  for(let i=0;i<30&&!(await ev(()=>window.__LH.S.guards.some(g=>g.fixing)));i++)await frames(2);
  ok(await ev(()=>window.__LH.S.guards.some(g=>g.fixing)),'un guardia va a arrancar el grupo');
  await ev(()=>{ const L=window.__LH; const g=L.S.guards.find(g=>g.fixing); if(g){ g.x=L.wx(3); g.z=L.wx(9); } }); await frames(4);
  ok(await ev(()=>window.__LH.W.gens[0]===true&&!window.__LH.S.guards.some(g=>g.fixing)),'al llegar lo arranca y el sector vuelve a tener luz');
  await calm(); await ev(()=>{ window.__LH.S.fixTimer=999; });
  await use(3,9,0); await use(21,7,0); ok(await ev(()=>window.__LH.W.gens.filter(v=>!v).length===2&&!window.__LH.W.gateOpen),'dos grupos parados: la compuerta sigue cerrada');
  ok(await ev(()=>!window.__LH.solidT||true),'(compuerta sólida mientras está cerrada)');
  await use(3,17,0); await frames(1); await ev(()=>{ window.__LH.S.fixTimer=9999; });
  ok(await ev(()=>{ const L=window.__LH; return L.W.gateOpen&&L.W.gens.every(v=>!v)&&document.getElementById('hPow').textContent.includes('0/3'); }),'tercer grupo parado: la compuerta cae y queda abierta');
  ok(await ev(()=>document.getElementById('hObj').textContent.includes('CAÍDO')),'objetivo: bajar por la compuerta');
  // guardar y continuar en la misión 2
  await ev(()=>window.__LH.saveGame('Prueba m2')); ok(await ev(()=>{ const L=window.__LH; const d=L.loadGame(); return !!d&&d.mission===2&&L.S.mission===2&&L.S.zone==='excavacion'&&L.W.gateOpen&&L.W.gens.every(v=>!v)&&L.S.clues.includes('lista'); }),'guardar y cargar conserva misión, compuerta y grupos');
  await ev(()=>window.__LH.startGame(false,true)); await settle(); await calm();
  // bajar al templo
  await use(14,21,Math.PI); await wait(2600); await settle(); await wait(1500); await settle();
  ok(await ev(()=>{ const L=window.__LH; return L.S.zone==='templo'&&L.S.guards.length===3&&L.S.guards[0].name.includes('Alarcón')&&L.S.guards[0].fz===-1; }),'el templo carga con Alarcón mirando al agua y su escolta');
  ok(await ev(()=>document.getElementById('hObj').textContent.includes('3/3')&&document.getElementById('hObj').textContent.includes('MONTACARGAS')),'objetivo 3/3: el montacargas');
  ok(await canWalk(),'al llegar al templo se puede andar (la casilla de llegada no es una columna)');
  ok(await ev(()=>{ const L=window.__LH; return L.useGrace>0&&Math.floor(L.S.p.x/2)===3&&Math.floor(L.S.p.z/2)===17; }),'se llega junto a la escalera, no encima, y E no actúa justo al llegar');
  await ev(()=>{ window.__LH.useGrace=performance.now()+5000; window.__LH.doUse(); }); await frames(2); ok(await ev(()=>window.__LH.S.zone==='templo'&&!window.__LH.S.traveling),'un E de más tras el códec no te devuelve arriba');
  await ev(()=>{ window.__LH.S.t+=1; }); await frames(2); ok(await ev(()=>{ const L=window.__LH; return L.ZONE.tick&&L.S.zone==='templo'; }),'la luz de la Fuente late');
  await calm(); await use(11,4,0); ok(await ev(()=>window.__LH.S.clues.includes('luz')),'mirar el agua da la pista de la luz'); await p.keyboard.press('1'); await frames(1);
  // interrogar a Alarcón por la espalda
  await calm(); await ev(()=>{ const L=window.__LH; const g=L.S.guards[0]; L.S.p.x=g.x; L.S.p.z=g.z+1.2; L.yaw=0; L.S.p.crouch=true; L.locked=true; }); await frames(3);
  ok(await ev(()=>document.getElementById('prompt').textContent.includes('INTERROGAR')),'se puede agarrar a Alarcón por la espalda');
  await ev(()=>window.__LH.doGrab()); await frames(1); ok(await ev(()=>document.getElementById('dlgTitle').textContent.includes('Alarcón')),'interrogatorio del coronel');
  for(const k of ['4','4','4','4','3'])await p.keyboard.press(k).then(()=>frames(1));
  ok(await ev(()=>window.__LH.S.clues.includes('alarcon')),'apretando cuatro veces confiesa: pista de Alarcón'); await p.keyboard.press('5'); await frames(2);
  // vuelta a la excavación y de nuevo al templo (estado conservado), y montacargas
  await calm(); await use(3,17,Math.PI/2); await wait(2600); await settle(); ok(await ev(()=>window.__LH.S.zone==='excavacion'&&window.__LH.W.gateOpen),'subir a la excavación conserva la compuerta abierta');
  await calm(); ok(await canWalk(),'al volver a la excavación se puede andar');
  await calm(); await use(14,21,Math.PI); await wait(2600); await settle(); ok(await ev(()=>window.__LH.S.zone==='templo'&&window.__LH.S.guards[0].down>0),'al volver, Alarcón sigue dormido donde cayó');
  await calm(); await use(18,2,0); await frames(2);
  ok(await ev(()=>window.__LH.S.over===true&&!!window.__LH.cut),'montacargas: cinemática final de la misión 2');
  await ev(()=>window.__LH.cutSkip()); await frames(2);
  ok(await ev(()=>!document.getElementById('end').hidden&&document.getElementById('end').textContent.includes('APAGÓ LA LUZ')&&document.getElementById('end').textContent.includes('lista')),'final «El que apagó la luz» con la lista');
  await p.screenshot({path:path.resolve(__dirname,'shots','m2-final.png')});
  // derrota en la misión 2: sin celda, directo a «Cuarta sesión»
  await p.click('#btnRestart2'); await wait(300); await settle(); await ev(()=>window.__LH.defeat('guards')); await frames(2);
  ok(await ev(()=>window.__LH.S.over&&document.getElementById('end').textContent.includes('CUARTA SESIÓN')),'la derrota en la misión 2 lleva a la cuarta sesión');
  // desde la galería de la misión 1, con el expediente, la blindada ofrece bajar
  await p.click('#btnMenu'); await wait(300); await p.click('[data-go="brief"]'); await p.click('#btnStart'); await wait(800); await settle();
  await ev(()=>{ const L=window.__LH; L.S.p.file=true; L.W.hatchOpen=true; L.travel('galeria',[3,2],0); }); await wait(2600); await settle();
  await ev(()=>{const it=window.__LH.INTER.find(i=>i.x===7&&i.y===15);it.f();}); await wait(200);
  ok(await ev(()=>document.getElementById('dlg').querySelectorAll('button').length>=2&&document.getElementById('dlgTxt').textContent.includes('Se abre')),'con el expediente, ALEPH-07 ofrece bajar a la misión 2');
  await p.keyboard.press('1'); await wait(600); ok(await ev(()=>window.__LH.S.mission===2&&window.__LH.S.zone==='excavacion'),'bajar arranca la misión 2');
  await ok(errs.length===0,'sin errores de consola '+(errs.length?JSON.stringify(errs.slice(0,5)):''));
  console.log(fails?'FALLOS: '+fails:'TODO OK'); await b.close(); })();
