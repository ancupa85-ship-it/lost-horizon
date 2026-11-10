// Exporta las piezas de cajas del juego como plantillas .glb (assets/plantillas/) para abrirlas en Blender:
// dan la escala, el origen y la orientación exactos de cada hueco, y una figura de 1,8 m como referencia de tamaño.
// Uso: node tools/export-templates.js   (requiere Playwright y Chromium)
const {chromium}=require('playwright'); const path=require('path'); const fs=require('fs');
(async()=>{ const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:640,height:360}}); p.on('pageerror',e=>console.error('error de página:',e.message));
  await p.goto('file://'+path.resolve(__dirname,'..','index.html')); await p.waitForTimeout(1200);
  await p.addScriptTag({path:path.resolve(__dirname,'vendor','GLTFExporter.js')});
  const out=path.resolve(__dirname,'..','assets','plantillas'); fs.mkdirSync(out,{recursive:true});
  const res=await p.evaluate(async()=>{ const L=window.__LH, THREE=L.THREE; const done={};
    const toB64=buf=>{ const u=new Uint8Array(buf); let s=''; for(let i=0;i<u.length;i+=0x8000)s+=String.fromCharCode.apply(null,u.subarray(i,i+0x8000)); return btoa(s); };
    const exp=obj=>new Promise((res,rej)=>{ try{ new THREE.GLTFExporter().parse(obj,r=>res(toB64(r)),{binary:true}); }catch(e){ rej(e); } });
    // materiales sencillos (color liso) para que Blender los abra sin texturas raras
    const plain=o=>{ o.traverse(m=>{ if(m.isMesh){ const c=m.material&&m.material.color?m.material.color.clone():new THREE.Color(0x888888); const map=m.material&&m.material.map; if(map&&map.image&&map.image.getContext){ const d=map.image.getContext('2d').getImageData(0,0,1,1).data; c.setRGB(d[0]/255,d[1]/255,d[2]/255); } m.material=new THREE.MeshStandardMaterial({color:c,roughness:1,metalness:0,name:(m.material&&m.material.name)||'liso'}); } }); return o; };
    for(const zone of ['base','torre','perimetro','excavacion']){ L.enterZone(zone,null,0,{fresh:true});
      for(const inst of L.slotInst){ if(done[inst.name]||inst.model)continue; const g=new THREE.Group(); g.name=inst.name;
        inst.objs.forEach(o=>{ const c=o.clone(); c.position.set(o.position.x-inst.px,o.position.y,o.position.z-inst.pz); g.add(c); });
        const root=new THREE.Group(); root.name='plantilla_'+inst.name; g.rotation.y=-(inst.rot||0); root.add(g); root.updateMatrixWorld(true); done[inst.name]=await exp(plain(root)); } }
    const fig=L.figure({uniform:0x4f5a3c,helmet:0x4a5a3a,rifle:true}).g.clone(); fig.name='referencia_persona_1m80'; fig.position.set(0,0,0); done['referencia-persona']=await exp(plain(fig));
    return done; });
  for(const k of Object.keys(res)){ const f=path.join(out,k+'.glb'); fs.writeFileSync(f,Buffer.from(res[k],'base64')); console.log('plantilla',k+'.glb',Math.round(fs.statSync(f).size/1024)+' KB'); }
  await b.close(); })();
