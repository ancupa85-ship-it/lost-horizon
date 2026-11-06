// Partida completa automática del nivel: node tests/nivel-run.js noletal|letal
const {chromium}=require('playwright'); const path=require('path'); const fs=require('fs');
const route=process.argv[2]||'noletal'; const shotDir=path.resolve(__dirname,'shots-nivel'); fs.mkdirSync(shotDir,{recursive:true});
(async()=>{ const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message)); p.on('console',m=>{ if(m.type()==='error')errs.push(m.text()); });
  await p.goto('file://'+path.resolve(__dirname,'..','nivel','index.html')+'?test'); await p.waitForTimeout(800);
  await p.click('#btnGo'); await p.addScriptTag({path:path.resolve(__dirname,'nivel-bot.js')});
  let fails=0; const ok=(c,m,extra)=>{ console.log((c?'ok   ':'FALLO ')+m+(extra?'  '+extra:'')); if(!c){ fails++; process.exitCode=1; } };
  const run=async(label,fn)=>{ try{ const r=await p.evaluate(fn); console.log('  ·',label,typeof r==='string'?r:JSON.stringify(r)); return r; }catch(e){ ok(false,label,e.message.split('\n')[0].slice(0,900)); throw e; } };
  const shot=async(n)=>{ await p.evaluate(()=>{ __T.updateCamera(1/30); __T.render(); }); await p.screenshot({path:path.join(shotDir,route+'-'+n+'.png')}); };
  const st=()=>p.evaluate(()=>BOT.st());
  try{
    await run('intro',()=>{ BOT.wait(1); return BOT.st(); });
    if(route==='noletal'){
      await run('a los juncos del este',()=>{ BOT.go(0,30); BOT.crouch(true); BOT.go(10,28.5,{crouch:true}); BOT.go(22,26,{crouch:true}); BOT.go(30,24.5,{crouch:true}); return BOT.st(); });
      await shot('1-valla');
      await run('por el agujero de la valla',()=>{ BOT.go(30,21,{crouch:true}); BOT.go(32.6,19,{crouch:true}); BOT.go(33,15,{crouch:true}); return BOT.st(); });
      await run('dormir al patrullero E con un dardo desde los juncos',()=>{ const g=BOT.guard('patio E'); BOT.wait(60,()=>g.state==='patrol'&&Math.hypot(g.x-__T.P.x,g.z-__T.P.z)<11&&g.x>24); const r=BOT.shootGuard('patio E',true); return r+' '+JSON.stringify(BOT.st()); });
      await run('cruzar hacia la escalera',()=>{ BOT.go(30,5,{crouch:true}); BOT.go(16,5,{crouch:true}); return BOT.st(); });
      await run('esperar a que el del balcón dé la espalda y subir agachado',()=>{ const g=BOT.guard('balcón'); BOT.wait(60,()=>g.ri===0&&g.x<-2); BOT.go(13.75,3,{crouch:true}); BOT.go(13.75,-7.6,{crouch:true}); BOT.go(13.6,-9,{crouch:true}); return BOT.st(); });
      await shot('2-balcon');
      await run('dormir al guardia del balcón (dardo)',()=>{ const g=BOT.guard('balcón'); BOT.wait(40,()=>g.state!=='patrol'||g.x>1&&g.ri===1); return BOT.shootGuard('balcón',true); });
      await run('entrar al archivo y leer la nota',()=>{ BOT.go(12.5,-9,{crouch:true}); BOT.go(0,-9,{crouch:true}); BOT.go(0,-13,{crouch:true}); BOT.go(3,-14,{crouch:true}); BOT.use(); BOT.wait(0.5); return {note:__T.S.noteRead,obj:__T.S.objective}; });
      await shot('3-archivo');
      await run('probar una clave mal',()=>{ BOT.go(0,-20.3,{crouch:true}); BOT.use(); ['1','9','8','3','OK'].forEach(k=>__T.keypadPress(k)); const m=__T.S.mode; document.getElementById('kpClose').click(); return {mode:m,tries:__T.S.codeTries,has:__T.S.hasFile}; });
      await run('escotilla arriba a la azotea',()=>{ BOT.crouch(false); BOT.go(-3,-13); BOT.go(-9,-13); BOT.go(-9,-18.3); BOT.go(-9,-19.0,{tol:0.5}); return BOT.climb(1); });
      await shot('4-azotea');
      await run('bajar al anexo por la escalera oeste',()=>{ BOT.go(-11.0,-17); BOT.climb(-1); return BOT.st(); });
      await run('saltar del anexo al suelo y llegar a la torre',()=>{ BOT.crouch(true); BOT.go(-19.4,-12.5,{crouch:true}); BOT.crouch(false); BOT.go(-19.4,-11.0); BOT.wait(1); BOT.crouch(true); const g=BOT.guard('patio O'); BOT.wait(30,()=>g.x>0); BOT.go(-24,-4,{crouch:true}); BOT.go(-20,4.8,{crouch:true}); return BOT.st(); });
      await run('trepar a la torre de vigilancia',()=>{ BOT.crouch(false); BOT.go(-20,5.4,{tol:0.4}); return BOT.climb(1); });
      await shot('5-torre');
      await run('estrangular al vigía por la espalda',()=>{ BOT.crouch(true); BOT.go(-19.6,7.9,{crouch:true,tol:0.25}); return BOT.takedown('vigía'); });
      ok(await p.evaluate(()=>!__T.S.spotOn),'con el vigía dormido el reflector se apaga');
      await run('leer la Biblia',()=>{ BOT.go(-21.0,7.2,{crouch:true}); BOT.use(); BOT.wait(0.5); return {bible:__T.S.bibleRead,darts:__T.P.ammoN}; });
      await run('bajar de la torre y volver al anexo por las cajas',()=>{ BOT.crouch(false); BOT.go(-20,6.9); BOT.climb(-1); BOT.crouch(true); BOT.go(-21,-4,{crouch:true}); BOT.go(-17.4,-9.6,{crouch:true}); BOT.crouch(false); BOT.jumpTo(-17.4,-11.3); BOT.jumpTo(-16.2,-11.3); BOT.jumpTo(-16.2,-12.8); return BOT.st(); });
      ok(await p.evaluate(()=>__T.P.y>2.3),'subido al tejado del anexo (2,4 m) saltando por las cajas');
      await run('anexo → azotea → escotilla → caja fuerte',()=>{ BOT.go(-12.45,-17,{tol:0.4}); BOT.climb(1); BOT.go(-9,-17.5,{tol:0.3}); BOT.climb(-1); BOT.go(-9,-13); BOT.go(-3,-13); BOT.go(0,-20.3); BOT.use(); ['0','1','0','3','OK'].forEach(k=>__T.keypadPress(k)); BOT.wait(1); return {has:__T.S.hasFile,obj:__T.S.objective,reserve:BOT.guard('azotea').active}; });
      ok(await p.evaluate(()=>__T.S.hasFile&&__T.S.objective===3),'caja fuerte abierta con 0103 (Jonás 1,3): expediente');
      ok(await p.evaluate(()=>!__T.G[5].active),'sin muertos no aparece el tirador de la azotea');
      await run('subir por la escotilla y tirolina',()=>{ BOT.go(-3,-13); BOT.go(-9,-13); BOT.go(-9,-18.3); BOT.go(-9,-19,{tol:0.5}); BOT.climb(1); BOT.go(0,-20.6); BOT.use(); let t=0; while(__T.S.mode==='cut'&&t<200){ BOT.tick(1); t++; } return BOT.st(); });
      await p.evaluate(()=>{}); 
    } else {
      await run('aproximación al portón',()=>{ BOT.go(0,30); return BOT.st(); });
      await run('matar al centinela',()=>BOT.shootGuard('centinela',false,true));
      await run('tiroteo en el portón: abatir a los que vienen',()=>{ BOT.crouch(true); const r=BOT.fight(['patio O','patio E'],60); return r+' '+JSON.stringify(BOT.st()); });
      await shot('1-porton');
      await run('abatir al vigía de la torre desde el portón (se apaga el reflector)',()=>{ BOT.go(0,24); BOT.go(0,18); BOT.crouch(true); return BOT.fight(['vigía','patio E'],40); });
      ok(await p.evaluate(()=>!__T.S.spotOn),'vigía abatido: reflector apagado');
      await run('al oeste, a la torre',()=>{ BOT.go(-14,12); BOT.go(-20,4.8); BOT.go(-20,5.4,{tol:0.4}); return BOT.climb(1); });
      await run('Biblia',()=>{ BOT.go(-21.0,7.2); BOT.use(); BOT.wait(0.3); return __T.S.bibleRead; });
      await run('bajar de la torre',()=>{ BOT.go(-20,6.9); return BOT.climb(-1); });
      await run('a la escalera exterior',()=>{ BOT.go(-14,4); BOT.go(10,6); BOT.go(13.75,3); BOT.go(13.75,-7.6); return BOT.st(); });
      await run('abatir al del balcón',()=>BOT.fight(['balcón'],30));
      await run('nota y caja fuerte',()=>{ BOT.go(12.5,-9); BOT.go(0,-9); BOT.go(0,-13); BOT.go(3,-14); BOT.use(); BOT.wait(0.3); BOT.go(0,-20.3); BOT.use(); ['0','1','0','3','OK'].forEach(k=>__T.keypadPress(k)); BOT.wait(1); return {has:__T.S.hasFile,reserve:BOT.guard('azotea').active,base:__T.S.base}; });
      ok(await p.evaluate(()=>__T.S.hasFile&&__T.G[5].active),'expediente; con muertos aparece el tirador de la azotea');
      await shot('2-archivo');
      await run('salir por el balcón, la escalera y el portón hasta el bote',()=>{ BOT.go(0,-13); BOT.go(0,-9); BOT.fight(['azotea'],20); BOT.go(13.6,-9); BOT.go(13.75,-7.4); BOT.go(13.75,3); BOT.go(4,16); BOT.go(0,19); BOT.go(0,30); BOT.go(1.2,39); BOT.use(); return BOT.st(); });
    }
    const end=await p.evaluate(()=>({mode:__T.S.mode,exit:__T.S.exit,kills:__T.S.kills,sleeps:__T.S.sleeps,alarms:__T.S.alarms,time:Math.round(__T.S.time),txt:document.getElementById('end').innerText}));
    ok(end.mode==='end','nivel terminado de principio a fin ('+route+')',JSON.stringify({exit:end.exit,kills:end.kills,sleeps:end.sleeps,alarms:end.alarms,t:end.time}));
    console.log(end.txt.replace(/\n+/g,' | '));
    await p.screenshot({path:path.join(shotDir,route+'-9-fin.png')});
  }catch(e){ console.log('estado:',JSON.stringify(await st().catch(()=>null))); await shot('error'); }
  ok(errs.length===0,'sin errores de JavaScript',errs.slice(0,3).join(' | '));
  await b.close(); })();
