// Capturas de referencia del nivel (calidad completa): node tests/nivel-shots.js
const {chromium}=require('playwright'); const path=require('path'); const fs=require('fs');
const out=path.resolve(__dirname,'shots-nivel'); fs.mkdirSync(out,{recursive:true});
(async()=>{ const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}});
  await p.goto('file://'+path.resolve(__dirname,'..','nivel','index.html')+'?test&gfx=full'); await p.waitForTimeout(800);
  await p.click('#btnGo'); await p.addScriptTag({path:path.resolve(__dirname,'nivel-bot.js')}); await p.evaluate(()=>BOT.wait(2));
  const cam=async(n,pos,look)=>{ await p.evaluate(([pos,look])=>{ const c=__T.camera; c.position.set(...pos); c.lookAt(...look); c.fov=60; c.updateProjectionMatrix(); __T.render(); },[pos,look]); await p.screenshot({path:path.join(out,n+'.png')}); };
  const play=async(n,fn)=>{ await p.evaluate(fn); await p.evaluate(()=>{ __T.updateCamera(1/30); __T.render(); }); await p.screenshot({path:path.join(out,n+'.png')}); };
  await cam('vista-general',[38,30,44],[-2,2,-6]);
  await cam('vista-norte',[-30,22,-48],[2,4,-8]);
  await play('juego-embarcadero',()=>{ const T=__T; T.S.yaw=0.15; T.S.pitch=-0.05; BOT.wait(0.2); });
  await play('juego-patio',()=>{ const T=__T; T.S.flags.inside=1; const P=T.P; P.x=24; P.y=0; P.z=12; T.S.yaw=0.9; T.S.pitch=-0.1; BOT.crouch(true); BOT.wait(0.2); });
  await play('juego-balcon',()=>{ const T=__T; const P=T.P; P.x=13.7; P.y=4; P.z=-8.9; T.S.yaw=-1.45; T.S.pitch=-0.12; BOT.crouch(false); BOT.wait(0.2); });
  await play('juego-azotea',()=>{ const T=__T; const P=T.P; P.x=4; P.y=8.3; P.z=-12; T.S.yaw=0.5; T.S.pitch=-0.25; BOT.wait(0.2); });
  await b.close(); })();
