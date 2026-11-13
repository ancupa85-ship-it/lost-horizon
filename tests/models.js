// Prueba de la entrada de modelos de Blender: sin modelos el mundo se dibuja con cajas; al cargar un .glb en un hueco,
// todas las piezas de ese hueco pasan a usar el modelo (también al cambiar de zona), y un archivo roto no rompe nada.
// Usa las plantillas de assets/plantillas/ como modelos de prueba. Uso: node tests/models.js
const {chromium}=require('playwright'); const path=require('path'); const fs=require('fs');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1280,height:720}});
  const errs=[]; p.on('pageerror',e=>errs.push(e.message)); p.on('console',m=>{ if(m.type()==='error')errs.push(m.text()); });
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')); await p.waitForTimeout(1500);
  const ev=(f,a)=>p.evaluate(f,a); let fails=0; const ok=(c,msg)=>{ if(!c){ fails++; console.error('FALLO:',msg); process.exitCode=1; } else console.log('ok  ',msg); };
  const glb=n=>fs.readFileSync(path.resolve(__dirname,'..','assets','plantillas',n+'.glb')).toString('base64');
  const count=()=>ev(()=>{ const o={}; window.__LH.slotInst.forEach(i=>{ const k=i.name; o[k]=o[k]||{n:0,m:0}; o[k].n++; if(i.model)o[k].m++; }); return o; });
  ok(await ev(()=>typeof window.__LH.THREE.GLTFLoader==='function'),'el cargador glTF está disponible');
  ok(await ev(()=>Object.keys(window.LH_MODELS||{}).every(k=>!!window.__LH.MODELS[k])),'los modelos empaquetados (si los hay) están cargados');
  let c=await count(); const packed=await ev(()=>Object.keys(window.LH_MODELS||{}));
  ok(c.caja&&c.caja.n>20&&c.camion&&c.camion.n===3&&c.generador&&c.generador.n===1&&c.farola&&c.farola.n>5,'la base tiene sus huecos: '+JSON.stringify(c));
  if(!packed.includes('caja'))ok(c.caja.m===0,'sin modelo, las cajas se dibujan con la pieza de código');
  const meshes0=await ev(()=>{ let n=0; window.__LH.zoneGroup.traverse(o=>{ if(o.isMesh)n++; }); return n; });
  // cargar la plantilla de la caja como si fuera un modelo de Blender
  ok(await ev(b64=>window.__LH.loadModel('caja',b64),glb('caja')),'un .glb válido entra en el hueco «caja»');
  c=await count(); ok(c.caja.m===c.caja.n,'todas las cajas de la zona pasan a ser el modelo ('+c.caja.m+'/'+c.caja.n+')');
  const info=await ev(()=>window.__LH.MODEL_INFO.caja); ok(info&&info.tris>=12&&Math.abs(info.size[0]-1.8)<0.05&&Math.abs(info.size[1]-1.3)<0.05&&Math.abs(info.minY)<0.02,'medidas del modelo: 1,8 × 1,3 × 1,8 m, apoyado en el suelo ('+JSON.stringify(info)+')');
  ok(await ev(()=>{ let good=true; window.__LH.slotInst.filter(i=>i.name==='caja').forEach(i=>{ const o=i.objs[0]; if(Math.abs(o.position.x-i.px)>1e-6||Math.abs(o.position.z-i.pz)>1e-6||o.parent!==window.__LH.zoneGroup)good=false; o.traverse(m=>{ if(m.isMesh&&!m.material.isMeshToonMaterial)good=false; }); }); return good; }),'cada modelo está en su casilla y con material de cel-shading');
  ok(await ev(()=>{ const L=window.__LH; return L.MAPSRC.every((r,y)=>r.split('').every((ch,x)=>ch!=='c'||!L.los({x:L.wx(x-1),z:L.wx(y)},{x:L.wx(x+1),z:L.wx(y)}))); }),'las cajas siguen tapando la vista (la colisión va por casillas)');
  // camión, generador, farola, torreta
  for(const n of ['camion','generador','farola','torreta'])ok(await ev(([n,b64])=>window.__LH.loadModel(n,b64),[n,glb(n)]),'plantilla «'+n+'» cargada');
  c=await count(); ok(Object.keys(c).every(k=>c[k].m===c[k].n),'todos los huecos de la base usan modelo: '+JSON.stringify(c));
  const inf=await ev(()=>window.__LH.MODEL_INFO); ok(Math.abs(inf.camion.size[0]-4)<0.05&&Math.abs(inf.camion.size[2]-4)<0.05&&Math.abs(inf.torreta.size[1]-7)<0.05&&Math.abs(inf.farola.size[1]-3.3)<0.05,'huellas de camión (4 × 4), torreta (7 m) y farola (3,3 m)');
  // al cambiar de zona y volver, los modelos siguen
  await ev(()=>{ const L=window.__LH; L.enterZone('torre',null,0,{fresh:true}); }); c=await count(); ok(c.caja&&c.caja.m===c.caja.n&&c.caja.n>0,'otra zona: las cajas salen ya con el modelo ('+JSON.stringify(c)+')');
  await ev(()=>{ const L=window.__LH; L.enterZone('excavacion',null,0,{fresh:true}); L.enterZone('base',null,0,{fresh:true}); }); c=await count(); ok(c.caja.m===c.caja.n&&c.camion.m===3,'de vuelta en la base, igual');
  // un archivo roto no entra y no rompe el juego
  ok(await ev(()=>window.__LH.loadModel('caja','QUJDREVGRw==').then(r=>r===false)),'un archivo que no es glTF se rechaza sin romper nada');
  await ev(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r()))));
  if(process.argv[2])await p.screenshot({path:process.argv[2]});
  ok(errs.length===0,'sin errores de consola'+(errs.length?': '+errs.join(' | '):''));
  console.log(fails?('\n'+fails+' FALLOS'):'\nmodelos: todo en orden ('+meshes0+' mallas de código en la base antes de cargar)'); await b.close();
})();
