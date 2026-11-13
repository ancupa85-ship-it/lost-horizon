// Recorrido automático de la misión 3 «Tarsis»: menú → torre (lista completa, gasolina, archivo en llamas, radio) → perímetro → los cuatro finales,
// derrota, guardado, encadenado desde el final de la misión 2 (estado heredado) y alcanzabilidad de los dos planos.
// Uso: node tests/mission3.js   (requiere Playwright y Chromium; NODE_PATH=/opt/node-tools/node_modules en el sandbox)
const {chromium}=require('playwright'); const path=require('path');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}});
  const errs=[]; p.on('pageerror',e=>errs.push(e.message)); p.on('console',m=>{ if(m.type()==='error')errs.push(m.text()); });
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')); await p.waitForTimeout(1500);
  const ev=(f,a)=>p.evaluate(f,a); const wait=ms=>p.waitForTimeout(ms);
  const frames=async(n)=>{ for(let i=0;i<n;i++)await ev(()=>new Promise(r=>requestAnimationFrame(()=>r()))); };
  const dump=()=>ev(()=>{ const L=window.__LH; return JSON.stringify({zone:L.S.zone,mission:L.S.mission,ui:L.uiOpen,cut:!!L.cut,codec:!!L.codecQ,over:L.S.over,ending:L.S.ending,obj:document.getElementById('hObj').textContent,power:L.W.power,burned:L.W.burned,gas:L.S.gas,prompt:document.getElementById('prompt').textContent,end:document.getElementById('end').hidden?'':document.getElementById('end').textContent.slice(0,120)}); });
  let fails=0; const ok=async(c,msg)=>{ if(!c){ fails++; console.error('FALLO:',msg,await dump()); process.exitCode=1; } else console.log('ok  ',msg); };
  const closeCodec=async()=>{ for(let i=0;i<24;i++){ if(!(await ev(()=>!!window.__LH.codecQ)))break; await ev(()=>window.__LH.codecNext()); await wait(60);} };
  const settle=async()=>{ for(let i=0;i<40;i++){ if(await ev(()=>!!window.__LH.cut))await ev(()=>window.__LH.cutSkip()); await closeCodec(); if(await ev(()=>!window.__LH.uiOpen&&!window.__LH.cut&&!window.__LH.codecQ&&!window.__LH.S.traveling))break; await wait(150);} };
  const use=async(x,y,yaw)=>{ await settle(); await ev(([x,y,yaw])=>{ const L=window.__LH; L.S.p.x=L.wx(x); L.S.p.z=L.wx(y); if(yaw!=null)L.yaw=yaw; L.S.c.x=L.S.p.x; L.S.c.z=L.S.p.z; },[x,y,yaw]); await frames(2); await ev(()=>{ window.__LH.useGrace=0; window.__LH.doUse(); }); await frames(1); };
  const canWalk=async()=>{ await ev(()=>{ const L=window.__LH; L.locked=true; L.S.walk0=[L.S.p.x,L.S.p.z]; L.keys.w=true; }); await frames(10); return ev(()=>{ const L=window.__LH; L.keys.w=false; const [x0,z0]=L.S.walk0; const moved=Math.hypot(L.S.p.x-x0,L.S.p.z-z0)>0.05; L.S.p.x=x0; L.S.p.z=z0; return moved; }); };
  const calm=async()=>{ await settle(); await ev(()=>{ const L=window.__LH; L.S.alertT=0; L.S.alarms=0; L.S.base='calma'; L.S.freeze=0; L.locked=true; L.S.codecSeen.alarm=true; L.S.guards.forEach(g=>{ g.state='patrol'; g.susp=0; g.shotT=999; g.fixing=false; }); L.S.c.crouch=true; }); };
  const endText=()=>ev(()=>document.getElementById('end').hidden?'':document.getElementById('end').textContent);
  const reach=(from,extra)=>ev(([from,extra])=>{ const L=window.__LH; const M=L.MAPSRC; const solid=c=>('#WTcgBX'+extra).includes(c); const seen=new Set([from.join(',')]); const q=[from]; while(q.length){ const [x,y]=q.shift(); [[1,0],[-1,0],[0,1],[0,-1]].forEach(([dx,dy])=>{ const nx=x+dx,ny=y+dy,k=nx+','+ny; if(seen.has(k)||ny<0||ny>=M.length||nx<0||nx>=M[0].length||solid(M[ny][nx]))return; seen.add(k); q.push([nx,ny]); }); }
    return L.INTER.filter(it=>!(seen.has(it.x+','+it.y)||[[1,0],[-1,0],[0,1],[0,-1]].some(([dx,dy])=>seen.has((it.x+dx)+','+(it.y+dy))))).map(it=>it.x+','+it.y); },[from,extra]);
  // menú: MISIÓN 3 arranca con su intro y su códec
  ok(await ev(()=>!document.getElementById('btnM3').hidden),'el menú ofrece MISIÓN 3 · TARSIS');
  await p.click('#btnM3'); await wait(600);
  ok(await ev(()=>{ const L=window.__LH; return L.S.mission===3&&L.S.zone==='torre'&&!!L.cut; }),'misión 3: zona torre y cinemática de entrada');
  await ev(()=>window.__LH.cutSkip()); await wait(300); await closeCodec(); await settle(); await calm(); ok(await canWalk(),'al empezar la misión 3 se puede andar');
  ok(await ev(()=>{ const L=window.__LH; return L.S.guards.length===7&&L.S.guards.some(g=>g.name.includes('Ocaña'))&&L.S.dogsDone===true&&L.ZONE.outdoor; }),'siete guardias en la torre (con el sargento Ocaña), exterior, sin perrera');
  ok(await ev(()=>document.getElementById('hObj').textContent.includes('1/3')&&document.getElementById('hObj').textContent.includes('ARCHIVO')),'objetivo 1/3: la lista completa del archivo');
  await frames(3); ok(await ev(()=>document.getElementById('hClock').textContent.startsWith('03:4')),'el reloj marca las 03:40');
  ok(await ev(()=>document.getElementById('guide').hidden),'sin guía de novato en la misión 3');
  let miss=await reach([2,20],''); ok(miss.length===0,'torre: todos los puntos de interacción son alcanzables: '+miss.join(' '));
  // montacargas: no baja
  await use(2,20,0); ok(await ev(()=>document.getElementById('dlgTitle').textContent.includes('MONTACARGAS')),'el montacargas ya no baja'); await p.keyboard.press('1'); await frames(1);
  // sin gasolina no se puede quemar; la gasolina está en el depósito del este
  await use(11,4,0); ok(await ev(()=>!window.__LH.uiOpen&&!window.__LH.W.burned),'sin gasolina el archivo no se puede quemar');
  await ev(()=>{ const L=window.__LH; L.S.p.x=L.wx(11); L.S.p.z=L.wx(4); L.locked=true; }); await frames(2); ok(await ev(()=>document.getElementById('prompt').textContent.includes('GASOLINA')),'el aviso explica que hace falta gasolina');
  await use(23,6,0); ok(await ev(()=>window.__LH.S.gas===true&&window.__LH.S.clues.includes('gasolina')),'gasolina cogida del depósito');
  await ev(()=>{ const L=window.__LH; L.S.p.x=L.wx(23); L.S.p.z=L.wx(6); L.locked=true; }); await frames(2); ok(await ev(()=>document.getElementById('prompt').textContent===''||!document.getElementById('prompt').textContent.includes('GASOLINA')),'el depósito ya no ofrece más gasolina');
  // la lista completa
  await use(8,4,0); ok(await ev(()=>window.__LH.S.clues.includes('lista3')&&document.getElementById('dlgTitle').textContent.includes('LISTA COMPLETA')),'lista completa leída'); await p.keyboard.press('1'); await wait(1200); await settle(); await frames(2);
  ok(await ev(()=>document.getElementById('hObj').textContent.includes('2/3')&&document.getElementById('hObj').textContent.includes('PUERTA ESTE')),'objetivo 2/3: salir por la puerta este');
  // la radio: colgar no entrega
  await use(16,4,0); ok(await ev(()=>document.getElementById('dlgTitle').textContent.includes('RADIO')&&window.__LH.S.clues.includes('radio')),'la radio ofrece entregarse'); await p.keyboard.press('2'); await frames(1); ok(await ev(()=>!window.__LH.S.over&&!window.__LH.uiOpen),'colgar no acaba la partida');
  // guardar y cargar conserva gasolina y lista
  await ev(()=>window.__LH.saveGame('Prueba m3')); ok(await ev(()=>{ const L=window.__LH; const d=L.loadGame(); return !!d&&d.mission===3&&L.S.mission===3&&L.S.zone==='torre'&&L.S.gas===true&&L.S.clues.includes('lista3'); }),'guardar y cargar conserva misión 3, gasolina y lista');
  await ev(()=>window.__LH.startGame(false,true)); await settle(); await calm();
  ok(await ev(()=>{ const L=window.__LH; L.showMenu('main'); const t=document.getElementById('btnContinue').innerHTML; document.getElementById('ov').hidden=true; document.getElementById('menu').hidden=true; return t.includes('Misión 3'); }),'CONTINUAR anuncia la misión 3');
  // quemar el archivo: alarma, llamas y a los cinco segundos se va la luz (y nadie la arregla)
  await use(11,4,0); ok(await ev(()=>document.getElementById('dlgTitle').textContent.includes('QUEMAR')),'confirmación antes de quemar'); await p.keyboard.press('1'); await frames(2);
  ok(await ev(()=>{ const L=window.__LH; return L.W.burned&&L.S.alarms>=1&&L.S.clues.includes('fuego')&&L.W.power; }),'el archivo arde: alarma, pista, la luz aún encendida');
  await settle(); await calm(); await ev(()=>{ window.__LH.S.burnT=0.01; }); await frames(4);
  ok(await ev(()=>{ const L=window.__LH; return !L.W.power&&L.genOff()===null; }),'el fuego llega al cuadro: se va la luz y ningún guardia la repara');
  ok(await ev(()=>document.getElementById('hObj').textContent.includes('ARDE')),'el objetivo refleja el incendio');
  await calm(); await ev(()=>{ const L=window.__LH; L.S.p.x=L.wx(8); L.S.p.z=L.wx(4); L.locked=true; }); await frames(2); ok(await ev(()=>document.getElementById('prompt').textContent===''),'la lista ya leída no se vuelve a ofrecer');
  // al perímetro
  await calm(); await use(27,11,-Math.PI/2); await wait(2600); await settle(); await wait(1500); await settle();
  ok(await ev(()=>{ const L=window.__LH; return L.S.zone==='perimetro'&&L.S.guards.length===4&&L.ZONE.outdoor&&!L.W.power; }),'el perímetro carga con sus cuatro guardias y sigue a oscuras');
  ok(await ev(()=>document.getElementById('hObj').textContent.includes('3/3')&&document.getElementById('hObj').textContent.includes('CARRETERA')),'objetivo 3/3: elegir la salida');
  await calm(); ok(await canWalk(),'al llegar al perímetro se puede andar');
  await ev(()=>{ window.__LH.useGrace=performance.now()+5000; window.__LH.doUse(); }); await frames(2); ok(await ev(()=>window.__LH.S.zone==='perimetro'&&!window.__LH.S.traveling),'un E de más al llegar no te devuelve a la torre');
  miss=await reach([1,8],''); ok(miss.length===0,'perímetro: todo alcanzable por la verja: '+miss.join(' '));
  miss=await ev(()=>{ const L=window.__LH; const M=L.MAPSRC; const solid=(x,y)=>'#WTcgBX'.includes(M[y][x])||(x===5&&y===8); const seen=new Set(['1,8']); const q=[[1,8]]; while(q.length){ const [x,y]=q.shift(); [[1,0],[-1,0],[0,1],[0,-1]].forEach(([dx,dy])=>{ const nx=x+dx,ny=y+dy,k=nx+','+ny; if(seen.has(k)||ny<0||ny>=M.length||nx<0||nx>=M[0].length||solid(nx,ny))return; seen.add(k); q.push([nx,ny]); }); } return seen.has('29,9')&&seen.has('29,1'); });
  ok(miss===true,'con la verja cerrada, el agujero de la valla lleva igual al bote y a la carretera');
  await calm(); await use(5,13,0); ok(await ev(()=>window.__LH.S.clues.includes('valla')),'la valla rota da pista'); await p.keyboard.press('1'); await frames(1);
  await calm(); await use(26,10,0); ok(await ev(()=>window.__LH.S.clues.includes('embarcadero')),'la nota del barquero da pista'); await p.keyboard.press('1'); await frames(1);
  // volver a la torre conserva el incendio
  await calm(); await use(0,8,Math.PI/2); await wait(2600); await settle(); ok(await ev(()=>window.__LH.S.zone==='torre'&&window.__LH.W.burned&&!window.__LH.W.power),'volver a la torre conserva el incendio y la oscuridad');
  await calm(); await use(27,11,-Math.PI/2); await wait(2600); await settle();
  // final Nínive (lista + incendio)
  await calm(); await use(29,1,0); ok(await ev(()=>document.getElementById('dlgTitle').textContent.includes('CARRETERA')&&document.getElementById('dlgOpts').textContent.includes('NÍNIVE')),'la carretera ofrece ir a Nínive con la lista');
  await p.keyboard.press('1'); await frames(2); ok(await ev(()=>window.__LH.S.over===true&&window.__LH.S.ending==='ninive'&&!!window.__LH.cut),'carretera: cinemática final');
  await ev(()=>window.__LH.cutSkip()); await frames(2); let t=await endText(); ok(t.includes('NÍNIVE')&&t.includes('ardiendo')&&t.includes('REPETIR LA MISIÓN 3')&&!t.includes('MISIÓN 4'),'final «Nínive» con la torre ardiendo; sin misión 4');
  await p.screenshot({path:path.resolve(__dirname,'shots','m3-final-ninive.png')});
  // repetir: el bote (huir)
  await p.click('#btnRestart2'); await wait(300); await settle(); await calm(); ok(await ev(()=>window.__LH.S.mission===3&&window.__LH.S.zone==='torre'&&!window.__LH.W.burned),'repetir la misión 3 empieza de nuevo en la torre');
  await ev(()=>window.__LH.travel('perimetro',[1,8],-Math.PI/2)); await wait(2600); await settle(); await wait(1500); await settle();
  await calm(); await use(29,9,0); ok(await ev(()=>document.getElementById('dlgTitle').textContent.includes('EMBARCADERO')),'el embarcadero pide confirmación'); await p.keyboard.press('2'); await frames(1); ok(await ev(()=>!window.__LH.S.over),'«todavía no» no acaba');
  await use(29,9,0); await p.keyboard.press('1'); await frames(2); await ev(()=>window.__LH.cutSkip()); await frames(2); t=await endText(); ok(t.includes('EL MAR'),'final «El mar» (huir sin quemar)');
  // la radio: Séneca
  await p.click('#btnRestart2'); await wait(300); await settle(); await calm(); await use(16,4,0); await p.keyboard.press('1'); await frames(2);
  ok(await ev(()=>window.__LH.S.over&&window.__LH.S.ending==='seneca'),'entregarse por la radio acaba la misión'); await ev(()=>window.__LH.cutSkip()); await frames(2); t=await endText(); ok(t.includes('SÉNECA'),'final «Séneca»');
  // la carretera sin la lista
  await p.click('#btnRestart2'); await wait(300); await settle(); await ev(()=>window.__LH.travel('perimetro',[1,8],-Math.PI/2)); await wait(2600); await settle(); await wait(1500); await settle();
  await calm(); await use(29,1,0); ok(await ev(()=>!document.getElementById('dlgOpts').textContent.includes('NÍNIVE')),'sin la lista, la carretera no es Nínive'); await p.keyboard.press('1'); await frames(2); await ev(()=>window.__LH.cutSkip()); await frames(2); t=await endText(); ok(t.includes('CARRETERA DE ROTA')&&!t.includes('>NÍNIVE<'),'final «La carretera de Rota»');
  // derrota: cuarta sesión, sin celda
  await p.click('#btnRestart2'); await wait(300); await settle(); await ev(()=>window.__LH.defeat('guards')); await frames(2);
  ok(await ev(()=>window.__LH.S.over&&document.getElementById('end').textContent.includes('CUARTA SESIÓN')),'la derrota en la misión 3 lleva a la cuarta sesión');
  // interrogatorio: etiquetas de la misión 3 y Ocaña confiesa dónde está la lista
  await p.click('#btnRestart2'); await wait(300); await settle(); await calm();
  await ev(()=>{ const L=window.__LH; const g=L.S.guards.find(g=>g.name.includes('Ocaña')); g.x=L.wx(9); g.z=L.wx(4); g.fx=0; g.fz=-1; L.S.p.x=g.x; L.S.p.z=g.z+1.2; L.yaw=0; L.S.p.crouch=true; L.locked=true; }); await frames(3);
  ok(await ev(()=>document.getElementById('prompt').textContent.includes('INTERROGAR')),'se puede agarrar a Ocaña por la espalda');
  await ev(()=>window.__LH.doGrab()); await frames(1); ok(await ev(()=>document.getElementById('dlgOpts').textContent.includes('lista completa')&&document.getElementById('dlgOpts').textContent.includes('sale de Tarsis')),'preguntas propias de la misión 3');
  for(const k of ['4','4','1'])await p.keyboard.press(k).then(()=>frames(1)); ok(await ev(()=>window.__LH.S.clues.includes('ocana')),'Ocaña suelta dónde está la lista'); await p.keyboard.press('5'); await frames(2);
  // encadenado desde el final de la misión 2: hereda compuerta y lista
  await ev(()=>{ const L=window.__LH; L.reset(); L.showMenu('main'); }); await wait(300); await p.click('#btnM2'); await wait(600); await settle(); await calm();
  await ev(()=>{ const L=window.__LH; L.W.gateOpen=true; L.S.clues.push('lista'); L.S.over=true; L.outro2(); }); await frames(2); await ev(()=>window.__LH.cutSkip()); await frames(2);
  ok(await ev(()=>!!document.getElementById('btnNext')&&document.getElementById('btnNext').textContent.includes('MISIÓN 3')),'el final de la misión 2 ofrece la misión 3');
  await p.click('#btnNext'); await wait(600); ok(await ev(()=>{ const L=window.__LH; return L.S.mission===3&&L.S.zone==='torre'&&L.S.prev&&L.S.prev.gate===true&&L.S.prev.lista===true; }),'la misión 3 hereda compuerta y lista de la 2');
  await ev(()=>window.__LH.cutSkip()); await wait(300); await settle(); await calm(); await ev(()=>window.__LH.saveGame('Prueba herencia'));
  ok(await ev(()=>{ const L=window.__LH; const d=L.loadGame(); return !!d&&L.S.prev&&L.S.prev.gate===true; }),'el estado heredado se guarda y se carga');
  await ev(()=>window.__LH.startGame(false,true)); await settle(); await ev(()=>window.__LH.travel('perimetro',[1,8],-Math.PI/2)); await wait(2600); await settle(); await wait(1500); await settle(); await calm();
  await use(29,9,0); await p.keyboard.press('1'); await frames(2); await ev(()=>window.__LH.cutSkip()); await frames(2); t=await endText(); ok(t.includes('la compuerta cayó')&&t.includes('siete nombres del laboratorio'),'el final menciona lo heredado de la misión 2');
  await p.screenshot({path:path.resolve(__dirname,'shots','m3-final-mar.png')});
  await ok(errs.length===0,'sin errores de consola '+(errs.length?JSON.stringify(errs.slice(0,5)):''));
  console.log(fails?'FALLOS: '+fails:'TODO OK'); await b.close(); })();
