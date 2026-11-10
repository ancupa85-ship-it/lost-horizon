'use strict';
// ---------- MODELOS glTF (Blender): cada «hueco» del mundo se dibuja con cajas hasta que existe su modelo.
// Los .glb viven en assets/models/<hueco>.glb; `python3 tools/build-models.py` los empaqueta en assets/models/pack.js
// (window.LH_MODELS = {hueco: base64}), que se carga antes que el juego. Así funcionan igual abriendo index.html,
// en las pruebas y dentro del Artifact, sin pedir nada por red. Guía de medidas: docs/ASSETS.md.
// Convenio del modelo: 1 unidad = 1 metro, Y hacia arriba, origen en el suelo y en el centro de la huella, frente hacia +Z.
const MODEL_SLOTS={
  caja:{desc:'Caja de madera que tapa la vista (casilla c)',size:[1.8,1.3,1.8]},
  camion:{desc:'Camión aparcado o bloque de vehículo (bloque de casillas T, 2×2)',size:[4,2.2,4]},
  generador:{desc:'Grupo electrógeno con tubo de escape (casilla g)',size:[1.8,2.9,1.4]},
  farola:{desc:'Poste de farola; la bombilla la pone el juego a 3,25 m (casilla l en exteriores)',size:[0.3,3.3,0.3]},
  torreta:{desc:'Torre del foco giratorio; el foco lo pone el juego a 7 m',size:[1.2,7,1.2]},
};
const MODELS={}, MODEL_INFO={}, slotInst=[];
// materiales del modelo → toon con la misma rampa que el resto del juego (color, textura, transparencia y emisión se conservan)
function toonify(root){ let tris=0; root.traverse(o=>{ if(!o.isMesh)return;
    const conv=m=>{ const t=new THREE.MeshToonMaterial({gradientMap:grad,color:m.color?m.color.clone():new THREE.Color(0xffffff),map:m.map||null,transparent:!!m.transparent,opacity:m.opacity!==undefined?m.opacity:1,alphaTest:m.alphaTest||0,side:m.side,vertexColors:!!m.vertexColors});
      if(m.emissive&&(m.emissive.r||m.emissive.g||m.emissive.b)){ t.emissive=m.emissive.clone(); t.emissiveMap=m.emissiveMap||null; } t.name=m.name; return t; };
    o.material=Array.isArray(o.material)?o.material.map(conv):conv(o.material); o.castShadow=true; o.receiveShadow=true; o.geometry.userData.shared=true;
    const g=o.geometry; tris+=g.index?g.index.count/3:(g.attributes.position?g.attributes.position.count/3:0); }); return Math.round(tris); }
function modelReady(name,sceneObj){ const tris=toonify(sceneObj); const bb=new THREE.Box3().setFromObject(sceneObj); const sz=bb.getSize(new THREE.Vector3());
  MODELS[name]=sceneObj; MODEL_INFO[name]={tris,size:[+sz.x.toFixed(2),+sz.y.toFixed(2),+sz.z.toFixed(2)],minY:+bb.min.y.toFixed(2)};
  // huecos ya dibujados con cajas en la zona cargada: se cambian por el modelo
  slotInst.forEach(inst=>{ if(inst.name!==name||inst.model||inst.group!==zoneGroup)return; inst.objs.forEach(o=>{ if(o.parent)o.parent.remove(o); if(o.geometry&&!o.geometry.userData.shared&&o.geometry!==box&&o.geometry!==tall)o.geometry.dispose(); }); inst.objs=[placeModel(inst)]; inst.model=true; }); }
function b64buf(s){ const bin=atob(s); const u=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i); return u.buffer; }
// carga un .glb en base64 en un hueco; devuelve una promesa (true si entró)
function loadModel(name,b64){ return new Promise(res=>{ if(!THREE.GLTFLoader){ res(false); return; }
  try{ new THREE.GLTFLoader().parse(b64buf(b64),'',g=>{ try{ modelReady(name,g.scene); res(true); }catch(e){ console.warn('modelo '+name+': '+e.message); res(false); } },e=>{ console.warn('modelo '+name+' no válido: '+(e&&e.message||e)); res(false); }); }
  catch(e){ console.warn('modelo '+name+' no válido: '+e.message); res(false); } }); }
function placeModel(inst){ const o=MODELS[inst.name].clone(); o.position.set(inst.px,0,inst.pz); o.rotation.y=inst.rot||0; inst.group.add(o); return o; }
// dibuja un hueco en (px,pz): con su modelo si existe; si no, con las cajas que devuelve build()
function slot(name,px,pz,rot,build){ const inst={name,px,pz,rot:rot||0,objs:null,model:false,group:zoneGroup};
  if(MODELS[name]){ inst.objs=[placeModel(inst)]; inst.model=true; } else inst.objs=build(); slotInst.push(inst); return inst; }
(function(){ const pack=window.LH_MODELS||{}; Object.keys(pack).forEach(name=>{ loadModel(name,pack[name]); }); })();
