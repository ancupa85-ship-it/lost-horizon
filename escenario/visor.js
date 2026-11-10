'use strict';
// Visor en tiempo real del escenario realista de la base de Tarsis. La geometría sale de Blender (tools/blender/escena_base.py con LH_GLB),
// las texturas son de Poly Haven (CC0) y este archivo pone los materiales, las luces, la niebla, la lluvia y el resplandor.
(function(){
const D=window.LH_ESC, INFO=D.info, T=INFO.T, MAP=INFO.map, ROWS=MAP.length, COLS=MAP[0].length;
const Q=new URLSearchParams(location.search); const LOW=Q.get('q')==='low';
const el=id=>document.getElementById(id);
const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,LOW?1:1.5)); renderer.setSize(innerWidth,innerHeight);
renderer.outputEncoding=THREE.sRGBEncoding; if(!LOW){ renderer.shadowMap.enabled=true; renderer.shadowMap.type=THREE.PCFSoftShadowMap; } renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.0; renderer.physicallyCorrectLights=true;
document.body.appendChild(renderer.domElement);
const scene=new THREE.Scene(); const FOGC=new THREE.Color(0x120d0b); scene.background=FOGC; scene.fog=new THREE.FogExp2(FOGC.getHex(),0.024);
const camera=new THREE.PerspectiveCamera(68,innerWidth/innerHeight,0.08,400);
// Blender (x, y, z arriba) → three (x, z arriba → y, -y → z)
const B=(p)=>new THREE.Vector3(p[0],p[2],-p[1]);

// ---------- texturas
const TL=new THREE.TextureLoader();
function tex(name,rep,srgb){ const t=TL.load(D.tex[name]); t.wrapS=t.wrapT=THREE.RepeatWrapping; t.repeat.set(1/rep,1/rep); t.anisotropy=LOW?2:8; if(srgb)t.encoding=THREE.sRGBEncoding; return t; }
const std=o=>new THREE.MeshStandardMaterial(o);
const M={
  suelo:std({map:tex('asphalt_diff',3,true),normalMap:tex('asphalt_nor',3),roughnessMap:tex('asphalt_rough',3),color:0x777777,roughness:0.75,normalScale:new THREE.Vector2(1.2,1.2)}),
  muro:std({map:tex('concrete_diff',3.2,true),normalMap:tex('concrete_nor',3.2),color:0x8a8a88,roughness:0.82}),
  pared:std({map:tex('plaster_diff',2.6,true),normalMap:tex('plaster_nor',2.6),color:0xa39c8e,roughness:0.85}),
  madera:std({map:tex('wood_diff',1.6,true),color:0xb09a80,roughness:0.75}),
  veta:std({color:0x2a1a0e,roughness:0.7}),
  hierro:std({map:tex('rust_diff',1.4,true),color:0x999999,roughness:0.6,metalness:0.55}),
  oliva:std({map:tex('green_diff',2.2,true),color:0x6f8a4c,roughness:0.5,metalness:0.1}),
  tejado:std({map:tex('roof_diff',2,true),normalMap:tex('roof_nor',2),color:0x666668,roughness:0.6,metalness:0.4}),
  bajos:std({color:0x15190f,roughness:0.6,metalness:0.3}), metal:std({color:0x7d858a,roughness:0.42,metalness:0.85}), oscuro:std({color:0x15171a,roughness:0.45,metalness:0.7}),
  lona:std({color:0x4b4a2e,roughness:0.9}), goma:std({color:0x0c0c0d,roughness:0.75}), cristal:std({color:0x06090b,roughness:0.05,metalness:0.2}),
  faro:std({color:0x8a8070,roughness:0.15,emissive:0xff9a40,emissiveIntensity:0.1}), piloto:std({color:0x551010,roughness:0.3,emissive:0xff1408,emissiveIntensity:0.5}),
  aviso:std({color:0xa8801a,roughness:0.6}), marisma:std({color:0x05090a,roughness:0.12,metalness:0.2}),
  ventana_on:std({color:0x2a2010,roughness:0.3,emissive:0xffa050,emissiveIntensity:3.2}), ventana_off:std({color:0x05080a,roughness:0.06,metalness:0.3}),
  bombilla:std({color:0x000000,emissive:0xff9a38,emissiveIntensity:9}), baliza:std({color:0x000000,emissive:0xff1408,emissiveIntensity:8}), foco:std({color:0x000000,emissive:0xcfe2ff,emissiveIntensity:12}),
};
M.hormigon=M.muro;
// charcos: en el suelo, un ruido en coordenadas del mundo baja la rugosidad, aplana el relieve y oscurece el asfalto
M.suelo.onBeforeCompile=sh=>{
  sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vWPos;').replace('#include <project_vertex>','#include <project_vertex>\nvWPos=(modelMatrix*vec4(transformed,1.0)).xyz;');
  sh.fragmentShader=sh.fragmentShader.replace('#include <common>',`#include <common>
varying vec3 vWPos;
float lhH(vec2 p){ return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
float lhN(vec2 p){ vec2 i=floor(p),f=fract(p); f=f*f*(3.0-2.0*f); return mix(mix(lhH(i),lhH(i+vec2(1,0)),f.x),mix(lhH(i+vec2(0,1)),lhH(i+vec2(1,1)),f.x),f.y); }
float lhPuddle(){ vec2 p=vWPos.xz*0.21; float n=lhN(p)*0.55+lhN(p*2.3+7.1)*0.3+lhN(p*5.1+3.3)*0.15; return smoothstep(0.5,0.6,n); }`)
   .replace('#include <map_fragment>','#include <map_fragment>\nfloat lhP=lhPuddle(); diffuseColor.rgb*=mix(1.0,0.22,lhP);')
   .replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=mix(roughnessFactor*0.62,0.03,lhP);')
   .replace('#include <normal_fragment_maps>','#include <normal_fragment_maps>\nnormal=normalize(mix(normal,normalize(vNormal),lhP*0.97));');
};

// ---------- reflejos: un entorno pequeño (cielo oscuro y un halo de sodio en el horizonte) para que el suelo mojado tenga qué reflejar
(function(){ const s=new THREE.Scene(); const g=new THREE.SphereGeometry(50,32,16); const c=[]; const p=g.attributes.position;
  for(let i=0;i<p.count;i++){ const y=p.getY(i)/50; const h=Math.exp(-Math.pow((y-0.04)/0.16,2)); c.push(0.012+0.5*h,0.014+0.27*h,0.022+0.09*h); }
  g.setAttribute('color',new THREE.Float32BufferAttribute(c,3)); s.add(new THREE.Mesh(g,new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.BackSide})));
  const pm=new THREE.PMREMGenerator(renderer); scene.environment=pm.fromScene(s,0.02).texture; pm.dispose(); })();

// ---------- halos (niebla iluminada alrededor de cada luz)
const haloTex=(function(){ const c=document.createElement('canvas'); c.width=c.height=128; const x=c.getContext('2d'); const g=x.createRadialGradient(64,64,0,64,64,64);
  g.addColorStop(0,'rgba(255,255,255,1)'); g.addColorStop(0.08,'rgba(255,255,255,.55)'); g.addColorStop(0.3,'rgba(255,255,255,.14)'); g.addColorStop(0.65,'rgba(255,255,255,.035)'); g.addColorStop(1,'rgba(255,255,255,0)');
  x.fillStyle=g; x.fillRect(0,0,128,128); return new THREE.CanvasTexture(c); })();
function halo(pos,color,size,op){ const s=new THREE.Sprite(new THREE.SpriteMaterial({map:haloTex,color,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:op,fog:false})); s.position.copy(pos); s.scale.set(size,size,1); scene.add(s); return s; }

// ---------- luces del plano de Blender
const lamps=[], spots=[];
// los focos de las torres barren despacio a un lado y a otro
const UP=new THREE.Vector3(0,1,0), DOWN=new THREE.Vector3(0,-1,0);
function spotTick(t){ spots.forEach(s=>{ const d=s.d.clone().applyAxisAngle(UP,Math.sin(t*0.16+s.phase)*0.42); s.L.target.position.copy(s.p).add(d.clone().multiplyScalar(40)); s.L.target.updateMatrixWorld(); s.cone.position.copy(s.p).add(d.clone().multiplyScalar(s.len/2)); s.cone.quaternion.setFromUnitVectors(DOWN,d); }); }
INFO.lights.forEach(l=>{ const p=B(l.pos), col=new THREE.Color(l.color[0],l.color[1],l.color[2]);
  if(l.kind==='POINT'&&l.name==='farola'){ const L=new THREE.PointLight(col,110,34,2); L.position.copy(p); scene.add(L); lamps.push(L); halo(p,0xffa24a,2.6,0.95); halo(p,0xff9038,12,0.26); }
  else if(l.kind==='POINT'&&l.name==='aplique'){ if(!LOW){ const L=new THREE.PointLight(col,7,9,2); L.position.copy(p); scene.add(L); } halo(p,0xffb870,1.3,0.9); halo(p,0xffa860,5,0.3); }
  else if(l.kind==='SPOT'){ const d=B(l.dir).normalize(); const A=THREE.MathUtils.degToRad(6.5); const L=new THREE.SpotLight(0xcfe0ff,3200,110,A,0.35,1.4); L.position.copy(p); scene.add(L); scene.add(L.target);
    if(!LOW){ L.castShadow=true; L.shadow.mapSize.set(2048,2048); L.shadow.camera.near=2; L.shadow.camera.far=110; L.shadow.bias=-0.0006; L.shadow.normalBias=0.03; }
    const h1=halo(p,0xdde8ff,4.5,1), h2=halo(p,0xbfd4ff,16,0.4);
    // haz del foco en la niebla
    const len=75, cone=new THREE.Mesh(new THREE.ConeGeometry(Math.tan(A)*len,len,28,1,true),new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,side:THREE.DoubleSide,
      uniforms:{c:{value:new THREE.Color(0x9fb8e6)}},vertexShader:'varying float h; varying vec3 n; varying vec3 v; void main(){ h=uv.y; n=normalize(normalMatrix*normal); vec4 mv=modelViewMatrix*vec4(position,1.0); v=normalize(-mv.xyz); gl_Position=projectionMatrix*mv; }',
      fragmentShader:'uniform vec3 c; varying float h; varying vec3 n; varying vec3 v; void main(){ float e=pow(abs(dot(normalize(n),normalize(v))),1.6); gl_FragColor=vec4(c*e*pow(h,1.6)*0.3,1.0); }'}));
    scene.add(cone); spots.push({L,cone,p,d,len,phase:spots.length*2.1}); }
});
scene.add(new THREE.HemisphereLight(0x27344f,0x0b0906,0.55));
const moon=new THREE.DirectionalLight(0x8fa8d8,0.22); moon.position.set(-30,50,20); scene.add(moon);
const balizaHalo=[];

// ---------- lluvia: rayas que caen alrededor de la cámara
const RAIN_N=LOW?2000:4500, RAIN_R=22, RAIN_H=16; const rainGeo=new THREE.BufferGeometry(); const rp=new Float32Array(RAIN_N*6), rs=new Float32Array(RAIN_N);
for(let i=0;i<RAIN_N;i++){ const x=(Math.random()*2-1)*RAIN_R, z=(Math.random()*2-1)*RAIN_R, y=Math.random()*RAIN_H; rs[i]=17+Math.random()*9; rp.set([x,y,z,x+0.05,y+0.55,z],i*6); }
rainGeo.setAttribute('position',new THREE.BufferAttribute(rp,3));
const rain=new THREE.LineSegments(rainGeo,new THREE.LineBasicMaterial({color:0xc8d4e0,transparent:true,opacity:0.075,depthWrite:false,fog:true})); rain.frustumCulled=false; scene.add(rain);
function rainTick(dt){ for(let i=0;i<RAIN_N;i++){ const d=rs[i]*dt; let y=rp[i*6+1]-d; if(y<0){ y+=RAIN_H; } rp[i*6+1]=y; rp[i*6+4]=y+0.55; } rainGeo.attributes.position.needsUpdate=true; rain.position.set(camera.position.x,0,camera.position.z);
  const c=(MAP[Math.floor(camera.position.z/T)]||'')[Math.floor(camera.position.x/T)]; rain.visible='_zLV'.indexOf(c||'.')<0; }   // bajo techo no llueve

// ---------- escena de Blender
const b64=s=>{ const bin=atob(s); const u=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i); return u.buffer; };
let ready=false; const stats={meshes:0,inst:0,tris:0};
new THREE.GLTFLoader().parse(b64(D.glb),'',g=>{
  g.scene.updateMatrixWorld(true); const groups=new Map(), singles=[];
  g.scene.traverse(o=>{ if(!o.isMesh)return; const n=(o.material.name||'').replace(/\.\d+$/,'');
    if(n.indexOf('lh_')===0&&M[n.slice(3)])o.material=M[n.slice(3)];
    else { const m=o.material; if(m.map)m.map.anisotropy=4; m.roughness=Math.min(1,(m.roughness||1)*0.72); if(m.emissiveMap||m.name.toLowerCase().indexOf('glass')>=0){ } m.envMapIntensity=0.7; }
    const k=o.geometry.uuid+'|'+o.material.uuid; if(!groups.has(k))groups.set(k,[]); groups.get(k).push(o); });
  groups.forEach(list=>{ const o=list[0]; stats.tris+=(o.geometry.index?o.geometry.index.count:o.geometry.attributes.position.count)/3*list.length;
    if(list.length<3){ list.forEach(m=>{ const c=new THREE.Mesh(m.geometry,m.material); c.applyMatrix4(m.matrixWorld); c.castShadow=c.receiveShadow=true; scene.add(c); stats.meshes++; }); return; }
    const im=new THREE.InstancedMesh(o.geometry,o.material,list.length); list.forEach((m,i)=>im.setMatrixAt(i,m.matrixWorld)); im.instanceMatrix.needsUpdate=true; im.frustumCulled=false; im.castShadow=im.receiveShadow=true; scene.add(im); stats.meshes++; stats.inst+=list.length; });
  ready=true; el('load').textContent='CLIC PARA ENTRAR'; el('intro').classList.add('ok');
},e=>{ el('load').textContent='No se pudo cargar la escena: '+(e&&e.message||e); });

// ---------- resplandor
let composer=null, bloom=null, useBloom=!LOW;
// El compositor trabaja en lineal y con margen (medio flotante); la última pasada hace el revelado: exposición, curva ACES, viñeta y grano.
const FINAL={uniforms:{tDiffuse:{value:null},exposure:{value:1.0},time:{value:0}},vertexShader:'varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
  fragmentShader:`uniform sampler2D tDiffuse; uniform float exposure; uniform float time; varying vec2 vUv;
vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.0,1.0); }
void main(){ vec3 c=texture2D(tDiffuse,vUv).rgb*exposure; c=aces(c); c=pow(c,vec3(1.0/2.2));
  float d=distance(vUv,vec2(0.5)); c*=1.0-0.55*smoothstep(0.35,0.95,d);
  float g=fract(sin(dot(vUv*vec2(1920.0,1080.0)+time*60.0,vec2(12.9898,78.233)))*43758.5453); c+=(g-0.5)*0.022; gl_FragColor=vec4(c,1.0); }`};
let finalPass=null;
function mkComposer(){ const pr=renderer.getPixelRatio(); const rt=new THREE.WebGLRenderTarget(innerWidth*pr,innerHeight*pr,{type:THREE.HalfFloatType,minFilter:THREE.LinearFilter,magFilter:THREE.LinearFilter,format:THREE.RGBAFormat});
  composer=new THREE.EffectComposer(renderer,rt); composer.addPass(new THREE.RenderPass(scene,camera)); bloom=new THREE.UnrealBloomPass(new THREE.Vector2(innerWidth,innerHeight),0.7,0.8,1.0); composer.addPass(bloom);
  finalPass=new THREE.ShaderPass(FINAL); composer.addPass(finalPass); }
if(THREE.EffectComposer&&THREE.UnrealBloomPass)mkComposer(); else useBloom=false;

// ---------- recorrido a pie: WASD y ratón, con las paredes del plano
const solid=(x,y)=>{ if(x<0||y<0||x>=COLS||y>=ROWS)return true; return '#WTcg'.indexOf(MAP[y][x])>=0; };
const P={x:0,z:0,yaw:0,pitch:0,vy:0,bob:0}; (function(){ let sx=2,sy=2; MAP.forEach((r,y)=>{ const i=r.indexOf('P'); if(i>=0){ sx=i; sy=y; } }); P.x=sx*T+T/2; P.z=sy*T+T/2; P.yaw=-2.2; })();
const keys={}; addEventListener('keydown',e=>{ keys[e.code]=true; if(e.code==='KeyB'&&composer){ useBloom=!useBloom; } if(e.code==='KeyH'){ el('hud').hidden=!el('hud').hidden; } }); addEventListener('keyup',e=>{ keys[e.code]=false; });
let locked=false; const cv=renderer.domElement;
el('intro').addEventListener('click',()=>{ if(!ready)return; if(cv.requestPointerLock)cv.requestPointerLock(); el('intro').hidden=true; locked=true; });
document.addEventListener('pointerlockchange',()=>{ locked=document.pointerLockElement===cv; if(!locked&&!TOUCH){ el('intro').hidden=false; } });
addEventListener('mousemove',e=>{ if(document.pointerLockElement!==cv)return; P.yaw-=e.movementX*0.0022; P.pitch=Math.max(-1.3,Math.min(1.3,P.pitch-e.movementY*0.0022)); });
// táctil: arrastrar la mitad derecha gira, la izquierda camina
const TOUCH='ontouchstart' in window; const touch={mx:0,mz:0,ids:{}};
if(TOUCH){ cv.addEventListener('touchstart',e=>{ for(const t of e.changedTouches)touch.ids[t.identifier]={x:t.clientX,y:t.clientY,left:t.clientX<innerWidth/2,ox:t.clientX,oy:t.clientY}; e.preventDefault(); },{passive:false});
  cv.addEventListener('touchmove',e=>{ for(const t of e.changedTouches){ const s=touch.ids[t.identifier]; if(!s)continue; if(s.left){ touch.mx=Math.max(-1,Math.min(1,(t.clientX-s.ox)/60)); touch.mz=Math.max(-1,Math.min(1,(t.clientY-s.oy)/60)); } else { P.yaw-=(t.clientX-s.x)*0.005; P.pitch=Math.max(-1.3,Math.min(1.3,P.pitch-(t.clientY-s.y)*0.005)); } s.x=t.clientX; s.y=t.clientY; } e.preventDefault(); },{passive:false});
  const end=e=>{ for(const t of e.changedTouches){ const s=touch.ids[t.identifier]; if(s&&s.left){ touch.mx=0; touch.mz=0; } delete touch.ids[t.identifier]; } }; cv.addEventListener('touchend',end); cv.addEventListener('touchcancel',end); }
function move(dt){ let f=(keys.KeyW||keys.ArrowUp?1:0)-(keys.KeyS||keys.ArrowDown?1:0)-touch.mz, s=(keys.KeyD||keys.ArrowRight?1:0)-(keys.KeyA||keys.ArrowLeft?1:0)+touch.mx; const l=Math.hypot(f,s); if(l>1){ f/=l; s/=l; }
  const sp=(keys.ShiftLeft?6.2:2.6)*dt; const sin=Math.sin(P.yaw), cos=Math.cos(P.yaw); const dx=(-sin*f+cos*s)*sp, dz=(-cos*f-sin*s)*sp; const R=0.32;
  const free=(x,z)=>!solid(Math.floor((x-R)/T),Math.floor((z-R)/T))&&!solid(Math.floor((x+R)/T),Math.floor((z-R)/T))&&!solid(Math.floor((x-R)/T),Math.floor((z+R)/T))&&!solid(Math.floor((x+R)/T),Math.floor((z+R)/T));
  if(free(P.x+dx,P.z))P.x+=dx; if(free(P.x,P.z+dz))P.z+=dz; if(l>0.05)P.bob+=dt*(keys.ShiftLeft?13:8.5);
  camera.position.set(P.x,1.66+Math.sin(P.bob)*0.028*Math.min(1,l),P.z); camera.rotation.set(0,0,0); camera.rotation.order='YXZ'; camera.rotation.y=P.yaw; camera.rotation.x=P.pitch; }
// vista inicial y vistas fijas (teclas 1 a 4) para comparar con los renders de Blender
const VIEWS=[[3,11.4,-0.95,0.02],[18.4,18.0,0.9,0.04],[40.2,13.4,-1.75,0.03],[25,40,0.5,0.05]];
addEventListener('keydown',e=>{ const i=['Digit1','Digit2','Digit3','Digit4'].indexOf(e.code); if(i>=0){ const v=VIEWS[i]; P.x=v[0]; P.z=v[1]; P.yaw=v[2]; P.pitch=v[3]; } });
if(Q.get('v')){ const v=VIEWS[(+Q.get('v')||1)-1]; P.x=v[0]; P.z=v[1]; P.yaw=v[2]; P.pitch=v[3]; }

addEventListener('resize',()=>{ camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth,innerHeight); if(composer)composer.setSize(innerWidth,innerHeight); });
let last=performance.now(), fpsT=0, fpsN=0, t=0;
function frame(now){ const dt=Math.min(0.05,(now-last)/1000); last=now; t+=dt; move(dt); rainTick(dt); spotTick(t);
  if(finalPass)finalPass.uniforms.time.value=t; if(composer){ bloom.enabled=useBloom; composer.render(); } else renderer.render(scene,camera);
  fpsT+=dt; fpsN++; if(fpsT>0.5){ el('fps').textContent=Math.round(fpsN/fpsT)+' fps · '+Math.round(stats.tris/1000)+' mil triángulos · resplandor '+(useBloom?'sí':'no'); fpsT=0; fpsN=0; }
  requestAnimationFrame(frame); }
requestAnimationFrame(frame);
window.__ESC={scene,camera,renderer,P,stats,M,isReady:()=>ready,spotTick,frameOnce:()=>{ move(0); if(composer)composer.render(); else renderer.render(scene,camera); }};
})();
