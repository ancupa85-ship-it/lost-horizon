// Prueba de reconocimiento: prismáticos y marcado, cargador vacío (distracción) y modo reflejo, en la base (misión 1).
// Uso: node tests/recon.js   (requiere Playwright y Chromium; NODE_PATH=/opt/node-tools/node_modules en el sandbox)
const {chromium}=require('playwright'); const path=require('path');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}});
  const errs=[]; p.on('pageerror',e=>errs.push(e.message)); p.on('console',m=>{ if(m.type()==='error')errs.push(m.text()); });
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')); await p.waitForTimeout(1500);
  const ev=(f,a)=>p.evaluate(f,a); const wait=ms=>p.waitForTimeout(ms);
  // la máquina de pruebas va a ~2 fotogramas por segundo: se avanza la simulación a paso fijo sin dibujar
  const frames=(n)=>ev((n)=>{ window.__LH.step(n); return new Promise(r=>requestAnimationFrame(()=>r())); },n);
  const until=async(f,max)=>{ for(let i=0;i<(max||300);i+=4){ if(await ev(f))return true; await ev(()=>window.__LH.step(4)); } return ev(f); };
  const dump=()=>ev(()=>{ const L=window.__LH,S=L.S; return JSON.stringify({ui:L.uiOpen,cut:!!L.cut,codec:!!L.codecQ,alertT:S.alertT,alarms:S.alarms,reflex:S.reflex?S.reflex.t:null,cd:S.reflexCd,marks:S.marks,decoys:S.decoys,guards:S.guards.map(g=>g.state+(g.marked?'*':'')+(g.down>0?'z':'')+(g.dead?'x':''))}); });
  let fails=0; const ok=async(c,msg)=>{ if(!c){ fails++; console.error('FALLO:',msg,await dump()); process.exitCode=1; } else console.log('ok  ',msg); };
  const closeCodec=async()=>{ for(let i=0;i<24;i++){ if(!(await ev(()=>!!window.__LH.codecQ)))break; await ev(()=>window.__LH.codecNext()); await wait(60);} };
  const settle=async()=>{ for(let i=0;i<40;i++){ if(await ev(()=>!!window.__LH.cut))await ev(()=>window.__LH.cutSkip()); await closeCodec(); if(await ev(()=>!window.__LH.uiOpen&&!window.__LH.cut&&!window.__LH.codecQ&&!window.__LH.S.traveling))break; await wait(150);} };
  // deja la base quieta: guardias clavados lejos en una esquina, mirando a la pared, y el jugador en el patio norte
  const stage=async()=>{ await settle(); await ev(()=>{ const L=window.__LH,S=L.S; S.alertT=0; S.alarms=0; S.base='calma'; S.freeze=0; S.reflex=null; S.reflexCd=0; L.locked=true; L.third=false; S.codecSeen.alarm=true; S.dogsDone=true;
    S.guards.forEach((g,i)=>{ g.state='patrol'; g.susp=0; g.shotT=999; g.fixing=false; g.dead=false; g.down=0; g.held=false; g.marked=false; g.decoy=0; g.heardF=null; g.x=L.wx(30+(i%4)); g.z=L.wx(24+((i/4)|0)); g.wps=[[30+(i%4),24+((i/4)|0)]]; g.wi=0; g.fx=1; g.fz=0; });
    S.bodies.length=0; S.p.x=L.wx(12); S.p.z=L.wx(1); S.p.crouch=false; S.p.hp=5; S.c.x=L.wx(2); S.c.z=L.wx(2); S.c.crouch=true; L.pitch=0; L.scopeKey=false; }); await frames(2); };
  // coloca a un guardia en una casilla, mirando hacia (fx,fz)
  const put=(i,x,y,fx,fz)=>ev(([i,x,y,fx,fz])=>{ const L=window.__LH, g=L.S.guards[i]; g.x=L.wx(x); g.z=L.wx(y); g.wps=[[x,y]]; g.wi=0; g.fx=fx; g.fz=fz; g.state='patrol'; g.susp=0; },[i,x,y,fx,fz]);
  const aimAt=(i)=>ev((i)=>{ const L=window.__LH,S=L.S,g=S.guards[i],P=S.p; const d=Math.hypot(g.x-P.x,g.z-P.z); L.yaw=Math.atan2(-(g.x-P.x),-(g.z-P.z)); L.pitch=Math.atan2(1.3-1.6,d); },i);

  await p.click('[data-go="brief"]'); await wait(300); await p.click('#btnStart'); await wait(600); await settle(); await stage();

  // ---- prismáticos y marcado
  await put(0,12,9,0,1); await aimAt(0);   // 16 m al sur, de espaldas
  ok(await ev(()=>!window.__LH.scopeOn()&&Math.abs(window.__LH.camera.fov-70)<0.5),'sin prismáticos: campo de visión normal');
  await p.keyboard.down('b'); ok(await until(()=>window.__LH.scopeK>0.95,60),'B mantenida: los prismáticos hacen zoom');
  ok(await ev(()=>window.__LH.camera.fov<22),'el campo de visión se cierra (×4)');
  ok(await until(()=>window.__LH.S.guards[0].marked,120),'la mira sobre un guardia lo marca');
  ok(await ev(()=>window.__LH.S.marks===1&&window.__LH.S.clues.length===0),'cuenta una marca y no da pistas gratis');
  const a0=await ev(()=>window.__LH.S.p.ammo); await ev(()=>window.__LH.shoot()); ok(await ev((a)=>window.__LH.S.p.ammo===a,a0),'con los prismáticos no se dispara');
  await p.keyboard.up('b'); ok(await until(()=>window.__LH.scopeK<0.05&&Math.abs(window.__LH.camera.fov-70)<0.5,60),'al soltar B vuelve la vista normal');
  await put(1,22,11,0,1);
  await aimAt(1); await p.keyboard.down('b'); await until(()=>window.__LH.scopeK>0.95,60); await frames(40);
  ok(await ev(()=>!window.__LH.S.guards[1].marked),'no se marca a través de una pared (sin línea de visión)'); await p.keyboard.up('b'); await frames(10);
  // la marca viaja con el guardado de la zona
  ok(await ev(()=>{ const L=window.__LH; L.saveGame('prueba'); const d=JSON.parse(localStorage.getItem('lh-save')); return d.zones.base.guards[0].marked===true&&d.marks===1; }),'la marca se guarda con la partida');

  // ---- distracción
  await stage(); await put(0,12,9,1,0);     // 16 m al sur del jugador, mirando al este
  await ev(()=>{ const L=window.__LH; L.yaw=Math.PI; L.pitch=0; });   // mirar al sur
  const land=await ev(()=>window.__LH.decoyLanding()); ok(Math.abs(land.x-25)<0.6&&land.z>11&&land.z<15,'el cargador caería unos diez metros delante ('+land.z.toFixed(1)+')');
  ok(await ev(()=>window.__LH.throwDecoy()),'Z lanza el cargador');
  ok(await ev(()=>!window.__LH.throwDecoy()),'no se puede lanzar otro al instante');
  await ev(()=>{ const L=window.__LH; L.S.p.x=L.wx(3); L.S.p.z=L.wx(12); });   // el jugador se quita de en medio (dentro del edificio)
  ok(await until(()=>window.__LH.S.guards[0].state==='suspect',120),'el guardia que lo oye deja la ronda y va a mirar');
  ok(await ev(()=>{ const S=window.__LH.S; return S.alertT<=0&&S.alarms===0&&S.base==='calma'; }),'la distracción no da la alarma ni cambia el estado de la base');
  ok(await ev(()=>{ const S=window.__LH.S; return S.guards.slice(1).every(g=>g.state==='patrol'); }),'los que están lejos no lo oyen');
  const d0=await ev(()=>{ const g=window.__LH.S.guards[0]; return Math.hypot(g.x-g.heardN.x,g.z-g.heardN.z); });
  await frames(25); ok(await ev((d0)=>{ const g=window.__LH.S.guards[0]; return g.state==='patrol'||Math.hypot(g.x-g.heardN.x,g.z-g.heardN.z)<d0-0.3; },d0),'camina hacia el ruido');
  ok(await until(()=>window.__LH.S.guards[0].state==='patrol',900),'al no encontrar nada vuelve a la ronda');
  // a la tercera ya no pica: va hacia quien lo tiró
  await stage(); await put(0,12,7,1,0); await ev(()=>{ const L=window.__LH; L.S.guards[0].decoy=2; L.makeNoise(L.wx(12),L.wx(5),10,{x:L.wx(3),z:L.wx(6)}); });
  ok(await ev(()=>{ const L=window.__LH, g=L.S.guards[0]; return g.state==='suspect'&&Math.abs(g.target.x-L.wx(3))<0.1&&Math.abs(g.target.z-L.wx(6))<0.1; }),'a la tercera, el guardia va hacia el origen del lanzamiento');
  // rodea obstáculos: ruido al otro lado del muro del despacho
  await stage(); await put(0,13,11,0,-1); await ev(()=>{ const L=window.__LH; L.makeNoise(L.wx(9),L.wx(13),10,null); });
  ok(await ev(()=>window.__LH.S.guards[0].state==='suspect'&&!!window.__LH.S.guards[0].heardF),'ruido tras una pared: el guardia toma un camino');
  ok(await until(()=>{ const L=window.__LH, g=L.S.guards[0]; return Math.hypot(g.x-L.wx(9),g.z-L.wx(13))<3.2||g.state==='patrol'; },900),'y llega al ruido rodeando por la puerta');
  await ev(()=>{ const L=window.__LH; L.S.p.carry={x:0,z:0}; }); await frames(100);
  ok(await ev(()=>!window.__LH.throwDecoy()),'con un cuerpo a cuestas no se lanza'); await ev(()=>{ window.__LH.S.p.carry=null; });

  // ---- modo reflejo
  await stage(); await put(0,12,4,0,-1);     // 6 m al sur, mirando al jugador
  ok(await until(()=>!!window.__LH.S.reflex,200),'un guardia te ve de cerca: entra el modo reflejo en vez de la alarma');
  ok(await ev(()=>{ const S=window.__LH.S; return S.alertT<=0&&S.alarms===0; }),'durante el reflejo aún no hay alarma');
  // tumbarlo a tiempo
  await ev(()=>{ const L=window.__LH; L.knock(L.S.guards[0],false); }); await frames(3);
  ok(await ev(()=>{ const S=window.__LH.S; return !S.reflex&&S.alarms===0&&S.alertT<=0&&S.reflexSaved===1&&S.reflexCd>0; }),'derribado a tiempo: no hay alarma y el reflejo queda en espera');
  // segunda vez seguida: sin reflejo, alarma directa
  await ev(()=>{ const L=window.__LH,S=L.S; S.bodies.length=0; const g=S.guards[1]; g.x=L.wx(12); g.z=L.wx(4); g.wps=[[12,4]]; g.fx=0; g.fz=-1; S.guards[0].x=L.wx(31); S.guards[0].z=L.wx(25); });
  ok(await until(()=>window.__LH.S.alarms>0,300),'con el reflejo gastado, el siguiente da la alarma');
  ok(await ev(()=>!window.__LH.S.reflex),'y no hay segundo reflejo');
  // dejarlo pasar: alarma al acabar
  await stage(); await put(0,12,4,0,-1); ok(await until(()=>!!window.__LH.S.reflex,200),'reflejo otra vez tras la espera');
  ok(await until(()=>window.__LH.S.alarms>0,600),'si no haces nada, al acabar el reflejo salta la alarma');
  ok(await ev(()=>!window.__LH.S.reflex&&window.__LH.S.reflexCd>0),'la alarma cierra el reflejo');
  // un disparo sin silenciador rompe el reflejo
  await stage(); await put(0,12,4,0,-1); await until(()=>!!window.__LH.S.reflex,200); await ev(()=>{ const L=window.__LH; L.S.silencer=false; L.yaw=0; L.pitch=1.2; L.shoot(); });
  ok(await ev(()=>!window.__LH.S.reflex&&window.__LH.S.alarms>0),'disparar sin silenciador durante el reflejo da la alarma');

  ok(errs.length===0,'sin errores de consola'+(errs.length?': '+errs.join(' | '):''));
  console.log(fails?('\n'+fails+' FALLOS'):'\nreconocimiento: todo en orden'); await b.close();
})();
