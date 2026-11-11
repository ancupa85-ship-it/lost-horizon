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
const scene=new THREE.Scene(); const FOGC=new THREE.Color(0x0f0b09); scene.background=FOGC; scene.fog=new THREE.FogExp2(FOGC.getHex(),0.034);
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
  piel:std({color:0xa8785c,roughness:0.6}), pelo:std({color:0x15100b,roughness:0.6}), capote:std({color:0x070906,roughness:0.5}), uniforme:std({color:0x12160d,roughness:0.85}),
  traje:std({color:0x14181f,roughness:0.45}), cuero:std({color:0x2a1c12,roughness:0.5}),
  aviso:std({color:0xa8801a,roughness:0.6}), marisma:std({color:0x05090a,roughness:0.12,metalness:0.2}),
  ventana_on:std({color:0x2a2010,roughness:0.3,emissive:0xffa050,emissiveIntensity:3.2}), ventana_off:std({color:0x05080a,roughness:0.06,metalness:0.3}),
  bombilla:std({color:0x000000,emissive:0xff9a38,emissiveIntensity:9}), baliza:std({color:0x000000,emissive:0xff1408,emissiveIntensity:8}), foco:std({color:0x000000,emissive:0xcfe2ff,emissiveIntensity:12}),
};
M.hormigon=M.muro; M.suelo_int=std({map:tex('floor_diff',2,true),color:0x8c8c8c,roughness:0.55}); M.techo_int=std({color:0x6a655c,roughness:0.95});
// charcos: en el suelo, un ruido en coordenadas del mundo baja la rugosidad, aplana el relieve y oscurece el asfalto
const RIP={value:0};
M.suelo.onBeforeCompile=sh=>{ sh.uniforms.lhT=RIP;
  sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vWPos;').replace('#include <project_vertex>','#include <project_vertex>\nvWPos=(modelMatrix*vec4(transformed,1.0)).xyz;');
  sh.fragmentShader=sh.fragmentShader.replace('#include <common>',`#include <common>
varying vec3 vWPos;
float lhH(vec2 p){ return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
float lhN(vec2 p){ vec2 i=floor(p),f=fract(p); f=f*f*(3.0-2.0*f); return mix(mix(lhH(i),lhH(i+vec2(1,0)),f.x),mix(lhH(i+vec2(0,1)),lhH(i+vec2(1,1)),f.x),f.y); }
uniform float lhT;
vec2 lhRip(vec2 p){ vec2 g=vec2(0.0); { vec2 q=p*2.1, i=floor(q), f=fract(q); float h=lhH(i), t=fract(lhT*(0.7+0.5*h)+h*9.0); vec2 c=vec2(0.3+0.4*lhH(i+1.7),0.3+0.4*lhH(i+4.1)), v=f-c; float d=length(v), r=t*0.42; g+=normalize(v+1e-5)*sin((d-r)*46.0)*smoothstep(0.07,0.0,abs(d-r))*(1.0-t); } return g; }
float lhPuddle(){ vec2 p=vWPos.xz*0.21; float n=lhN(p)*0.55+lhN(p*2.3+7.1)*0.3+lhN(p*5.1+3.3)*0.15; return smoothstep(0.5,0.6,n); }`)
   .replace('#include <map_fragment>','#include <map_fragment>\nfloat lhP=lhPuddle(); diffuseColor.rgb*=mix(1.0,0.22,lhP);')
   .replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=mix(roughnessFactor*0.62,0.03,lhP);')
   .replace('#include <normal_fragment_maps>','#include <normal_fragment_maps>\nnormal=normalize(mix(normal,normalize(vNormal),lhP*0.97)); if(lhP>0.02&&vViewPosition.z<22.0){ vec2 rg=lhRip(vWPos.xz)*lhP*0.35; normal=normalize(normal+(viewMatrix*vec4(rg.x,0.0,rg.y,0.0)).xyz); }   /* ondas de las gotas */');
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
const lamps=[], spots=[], beams=[];
// los focos de las torres barren despacio a un lado y a otro
const UP=new THREE.Vector3(0,1,0), DOWN=new THREE.Vector3(0,-1,0);
function spotTick(t){ spots.forEach(s=>{ const d=s.d.clone().applyAxisAngle(UP,Math.sin(t*0.16+s.phase)*0.42); s.L.target.position.copy(s.p).add(d.clone().multiplyScalar(40)); s.L.target.updateMatrixWorld(); s.cone.position.copy(s.p).add(d.clone().multiplyScalar(s.len/2)); s.cone.quaternion.setFromUnitVectors(DOWN,d); }); beams.forEach(b=>{ b.uniforms.time.value=t; }); }
const SPOTS=[], LIT=[];   // LIT: fuentes de luz que cuentan para el sigilo (y que se pueden apagar de un tiro)
INFO.lights.forEach(l=>{ const p=B(l.pos), col=new THREE.Color(l.color[0],l.color[1],l.color[2]);
  if(l.kind==='POINT'&&l.name==='farola'){ const L=new THREE.PointLight(col,110,34,2); L.position.copy(p); scene.add(L); lamps.push(L);
    if(!LOW){ L.castShadow=true; L.shadow.mapSize.set(1024,1024); L.shadow.camera.near=0.25; L.shadow.camera.far=34; L.shadow.bias=-0.003; L.shadow.normalBias=0.05; L.shadow.autoUpdate=false; } /* la escena no se mueve: la sombra se calcula una vez */ LIT.push({x:p.x,y:p.y,z:p.z,R:12,on:true,L,I:110,h:[halo(p,0xffa24a,2.6,0.95),halo(p,0xff9038,12,0.26)]}); }
  else if(l.kind==='POINT'&&l.name==='aplique'){ let L=null; if(!LOW){ L=new THREE.PointLight(col,7,9,2); L.position.copy(p); scene.add(L); } LIT.push({x:p.x,y:p.y,z:p.z,R:5.5,on:true,L,I:7,h:[halo(p,0xffb870,1.3,0.9),halo(p,0xffa860,5,0.3)]}); }
  else if(l.kind==='POINT'&&l.name==='interior'){ const L=new THREE.PointLight(col,l.power/120*24,9.5,1.6); L.position.copy(p); scene.add(L); LIT.push({x:p.x,y:p.y,z:p.z,R:7.5,on:true,L,I:L.intensity,h:[halo(p.clone().add(new THREE.Vector3(0,0.18,0)),0xffd9a0,0.9,0.9)]}); }
  else if(l.kind==='SPOT'){ const d=B(l.dir).normalize(); const A=THREE.MathUtils.degToRad(6.5); const L=new THREE.SpotLight(0xcfe0ff,280,110,A*1.5,0.7,1.4)   /* 2600 quemaba en blanco las fachadas enteras */; L.position.copy(p); scene.add(L); scene.add(L.target);
    if(!LOW){ L.castShadow=true; L.shadow.mapSize.set(1024,1024); L.shadow.camera.near=2; L.shadow.camera.far=110; L.shadow.bias=-0.0006; L.shadow.normalBias=0.03; L.shadow.autoUpdate=false; SPOTS.push(L); }   /* la sombra del foco se rehace cada pocos fotogramas, no en todos */
    const h1=halo(p,0xdde8ff,4.5,1), h2=halo(p,0xbfd4ff,16,0.4);
    // haz del foco en la niebla: varias capas anchas y tenues, sin borde, que se apagan con la distancia
    const len=70, cone=new THREE.Group();
    [[0.55,0.5],[1.0,0.3],[1.7,0.16],[2.6,0.09]].forEach(([w,k])=>{ const m=new THREE.Mesh(new THREE.ConeGeometry(Math.tan(A*w)*len,len,40,24,true),new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,side:THREE.DoubleSide,
      uniforms:{c:{value:new THREE.Color(0x9fb8e6)},k:{value:k},time:{value:0}},vertexShader:'varying float h; varying vec3 n; varying vec3 v; varying vec3 wp; void main(){ h=uv.y; n=normalize(normalMatrix*normal); vec4 mv=modelViewMatrix*vec4(position,1.0); v=normalize(-mv.xyz); wp=(modelMatrix*vec4(position,1.0)).xyz; gl_Position=projectionMatrix*mv; }',
      fragmentShader:'uniform vec3 c; uniform float k; uniform float time; varying float h; varying vec3 n; varying vec3 v; varying vec3 wp; void main(){ float e=pow(abs(dot(normalize(n),normalize(v))),3.2); float f=pow(h,2.6)*smoothstep(0.0,0.12,h)*smoothstep(1.0,0.985,h); float s=0.8+0.2*sin(wp.x*0.7+time*0.6)*sin(wp.z*0.5-time*0.4+wp.y); gl_FragColor=vec4(c*e*f*k*s*0.42,1.0); }'}));
      cone.add(m); beams.push(m.material); });
    scene.add(cone); spots.push({L,cone,p,d,len,phase:spots.length*2.1}); }
});
const hemi=new THREE.HemisphereLight(0x27344f,0x0b0906,0.36); scene.add(hemi);
const moon=new THREE.DirectionalLight(0x8fa8d8,0.22); moon.position.set(-30,50,20); scene.add(moon);
// cielo de tormenta: cúpula con nubes que se mueven; en el horizonte tiene el color de la niebla para que la base se funda con él. Cada tanto, un relámpago ilumina nubes y patio, y el trueno llega después.
const SKY={m:null,f:0,t:14+Math.random()*10,seq:null,th:0};
function skyNoise(){ const N=128, c=document.createElement('canvas'); c.width=c.height=N; const x=c.getContext('2d'), im=x.createImageData(N,N), hh=(a,b,p)=>{ a=((a%p)+p)%p; b=((b%p)+p)%p; const v=Math.sin(a*127.1+b*311.7+p*17.3)*43758.5453; return v-Math.floor(v); };
  const vn=(u,v,p)=>{ const i=Math.floor(u), j=Math.floor(v); let f=u-i, g=v-j; f=f*f*(3-2*f); g=g*g*(3-2*g); return (hh(i,j,p)*(1-f)+hh(i+1,j,p)*f)*(1-g)+(hh(i,j+1,p)*(1-f)+hh(i+1,j+1,p)*f)*g; };
  for(let y=0;y<N;y++)for(let k=0;k<N;k++){ let v=0, a=0.5; for(const p of [4,8,16,32]){ v+=a*vn(k/N*p,y/N*p,p); a*=0.5; } const q=(y*N+k)*4; im.data[q]=im.data[q+1]=im.data[q+2]=Math.min(255,v/0.94*255); im.data[q+3]=255; } x.putImageData(im,0,0);
  const t=new THREE.CanvasTexture(c); t.wrapS=t.wrapT=THREE.RepeatWrapping; t.minFilter=THREE.LinearFilter; t.generateMipmaps=false; return t; }
(function(){ const g=new THREE.SphereGeometry(320,24,12), m=new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,fog:false,uniforms:{time:{value:0},flash:{value:0},fogc:{value:FOGC.clone()},fp:{value:new THREE.Vector2(0.3,0.5)},nz:{value:skyNoise()}},
  vertexShader:'varying vec3 d; void main(){ d=normalize(position); gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
  fragmentShader:`uniform float time; uniform float flash; uniform vec3 fogc; uniform vec2 fp; varying vec3 d;
uniform sampler2D nz;
float fbm(vec2 p){ return texture2D(nz,p*0.11).r; }
void main(){ float up=max(d.y,0.0); vec2 q=d.xz/(up+0.22)*1.4+vec2(time*0.012,time*0.007); float c=fbm(q), c2=fbm(q*2.1+vec2(-time*0.02,4.0));
  vec3 hi=mix(vec3(0.016,0.02,0.034),vec3(0.07,0.062,0.07),smoothstep(0.35,0.8,c)); hi+=vec3(0.05,0.03,0.015)*smoothstep(0.5,0.9,c2)*(1.0-up);   /* panzas de nube teñidas por el sodio de la base */
  vec3 col=mix(fogc,hi,smoothstep(0.0,0.3,up));
  float near=exp(-6.0*distance(d.xz,fp)); col+=vec3(0.55,0.62,0.8)*flash*(0.25+1.6*near)*(0.4+0.8*c)*smoothstep(-0.05,0.25,d.y);
  gl_FragColor=vec4(col,1.0); }`}); const o=new THREE.Mesh(g,m); o.frustumCulled=false; o.renderOrder=-10; scene.add(o); SKY.m=o; })();
function skyTick(dt,t){ RIP.value=t; patioTick(dt,t); const u=SKY.m.material.uniforms; SKY.m.position.copy(camera.position); u.time.value=t; SKY.t-=dt;
  if(SKY.t<=0){ SKY.t=22+Math.random()*34; SKY.seq=[[0,1],[0.07,0.15],[0.13,0.8],[0.3,0.25],[0.36,0.6],[0.9,0]]; SKY.k=0; const a=Math.random()*6.28; u.fp.value.set(Math.cos(a)*0.7,Math.sin(a)*0.7); SKY.th=0.8+Math.random()*2.2; SKY.thG=0.25+Math.random()*0.3; }
  if(SKY.seq){ SKY.k+=dt; const q=SKY.seq; let v=0; for(let i=0;i<q.length-1;i++)if(SKY.k>=q[i][0]&&SKY.k<q[i+1][0]){ const f=(SKY.k-q[i][0])/(q[i+1][0]-q[i][0]); v=q[i][1]+(q[i+1][1]-q[i][1])*f; } if(SKY.k>=q[q.length-1][0]){ SKY.seq=null; v=0; } SKY.f=v; } else SKY.f=0;
  if(SKY.th>0){ SKY.th-=dt; if(SKY.th<=0){ sNoise(2.2,75,0.4,SKY.thG*1.8); } }
  u.flash.value=SKY.f; hemi.intensity=0.36+SKY.f*2.2; moon.intensity=0.22+SKY.f*1.6; }
const balizaHalo=[];

// ---------- lluvia: rayas que caen alrededor de la cámara
const RAIN_N=LOW?2000:4500, RAIN_R=22, RAIN_H=16; const rainGeo=new THREE.BufferGeometry(); const rp=new Float32Array(RAIN_N*6), rs=new Float32Array(RAIN_N);
for(let i=0;i<RAIN_N;i++){ const x=(Math.random()*2-1)*RAIN_R, z=(Math.random()*2-1)*RAIN_R, y=Math.random()*RAIN_H; rs[i]=17+Math.random()*9; rp.set([x,y,z,x+0.05,y+0.55,z],i*6); }
rainGeo.setAttribute('position',new THREE.BufferAttribute(rp,3));
const rain=new THREE.LineSegments(rainGeo,new THREE.LineBasicMaterial({color:0xc8d4e0,transparent:true,opacity:0.075,depthWrite:false,fog:true})); rain.frustumCulled=false; scene.add(rain);
function rainTick(dt){ const cx=camera.position.x, cz=camera.position.z; for(let i=0;i<RAIN_N;i++){ const d=rs[i]*dt; let y=rp[i*6+1]-d; if(y<0){ y+=RAIN_H; } rp[i*6+1]=y; const c=(MAP[Math.floor((cz+rp[i*6+2])/T)]||'')[Math.floor((cx+rp[i*6])/T)]; rp[i*6+4]=y+(y<INFO.HB+0.2&&'_zLVWDbd'.indexOf(c||'.')>=0?0:0.55); } rainGeo.attributes.position.needsUpdate=true; rain.position.set(cx,0,cz); }   // bajo techo no llueve: la gota que cae sobre un edificio se queda sin trazo

// ---------- escena de Blender
const b64=s=>{ const bin=atob(s); const u=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i); return u.buffer; };
let ready=false; const stats={meshes:0,inst:0,tris:0};
// ---------- personas: mallas con esqueleto, reposo y andar; el equipo (casco, capote, arma) se cuelga del hueso que le toca
const GEAR=[], PEOPLE=[];
function fixPersona(m,n){ const tela=/suit|pants|boots/.test(n); m.roughness=tela?0.82:0.62; m.metalness=0; m.envMapIntensity=0.35; if(/casualsuit/.test(n))m.color.setScalar(1.2); if(m.transparent){ m.transparent=false; m.alphaTest=0.35; m.depthWrite=true; } }
// guardias añadidos en el visor: reutilizan la malla de otro (no cabe un modelo más en el archivo) con su propia ronda, en casillas
const EXTRA=[{name:'vega',src:'moya',rz:1.57,wps:[[6,24],[20,24],[20,21],[20,24]]},{name:'ramos',src:'peris',rz:1.57,wps:[[2,13],[13,13],[13,10],[13,13]]},{name:'vidal',src:'ibarra',rz:0,wps:[[31,11]],npc:true}];
function loadPeople(done){ const base=(D.info.people||[]).filter(q=>D.people&&D.people[q.name]); const list=base.concat(EXTRA.map(e=>{ const sq=base.find(q=>q.name===e.src); return sq&&{name:e.name,src:e.src,npc:e.npc,sq,rz:e.rz,wps:e.wps,pos:[e.wps[0][0]*T+T/2,-(e.wps[0][1]*T+T/2),sq.pos[2]]}; }).filter(Boolean)); let left=list.length; if(!left)return done();
  list.forEach(q=>new THREE.GLTFLoader().parse(b64(D.people[q.src||q.name]),'',g=>{ const root=g.scene, q0=q.sq||q; root.position.set(q0.pos[0],q0.pos[2],-q0.pos[1]); root.rotation.y=q0.rz; scene.add(root);
    root.traverse(o=>{ if(o.isMesh){ o.frustumCulled=false; o.castShadow=true; o.receiveShadow=true; fixPersona(o.material,(o.material.name||'').replace(/\.\d+$/,'')); if(o.material.map)o.material.map.anisotropy=4; stats.tris+=(o.geometry.index?o.geometry.index.count:o.geometry.attributes.position.count)/3; } });
    const mixer=new THREE.AnimationMixer(root), acts={}; g.animations.forEach(c=>{ acts[c.name]=mixer.clipAction(c); }); if(acts.idle)acts.idle.play(); if(acts.down){ acts.down.setLoop(THREE.LoopOnce,1); acts.down.clampWhenFinished=true; } mixer.update(0); root.updateMatrixWorld(true);
    GEAR.filter(x=>x.who===(q.src||q.name)).forEach(x=>{ const b=root.getObjectByName(x.bone); if(!b)return; let m=x.mesh; const sl=(x.bone==='spine_03'&&x.mat!=='capote')||x.bone==='hand_r'; if(q.src){ m=new THREE.Mesh(x.mesh.geometry,x.mesh.material); m.applyMatrix4(x.m0); m.castShadow=m.receiveShadow=true; scene.add(m); m.updateMatrixWorld(true); } b.attach(m); if(sl)(root.userData.slung=root.userData.slung||[]).push(m); });
    if(q.src){ root.position.set(q.pos[0],q.pos[2],-q.pos[1]); root.rotation.y=q.rz; }
    const p={slung:root.userData.slung||[],hr:root.getObjectByName('hand_r'),hl:root.getObjectByName('hand_l'),q,root,mixer,acts,i:0,yaw:q.rz,wps:(q.wps||[]).map(w=>[w[0]*T+T/2,w[1]*T+T/2])};
    if(q.name!=='cuttlas'&&p.wps.length>1&&acts.walk){ acts.idle.stop(); acts.walk.play(); root.position.set(p.wps[0][0],q.pos[2],p.wps[0][1]); p.i=1; }
    if(q.name==='cuttlas'&&acts.stand&&acts.sneak){ PL.p=p; PL.yaw=q.rz; P.x=q.pos[0]; P.z=-q.pos[1]; P.yaw=q.rz+Math.PI; P.pitch=-0.12; }
    PEOPLE.push(p); if(!--left)done(); },e=>{ console.error('persona',q.name,e); if(!--left)done(); })); }
const WALK_V=1.4/1.25;   // metros por ciclo / segundos por ciclo: los pies no patinan
// ---------- guardias: ronda, vista (cono y línea de visión por el plano), oído, sospecha, persecución y captura
const NOISE={x:0,z:0,r:0}, NOISES=[], ALERT={level:0,msg:'',msgT:0,caught:0};
const cellOf=(x,z)=>[Math.floor(x/T),Math.floor(z/T)];
function blocked(x0,z0,x1,z1,low){ const d=Math.hypot(x1-x0,z1-z0), n=Math.ceil(d/0.35); for(let i=1;i<n;i++){ const x=x0+(x1-x0)*i/n, z=z0+(z1-z0)*i/n; const r=MAP[Math.floor(z/T)], c=r&&r[Math.floor(x/T)]; if(!c||'#WTLV'.indexOf(c)>=0||(low&&'cg'.indexOf(c)>=0))return true; } return false; }
function bfs(a,b){ const key=(x,y)=>y*COLS+x, prev=new Map([[key(a[0],a[1]),-1]]), q=[a]; let hit=false;
  while(q.length){ const c=q.shift(); if(c[0]===b[0]&&c[1]===b[1]){ hit=true; break; } for(const d of [[1,0],[-1,0],[0,1],[0,-1]]){ const x=c[0]+d[0], y=c[1]+d[1]; if(x<0||y<0||x>=COLS||y>=ROWS||prev.has(key(x,y))||'#WTcgsLVb'.indexOf(MAP[y][x])>=0)continue; prev.set(key(x,y),key(c[0],c[1])); q.push([x,y]); } }
  if(!hit)return null; const out=[]; let k=key(b[0],b[1]); while(k!==-1){ out.unshift([k%COLS,Math.floor(k/COLS)]); k=prev.get(k); } return out; }
function mark(ch,col){ const c=document.createElement('canvas'); c.width=c.height=64; const x=c.getContext('2d'); x.font='bold 56px sans-serif'; x.textAlign='center'; x.textBaseline='middle'; x.lineWidth=6; x.strokeStyle='#000'; x.strokeText(ch,32,34); x.fillStyle=col; x.fillText(ch,32,34);
  const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c),depthTest:false,transparent:true,fog:false})); sp.scale.set(0.5,0.5,1); sp.position.y=2.25; sp.visible=false; sp.renderOrder=10; return sp; }
function gAct(p,name,ts){ if(p.acts[name]&&p.act!==name){ const a=p.acts[p.act], b=p.acts[name]; b.reset(); b.play(); if(a)a.crossFadeTo(b,0.25,false); p.act=name; } if(name==='walk'&&p.acts.walk)p.acts.walk.timeScale=ts||1; }
function face(p,want,dt,rate){ let da=want-p.yaw; while(da>Math.PI)da-=2*Math.PI; while(da<-Math.PI)da+=2*Math.PI; p.yaw+=Math.max(-rate*dt,Math.min(rate*dt,da)); p.root.rotation.y=p.yaw; return da; }
function stepTo(p,tx,tz,v,dt){ const r=p.root.position, dx=tx-r.x, dz=tz-r.z, d=Math.hypot(dx,dz); if(d<0.12){ return true; } const da=face(p,Math.atan2(dx,dz),dt,v>1.6?5:2.6), turning=Math.abs(da)>0.6;
  gAct(p,'walk',(turning?0.5:1)*v/WALK_V); const s=Math.min((turning?0.25:1)*v*dt,d); let nx=r.x+Math.sin(p.yaw)*s, nz=r.z+Math.cos(p.yaw)*s; p.avT=Math.max(0,(p.avT||0)-dt*0.5);
  // los muebles se rodean: si el paso entra en uno, se desliza por el lado libre; si se atasca, pasa (mejor que quedarse clavado)
  if(p.avT<4&&gObst(nx,nz)&&!gObst(r.x,r.z)&&!gObst(tx,tz)){ p.avT+=dt*1.5; let ok=false; for(const k of [p.avS||1,-(p.avS||1)]){ for(const a of [1.0,1.57,2.2]){ const ax=r.x+Math.sin(p.yaw+k*a)*s, az=r.z+Math.cos(p.yaw+k*a)*s; if(!gObst(ax,az)&&!gWall(ax,az)){ nx=ax; nz=az; p.avS=k; ok=true; break; } } if(ok)break; } if(!ok)return false; }
  r.x=nx; r.z=nz; return false; }
function gObst(x,z){ for(const o of OBST){ const dx=x-o[1], dz=z+o[2]; if(Math.abs(dx)>3||Math.abs(dz)>3)continue; const c=Math.cos(o[5]), sn=Math.sin(o[5]), u=dx*c-dz*sn, v=-dx*sn-dz*c; if(Math.abs(u)<o[3]+0.3&&Math.abs(v)<o[4]+0.3)return true; } return false; }
function gWall(x,z){ const c=(MAP[Math.floor(z/T)]||'')[Math.floor(x/T)]; return !c||'#WTLVcgsb'.indexOf(c)>=0; }
function goTo(p,tx,tz,v,dt){ const r=p.root.position, a=cellOf(r.x,r.z), b=cellOf(tx,tz); if((a[0]===b[0]&&a[1]===b[1])||!blocked(r.x,r.z,tx,tz,true))return stepTo(p,tx,tz,v,dt);
  p.pathT=(p.pathT||0)-dt; if(!p.path||p.pathT<=0||p.pathK!==b[0]+','+b[1]){ p.path=bfs(a,b); p.pathT=0.5; p.pathK=b[0]+','+b[1]; } if(!p.path||p.path.length<2){ gAct(p,'idle'); return true; }
  let n=p.path[1]; if(p.path.length>2&&n[0]===a[0]&&n[1]===a[1])n=p.path[2]; stepTo(p,n[0]*T+T/2,n[1]*T+T/2,v,dt); return false; }
function sees(p){ if(CELL.on)return 0; const r=p.root.position, dx=P.x-r.x, dz=P.z-r.z, d=Math.hypot(dx,dz), lit=PL.lit===undefined?1:PL.lit, range=(PL.crouch?7:13)*(0.45+0.55*lit); if(d>range)return 0;
  let da=Math.atan2(dx,dz)-p.yaw; while(da>Math.PI)da-=2*Math.PI; while(da<-Math.PI)da+=2*Math.PI; if(Math.abs(da)>(p.state==='chase'?1.3:0.85)&&d>1.6)return 0;
  if(blocked(r.x,r.z,P.x,P.z,PL.crouch))return 0; return (0.3+1.5*(1-d/range))*(PL.crouch?0.6:1)*(0.55+0.45*lit)*(p.wary>0?1.35:1); }
// ---------- sonido, todo sintetizado: lluvia de fondo (apagada bajo techo), pasos propios y de los guardias cercanos, avisos de sospecha y de alarma. M lo silencia.
const SND={ac:null,on:true,rg:null,rf:null,ph:0,gT:0};
function sac(){ if(!SND.on)return null; try{ const AC=window.AudioContext||window.webkitAudioContext; if(!AC)return null; if(!SND.ac){ SND.ac=FX.ac||new AC(); FX.ac=SND.ac; } if(SND.ac.state==='suspended')SND.ac.resume(); return SND.ac; }catch(e){ return null; } }
function sNoise(dur,f,q,g,type){ const ac=sac(); if(!ac)return; const n=Math.floor(ac.sampleRate*dur), b=ac.createBuffer(1,n,ac.sampleRate), d=b.getChannelData(0); for(let i=0;i<n;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/n,2.5);
  const src=ac.createBufferSource(); src.buffer=b; const fl=ac.createBiquadFilter(); fl.type=type||'lowpass'; fl.frequency.value=f; fl.Q.value=q; const v=ac.createGain(); v.gain.value=g; src.connect(fl); fl.connect(v); v.connect(ac.destination); src.start(); }
function sTone(f,dur,g,type,at,f2){ const ac=sac(); if(!ac)return; const t=ac.currentTime+(at||0), o=ac.createOscillator(), v=ac.createGain(), fl=ac.createBiquadFilter(); fl.type='lowpass'; fl.frequency.value=1400; o.type=type||'sine'; o.frequency.setValueAtTime(f,t); if(f2)o.frequency.linearRampToValueAtTime(f2,t+dur);
  v.gain.setValueAtTime(0.0001,t); v.gain.linearRampToValueAtTime(g,t+0.03); v.gain.exponentialRampToValueAtTime(0.0001,t+dur); o.connect(fl); fl.connect(v); v.connect(ac.destination); o.start(t); o.stop(t+dur+0.05); }
function sRain(){ const ac=sac(); if(!ac||SND.rg)return; const n=ac.sampleRate*2, b=ac.createBuffer(1,n,ac.sampleRate), d=b.getChannelData(0); for(let i=0;i<n;i++)d[i]=Math.random()*2-1; const src=ac.createBufferSource(); src.buffer=b; src.loop=true;
  const hp=ac.createBiquadFilter(); hp.type='highpass'; hp.frequency.value=500; SND.rf=ac.createBiquadFilter(); SND.rf.type='lowpass'; SND.rf.frequency.value=6500; SND.rg=ac.createGain(); SND.rg.gain.value=0.0001; src.connect(hp); hp.connect(SND.rf); SND.rf.connect(SND.rg); SND.rg.connect(ac.destination); src.start(); }
function sIndoor(){ const c=(MAP[Math.floor(camera.position.z/T)]||'')[Math.floor(camera.position.x/T)]; return '_zd'.indexOf(c||'.')>=0; }
function sStep(moving,fast){ const k=Math.floor(P.bob/Math.PI); if(k===SND.ph)return; SND.ph=k; if(!moving||!PL.p)return; const inn=sIndoor(); sNoise(0.09,inn?260:520,0.8,(PL.crouch||PL.drag?0.035:fast?0.2:0.1)*(inn?1.3:1)); }
// ---------- música sintetizada (no cabe un archivo de audio): un secuenciador en re menor con tres estados. Sigilo: colchón grave, pulso lento y notas sueltas. Sospecha: tictac y una segunda menor que incomoda. Alarma: más rápido, bajo en corcheas, bombo y caja. T la apaga.
const MUS={on:true,g:null,pad:null,next:0,step:0,lv:0,n:0}; try{ MUS.on=localStorage.getItem('lh-musica')!=='0'; }catch(e){}
const MHZ=n=>440*Math.pow(2,(n-69)/12);
function mNote(f,t,dur,g,type,cut,f2){ const ac=SND.ac, o=ac.createOscillator(), v=ac.createGain(), fl=ac.createBiquadFilter(); fl.type='lowpass'; fl.frequency.value=cut||1200; o.type=type||'sine'; o.frequency.setValueAtTime(f,t); if(f2)o.frequency.exponentialRampToValueAtTime(f2,t+dur*0.6);
  v.gain.setValueAtTime(0.0001,t); v.gain.linearRampToValueAtTime(g,t+0.012); v.gain.exponentialRampToValueAtTime(0.0001,t+dur); o.connect(fl); fl.connect(v); v.connect(MUS.g); o.start(t); o.stop(t+dur+0.05); MUS.n++; }
function mHit(t,dur,g,f,type){ const ac=SND.ac; if(!MUS.nb){ const n=ac.sampleRate*0.4, b=ac.createBuffer(1,n,ac.sampleRate), d=b.getChannelData(0); for(let i=0;i<n;i++)d[i]=Math.random()*2-1; MUS.nb=b; } const src=ac.createBufferSource(); src.buffer=MUS.nb; const fl=ac.createBiquadFilter(); fl.type=type||'highpass'; fl.frequency.value=f; const v=ac.createGain(); v.gain.setValueAtTime(g,t); v.gain.exponentialRampToValueAtTime(0.0001,t+dur); src.connect(fl); fl.connect(v); v.connect(MUS.g); src.start(t); src.stop(t+dur+0.02); MUS.n++; }
function musTick(){ const ac=SND.ac; if(!ac||ac.state!=='running')return; if(!MUS.g){ MUS.g=ac.createGain(); MUS.g.gain.value=0; MUS.g.connect(ac.destination);
    // colchón: dos sierras desafinadas en re y una quinta, muy filtradas, que respiran
    const fl=ac.createBiquadFilter(); fl.type='lowpass'; fl.frequency.value=320; fl.Q.value=1.5; const pg=ac.createGain(); pg.gain.value=0.05; [[38,-6],[38,7],[45,0]].forEach(q=>{ const o=ac.createOscillator(); o.type='sawtooth'; o.frequency.value=MHZ(q[0]); o.detune.value=q[1]; o.connect(fl); o.start(); }); fl.connect(pg); pg.connect(MUS.g);
    const lfo=ac.createOscillator(), lg=ac.createGain(); lfo.frequency.value=0.07; lg.gain.value=120; lfo.connect(lg); lg.connect(fl.frequency); lfo.start(); MUS.pad=fl; MUS.next=ac.currentTime+0.1; }
  MUS.g.gain.setTargetAtTime(MUS.on&&PL.p?0.55:0,ac.currentTime,0.4); if(!MUS.on||!PL.p){ MUS.next=ac.currentTime+0.1; return; }
  if(MUS.next<ac.currentTime)MUS.next=ac.currentTime+0.05;   // tras una pausa o un tirón no se amontonan notas
  while(MUS.next<ac.currentTime+0.3){ const t=MUS.next, L=ALERT.caught?0:ALERT.level, st=MUS.step%32, b=st%4===0, PENT=[62,65,67,69,72,74];
    if(L===2){ const bs=[38,38,41,38,43,38,44,38][Math.floor(st/2)%8]; if(st%2===0)mNote(MHZ(bs),t,0.2,0.2,'sawtooth',500); if(st%8===0)mNote(120,t,0.22,0.5,'sine',400,42); if(st%8===4)mHit(t,0.16,0.16,1400,'bandpass'); if(st%2===1)mHit(t,0.04,0.045,7000);
      if(st%16===0){ [62,65,69].forEach(n=>mNote(MHZ(n),t,0.5,0.045,'sawtooth',1500)); } if(st%16===10)[63,68].forEach(n=>mNote(MHZ(n),t,0.35,0.04,'sawtooth',1500)); }
    else if(L===1){ if(st%8===0)mNote(MHZ(38),t,0.9,0.3,'sine',300); if(st%8===6)mNote(MHZ(38),t,0.3,0.16,'sine',300); if(st%2===0)mHit(t,0.03,st%4===0?0.035:0.018,8000); if(st%16===8)mNote(MHZ(63),t,1.6,0.03,'sawtooth',900); if(st%32===0)mNote(MHZ(62),t,2.4,0.03,'sawtooth',800); if(st%32===20)mNote(MHZ(75),t,0.9,0.02,'triangle',2000); }
    else { if(st%16===0)mNote(MHZ(38),t,1.6,0.26,'sine',260); if(st%16===10)mNote(MHZ(38),t,0.5,0.1,'sine',260); if(b&&Math.random()<0.2){ const n=PENT[Math.floor(Math.random()*PENT.length)]; mNote(MHZ(n),t,2.2,0.03,'triangle',1800); mNote(MHZ(n+12),t+0.02,1.4,0.008,'sine',3000); } if(st===24&&Math.random()<0.5)mNote(MHZ(57),t,3.0,0.022,'sawtooth',600); }
    MUS.lv+=(L-MUS.lv)*0.25; if(MUS.pad)MUS.pad.frequency.setTargetAtTime(280+MUS.lv*260,t,0.5); MUS.next+=L===2?0.134:L===1?0.2:0.227; MUS.step++; } }
addEventListener('keydown',e=>{ if(e.code==='KeyT'){ MUS.on=!MUS.on; try{ localStorage.setItem('lh-musica',MUS.on?'1':'0'); }catch(e2){} say(MUS.on?'MÚSICA ACTIVADA':'MÚSICA APAGADA',1.5); } });
function sndTick(dt){ if(!SND.rg||!SND.ac)return; musTick(); const inn=sIndoor(), t=SND.ac.currentTime; SND.rf.frequency.setTargetAtTime(inn?650:6500,t,0.25); SND.rg.gain.setTargetAtTime(inn?0.035:0.085,t,0.25);
  SND.gT-=dt; if(SND.gT<=0){ let bd=15, g=null; PEOPLE.forEach(o=>{ if(o===PL.p||o.dead||o.act!=='walk')return; const d=Math.hypot(o.root.position.x-P.x,o.root.position.z-P.z); if(d<bd){ bd=d; g=o; } });
    if(g){ sNoise(0.1,380,0.9,0.22/(1+bd*0.4)); SND.gT=0.5/((g.acts.walk&&g.acts.walk.timeScale)||1); } else SND.gT=0.2; } }
addEventListener('keydown',e=>{ if(e.code==='KeyM'){ SND.on=!SND.on; if(SND.ac){ if(SND.on)SND.ac.resume(); else SND.ac.suspend(); } } });
const BARK={suspect:['¿Qué ha sido eso?','¿Hay alguien ahí?','¿Eh? ¿Quién anda?'],search:['Voy a echar un vistazo.','Espera, voy a mirar.'],quiet:['Nada. Será el viento.','Habrán sido las ratas.','Aquí no hay nadie.'],chase:['¡Alto! ¡Alto o disparo!','¡Intruso! ¡Dad la alarma!'],lost:['¿Dónde se ha metido?','Lo he perdido. ¡Buscadlo!'],body:['¡Hombre caído! ¡Aquí!'],lamp:['Esa luz estaba encendida…','¿Quién ha apagado eso?','Otra bombilla fundida. Qué raro.'],door:['Esa puerta estaba cerrada.','¿Quién ha abierto aquí?'],gone:['No está en su puesto. Aquí pasa algo.']};
const gName=p=>p.q.name==='ibarra'?'Cabo Ibarra':p.q.name==='moya'?'Sargento Moya':p.q.name==='peris'?'Soldado Peris':p.q.name[0].toUpperCase()+p.q.name.slice(1);
// radio: Cuttlas lleva la frecuencia de la base pinchada, así que oye a control. Las frases van en cola para que no se pisen.
const RADIO={q:[],t:28,i:0,miss:null};
function radio(txt,who){ RADIO.q.push('<i>'+(who||'Control')+' (radio)</i> '+txt); }
function gWary(t){ PEOPLE.forEach(o=>{ if(o!==PL.p&&o.state&&!o.dead)o.wary=Math.max(o.wary||0,t); }); }
function radioTick(dt){ if(!PL.p||ALERT.caught)return; if(RADIO.q.length&&!(ALERT.subT>0)){ ALERT.sub=RADIO.q.shift(); ALERT.subT=3.2; sNoise(0.18,2400,3,0.05,'bandpass'); sTone(1250,0.06,0.03,'square'); }
  const gs=PEOPLE.filter(o=>o!==PL.p&&o.state); if(!gs.length)return;
  // quien iba a buscar al que no contesta: al llegar, o lo encuentra (lo hace peopleTick) o da el aviso de que falta
  if(RADIO.miss){ const m=RADIO.miss; m.t+=dt; if(m.o.found||m.g.dead||m.g.state==='chase'){ RADIO.miss=null; } else if(m.t>3&&(m.g.state==='return'||m.g.state==='patrol'||m.t>45)){ RADIO.miss=null; m.o.found=true; radio(BARK.gone[0],gName(m.g)); radio('A todas las unidades: falta '+gName(m.o)+'. Ojos abiertos.'); gWary(60); } return; }
  if(ALERT.level>0){ RADIO.t=Math.max(RADIO.t,12); return; } RADIO.t-=dt; if(RADIO.t>0)return; RADIO.t=26+Math.random()*10; const o=gs[RADIO.i++%gs.length];
  if(!o.dead){ if(RADIO.i%2)radio(gName(o)+', novedades. <i>'+gName(o)+'</i> Sin novedad.'); return; } if(o.found)return;
  let g=null, bd=1e9; const bc=bodyC(o); gs.forEach(x=>{ if(x.dead||x.state==='chase')return; const d=Math.hypot(x.root.position.x-bc[0],x.root.position.z-bc[1]); if(d<bd){ bd=d; g=x; } }); radio(gName(o)+', novedades… '+gName(o)+', ¿me recibes?'); if(!g)return;
  radio(gName(g)+', acércate a ver qué pasa con '+gName(o)+'.'); radio('Recibido. Voy.',gName(g)); const h=o.wps.length?o.wps[o.i%o.wps.length]:[o.q.pos[0],-o.q.pos[1]]; g.seen=o.hidden?h.slice():[bc[0],bc[1]]; setState(g,'search'); g.stT=-20; RADIO.miss={o,g,t:0}; }
function bark(p,k){ if(!BARK[k])return; const r=p.root.position; if(!PL.p||Math.hypot(r.x-P.x,r.z-P.z)>24)return; const L=BARK[k], n=gName(p); ALERT.sub='<b>'+n+'</b> '+L[Math.floor(Math.random()*L.length)]; ALERT.subT=2.8; }
function setState(p,st){ if(p.state&&st!==p.state)bark(p,st==='suspect'?'suspect':st==='chase'?'chase':st==='search'?(p.state==='chase'?'lost':'search'):st==='return'&&p.state==='search'?'quiet':'x'); if(st==='chase'&&p.state!=='chase'){ MS.alarms=(MS.alarms||0)+1; if(!MS.alarmSaid){ MS.alarmSaid=true; radio('Te han visto. Ahora eres ruido. Si te cogen, no te conocemos; si sales, tampoco.'); } } if(st==='chase')p.fireT=1.1; if(st!==p.state&&p.state){ if(st==='chase'){ sTone(196,0.7,0.1,'sawtooth',0,185); sTone(233,0.7,0.08,'sawtooth',0.02,220); sTone(98,0.9,0.12,'triangle'); } else if(st==='suspect')sTone(620,0.22,0.045,'sine',0,700); } p.state=st; p.stT=0; p.q1.visible=st==='suspect'||st==='search'; p.q2.visible=st==='chase'; }
// los guardias tiran en la alarma: aciertan más de cerca y menos si vas agachado o corriendo; cada tiro se oye en media base
const TR=[]; let trK=0; function tracer(a,b){ if(TR.length<4){ const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(6),3)); const l=new THREE.Line(g,new THREE.LineBasicMaterial({color:0xffe0a0,transparent:true,opacity:0.8,fog:false})); l.frustumCulled=false; scene.add(l); TR.push({l,t:0}); }
  const o=TR[trK++%TR.length], q=o.l.geometry.attributes.position; q.setXYZ(0,a[0],a[1],a[2]); q.setXYZ(1,b[0],b[1],b[2]); q.needsUpdate=true; o.l.visible=true; o.t=0.07; }
// fusil en las manos mientras apunta: se tiende de la mano derecha a la izquierda; el que llevaba colgado se esconde
function mkRifle(){ const g=new THREE.Group(), w=M.madera||M.hierro, k=M.oscuro||M.hierro, add=(geo,m,z,y)=>{ const o=new THREE.Mesh(geo,m); o.position.set(0,y||0,z); o.castShadow=true; g.add(o); return o; };
  add(new THREE.BoxGeometry(0.045,0.11,0.34),w,-0.2,-0.03); add(new THREE.BoxGeometry(0.05,0.06,0.5),w,0.22,-0.005); add(new THREE.BoxGeometry(0.04,0.05,0.2),k,0.02,0.03); const b=add(new THREE.CylinderGeometry(0.011,0.011,0.62,8),k,0.6,0.02); b.rotation.x=Math.PI/2; add(new THREE.BoxGeometry(0.02,0.09,0.04),k,0.06,-0.07); g.visible=false; scene.add(g); return g; }
const _a=new THREE.Vector3(), _b=new THREE.Vector3(), _z=new THREE.Vector3(0,0,1);
function aimTick(p){ const on=p.act==='aim'&&!p.dead&&p.hr&&p.hl; if(!on){ if(p.rifle&&p.rifle.visible){ p.rifle.visible=false; p.slung.forEach(m=>{ m.visible=true; }); } return; }
  if(!p.rifle)p.rifle=mkRifle(); if(!p.rifle.visible){ p.rifle.visible=true; p.slung.forEach(m=>{ m.visible=false; }); }
  p.hr.getWorldPosition(_a); p.hl.getWorldPosition(_b); const fx=Math.sin(p.yaw), fz=Math.cos(p.yaw); _b.sub(_a); const dy=Math.max(-0.12,Math.min(0.12,_b.y*0.5)); _b.set(fx,dy,fz).normalize(); p.rifle.position.copy(_a).addScaledVector(_b,0.04); p.rifle.position.y+=0.04; p.rifle.quaternion.setFromUnitVectors(_z,_b); }
function gFire(p,d){ const r=p.root.position, fast=keys.ShiftLeft||keys.ShiftRight, ch=Math.max(0.12,Math.min(0.7,0.78-d*0.06))*(PL.crouch?0.7:1)*(fast?0.75:1), hit=Math.random()<ch;
  const a=[r.x+Math.sin(p.yaw)*1.1,1.42,r.z+Math.cos(p.yaw)*1.1], b=hit?[P.x,PL.eye-0.35,P.z]:[P.x+(Math.random()-0.5)*1.6,0.3+Math.random()*1.8,P.z+(Math.random()-0.5)*1.6]; tracer(a,b);
  sNoise(0.22,900,0.6,Math.min(0.5,1.6/(1+d*0.25)),'bandpass'); sNoise(0.3,160,0.7,Math.min(0.5,1.4/(1+d*0.25)));
  PEOPLE.forEach(o=>{ if(o!==p&&o!==PL.p&&o.state&&!o.dead&&o.state!=='chase'&&Math.hypot(o.root.position.x-r.x,o.root.position.z-r.z)<28){ o.seen=[r.x,r.z]; setState(o,'search'); } });
  if(hit&&!ALERT.caught){ PL.hp-=24; PL.hurt=1; PL.hpT=0; sNoise(0.12,300,1,0.3); if(PL.hp<=0){ PL.hp=0; ALERT.caught=3.2; ALERT.info=false; ALERT.msg='ABATIDO'; ALERT.msgT=3.2; PL.drag=null; } } }
function lightTick(dt){ PL.lk=(PL.lk||0)+1; if(PL.lk%5===0||PL.lit===undefined){ let v=0.08; const inn='_zd'.indexOf((MAP[Math.floor(P.z/T)]||'')[Math.floor(P.x/T)]||'.')>=0;
    for(const s of LIT){ if(!s.on)continue; const d=Math.hypot(s.x-P.x,s.z-P.z); if(d>=s.R)continue; const k=1-d/s.R; if(k>v&&!blocked(s.x,s.z,P.x,P.z,false))v=k; }
    // foco de torreta: solo cuenta el círculo brillante del suelo, y un muro, un cobertizo o unas cajas entre el foco y tú te dan sombra (se comprueba con la altura real del rayo)
    let spot=false; if(!inn)for(const s of spots){ _a.copy(s.L.target.position).sub(s.p).normalize(); _b.set(P.x-s.p.x,1.0-s.p.y,P.z-s.p.z); const d=_b.length(); if(d<70&&_b.normalize().dot(_a)>Math.cos(0.055)&&!shade(s.p)){ spot=true; } }
    if(spot)v=Math.max(v,0.8); PL.litT=Math.min(1,v*1.25); PL.spot=spot; }
  PL.lit=(PL.lit===undefined?PL.litT:PL.lit+(PL.litT-PL.lit)*Math.min(1,dt*4)); PL.spotCd=Math.max(0,(PL.spotCd||0)-dt);
  // el foco no delata al instante: avisa y da tiempo a salir; agachado tarda mucho más. Solo va a mirar el guardia más cercano.
  if(PL.spot&&!PL.spotCd){ if(!(PL.spotT>0))sTone(880,0.12,0.04,'sine'); PL.spotT=(PL.spotT||0)+dt*(PL.crouch?0.35:1); } else PL.spotT=Math.max(0,(PL.spotT||0)-dt*1.5);
  if(PL.p&&PL.spotT>2.2&&!PL.spotCd&&!ALERT.caught){ PL.spotCd=18; PL.spotT=0; ALERT.info=false; ALERT.msg='EL FOCO TE HA VISTO'; ALERT.msgT=2.6; sTone(520,0.5,0.07,'square',0,500); let g=null, bd=30; PEOPLE.forEach(o=>{ if(o===PL.p||!o.state||o.dead||o.state!=='patrol')return; const d=Math.hypot(o.root.position.x-P.x,o.root.position.z-P.z); if(d<bd){ bd=d; g=o; } }); if(g){ g.seen=[P.x,P.z]; setState(g,'suspect'); } }
  else if(PL.p&&PL.spot&&!PL.spotCd&&!ALERT.caught&&!(ALERT.msgT>0)){ ALERT.info=true; ALERT.msg='EL FOCO TE ROZA: SAL DE LA LUZ'; ALERT.msgT=0.4; }
  const e=el('luzT'); if(e)setH(e,PL.spot?'EN EL FOCO':PL.lit>0.6?'A LA VISTA':PL.lit>0.28?'PENUMBRA':'A OSCURAS'); const sb=el('sub'); if(sb){ if(ALERT.subT>0){ ALERT.subT-=dt; setH(sb,ALERT.sub); } else setH(sb,''); } }
function shade(sp){ const dx=sp.x-P.x, dz=sp.z-P.z, d=Math.hypot(dx,dz), n=Math.ceil(d/0.5); for(let i=1;i<n;i++){ const f=i/n, h=1+(sp.y-1)*f; if(h>INFO.HW+0.5)break; const c=(MAP[Math.floor((P.z+dz*f)/T)]||'')[Math.floor((P.x+dx*f)/T)]; if(!c)continue; const H=c==='#'?INFO.HW:'WLVb_zdD'.indexOf(c)>=0?INFO.HB:c==='c'?1.5:c==='g'?2.2:0; if(H>h)return true; } return false; }
function lampOff(s){ s.on=false; if(s.L)s.L.intensity=0; s.h.forEach(h=>{ h.visible=false; }); sNoise(0.25,3800,2,0.25,'bandpass'); sNoise(0.4,6000,1,0.12,'highpass'); NOISES.push({x:s.x,z:s.z,r:10}); say('LUZ APAGADA',1.6); PL.lit=undefined; }
function lampsOn(){ RADIO.q.length=0; RADIO.miss=null; RADIO.t=28; LIT.forEach(s=>{ s.on=true; s.noted=false; if(s.L)s.L.intensity=s.I; s.h.forEach(h=>{ h.visible=true; }); }); }
function hpTick(dt){ lightTick(dt); radioTick(dt); if(RADIO.cd>0)RADIO.cd-=dt; TR.forEach(o=>{ if(o.t>0){ o.t-=dt; if(o.t<=0)o.l.visible=false; } }); PL.hpT=(PL.hpT||0)+dt; if(PL.hpT>6&&PL.hp<100&&!ALERT.caught)PL.hp=Math.min(100,PL.hp+dt*9); PL.hurt=Math.max(0,(PL.hurt||0)-dt*1.6);
  const v=el('vida'); if(v){ v.hidden=!PL.p; const w=Math.round(PL.hp)+'%'; if(v._w!==w){ v._w=w; el('vidaB').style.width=w; v.className=PL.hp<35?'mal':''; } } const dn=el('dano'); if(dn){ const op=(Math.min(0.85,PL.hurt*0.7+(PL.hp<35?0.25:0))).toFixed(2); if(dn._o!==op){ dn._o=op; dn.style.opacity=op; } } }
function resetStealth(){ if(DOGS.length){ dogsClear(); DOG.done=true; } PL.hp=100; PL.hurt=0; PEOPLE.forEach(p=>{ if(p===PL.p||p.q.npc)return; if(p.q.name==='roig'){ roigHome(p); return; } p.frz=false; p.dead=false; p.wary=0; p.found=false; p.hidden=false; p.meter=0; p.lost=0; p.path=null; const h=p.wps.length?p.wps[0]:[p.q.pos[0],-p.q.pos[1]]; p.root.position.x=h[0]; p.root.position.z=h[1]; p.i=p.wps.length>1?1:0; p.yaw=p.q.rz; p.root.rotation.y=p.yaw; setState(p,'patrol'); gAct(p,p.wps.length>1?'walk':'idle'); });
  const q=PL.p.q; P.x=q.pos[0]; P.z=-q.pos[1]; P.yaw=q.rz+Math.PI; P.pitch=-0.12; PL.yaw=q.rz; PL.crouch=PL.third; NOISE.r=0; PL.mag=8; PL.res=16; PL.rel=0; PL.drag=null; if(MS.spawn){ P.x=MS.spawn[0]; P.z=MS.spawn[1]; P.yaw=MS.spawn[2]; } }
function peopleTick(dt){ const live=PL.p&&!ALERT.caught; let top=0;
  if(ALERT.caught){ ALERT.caught-=dt; if(ALERT.caught<=0){ ALERT.caught=0; if(PL.p&&!MS.cellDone&&!MS.done)toCell(); else resetStealth(); } }
  PEOPLE.forEach(p=>{ p.mixer.update(dt); if(p===PL.p)return; if(p.q.name==='roig'){ roigTick(p,dt,live); return; } if(p.q.npc){ if(p.root.visible!==CELL.vis){ p.root.visible=CELL.vis; p.root.position.y=CELL.vis?0:-40; } p.root.rotation.y=CELL.back?Math.PI:0; return; } aimTick(p); if(p.frz)return; if(!p.q1){ p.q1=mark('?','#ffd23a'); p.q2=mark('!','#ff3b2f'); p.root.add(p.q1); p.root.add(p.q2); p.state='patrol'; p.stT=0; p.meter=0; p.act=p.wps.length>1&&p.acts.walk?'walk':'idle'; p.home=p.wps.length?null:[p.q.pos[0],-p.q.pos[1]]; }
    const r=p.root.position; if(p.dead){ p.q1.visible=p.q2.visible=false; return; } const vis=live?sees(p):0; p.stT+=dt;
    if(live&&p.state!=='chase')PEOPLE.forEach(o=>{ if(!o.dead||o.found||o.hidden||o===PL.drag)return; const bc=bodyC(o), b={x:bc[0],z:bc[1]}, dx=b.x-r.x, dz=b.z-r.z, d=Math.hypot(dx,dz); if(d>13)return; let da=Math.atan2(dx,dz)-p.yaw; while(da>Math.PI)da-=2*Math.PI; while(da<-Math.PI)da+=2*Math.PI; if((Math.abs(da)>0.95&&d>2)||blocked(r.x,r.z,b.x,b.z,true))return;
      o.found=true; p.seen=[b.x,b.z]; p.meter=Math.max(p.meter,0.6); setState(p,'search'); bark(p,'body'); radio('¡Hombre caído! Es '+gName(o)+'.',gName(p)); radio('A todas las unidades: tenemos una baja. Registrad la base.'); gWary(75); });
    if(p.wary>0)p.wary-=dt;
    if(live&&(p.state==='patrol'||p.state==='return')&&((p.nk=(p.nk||0)+1)%12===0)){ const note=(x,z,R)=>{ const dx=x-r.x, dz=z-r.z, d=Math.hypot(dx,dz); if(d>R)return false; let da=Math.atan2(dx,dz)-p.yaw; while(da>Math.PI)da-=2*Math.PI; while(da<-Math.PI)da+=2*Math.PI; if(Math.abs(da)>1.0)return false; const k=Math.max(0,(d-1.3)/d); return !blocked(r.x,r.z,r.x+dx*k,r.z+dz*k,false); };
      for(const s of LIT){ if(s.on||s.noted||!note(s.x,s.z,s.R))continue; s.noted=true; p.seen=[s.x,s.z]; setState(p,'search'); bark(p,'lamp'); p.wary=Math.max(p.wary||0,40); break; }
      for(const c in DOORS){ const d=DOORS[c]; if(!d.want||d.noted||!note(d.cx,d.cz,9))continue; d.noted=true; p.seen=[d.cx,d.cz]; setState(p,'search'); bark(p,'door'); p.wary=Math.max(p.wary||0,40); break; } }
    if(vis>0){ p.meter=Math.min(1.2,p.meter+vis*dt*(p.state==='chase'?3:1.15)); p.seen=[P.x,P.z]; p.lost=0; } else { p.meter=Math.max(0,p.meter-dt*0.3); p.lost=(p.lost||0)+dt; }
    if(live&&p.state!=='chase')for(const N of [NOISE].concat(NOISES)){ if(!(N.r>0))continue; const d=Math.hypot(N.x-r.x,N.z-r.z); if(d<N.r*(blocked(r.x,r.z,N.x,N.z,false)?0.5:1)){ p.seen=[N.x,N.z]; if(p.state==='patrol'||p.state==='return')setState(p,'suspect'); } }
    if(live&&p.meter>=1&&p.state!=='chase'){ setState(p,'chase'); ALERT.info=false; ALERT.msg='¡ALTO! ¡INTRUSO EN EL PATIO!'; ALERT.msgT=3; if(!(RADIO.cd>0)){ RADIO.cd=25; radio('¡Intruso en la base! ¡Lo tengo a la vista!',gName(p)); radio('A todas las unidades: intruso. Estad atentos.'); } gWary(45); PEOPLE.forEach(o=>{ if(o!==p&&o!==PL.p&&o.state&&o.state!=='chase'&&Math.hypot(o.root.position.x-r.x,o.root.position.z-r.z)<30){ o.seen=p.seen.slice(); setState(o,'search'); } }); }
    else if(live&&p.meter>0.35&&p.state==='patrol')setState(p,'suspect');
    if(p.state==='patrol'){ if(p.wps.length>1&&p.acts.walk){ const w=p.wps[p.i]; if(stepTo(p,w[0],w[1],WALK_V,dt))p.i=(p.i+1)%p.wps.length; } else { gAct(p,'idle'); face(p,p.q.rz,dt,2); } }
    else if(p.state==='suspect'){ gAct(p,'idle'); if(p.seen)face(p,Math.atan2(p.seen[0]-r.x,p.seen[1]-r.z),dt,3); if(p.stT>1.6)setState(p,'search'); }
    else if(p.state==='search'){ if(!p.seen||goTo(p,p.seen[0],p.seen[1],1.6,dt)||p.stT>14){ gAct(p,'idle'); p.look=(p.look||0)+dt; p.yaw+=Math.sin(p.look*1.6)*dt*1.2; p.root.rotation.y=p.yaw; if(p.look>3.5){ p.look=0; setState(p,'return'); } } }
    else if(p.state==='chase'){ const d=Math.hypot(P.x-r.x,P.z-r.z); if(!live){ setState(p,'return'); } else if(vis>0&&d<1.25){ gAct(p,'idle'); ALERT.caught=3.2; ALERT.info=false; ALERT.msg='CAPTURADO'; ALERT.msgT=3.2; }
      else if(vis>0&&d<9){ gAct(p,p.acts.aim?'aim':'idle'); face(p,Math.atan2(P.x-r.x,P.z-r.z),dt,6); p.fireT=(p.fireT===undefined?1.1:p.fireT)-dt; if(p.fireT<=0){ p.fireT=0.9+Math.random()*0.6; gFire(p,d); } }
      else { const tgt=p.lost<0.8?[P.x,P.z]:p.seen; goTo(p,tgt[0],tgt[1],2.3,dt); if(p.lost>3.5){ p.meter=0.3; setState(p,'search'); } } }
    else if(p.state==='return'){ const h=p.home||p.wps[p.i]; if(goTo(p,h[0],h[1],WALK_V,dt)||p.stT>40)setState(p,'patrol'); }
    top=Math.max(top,p.state==='chase'?2:(p.state==='suspect'||p.state==='search')?1:0); ALERT.meter=Math.max(ALERT.meter||0,p.state==='chase'?1:p.meter); });
  NOISE.r=0; NOISES.length=0; ALERT.level=top; if(ALERT.msgT>0)ALERT.msgT-=dt;
  const st=el('estado'); if(st){ st.hidden=!PL.p; st.className=['ok','sos','ale'][top]; el('estadoT').textContent=['SIGILO','SOSPECHA','ALERTA'][top]; el('estadoB').style.width=Math.round(Math.min(1,ALERT.meter||0)*100)+'%'; ALERT.meter=0;
    const m=el('aviso'); m.textContent=ALERT.msgT>0?ALERT.msg:''; m.className=ALERT.caught?'cap':(ALERT.info||ALERT.msg==='CUERPO OCULTO'?'ok':''); if(ALERT.msgT<=0)ALERT.info=false; } }
new THREE.GLTFLoader().parse(b64(D.glb),'',g=>{
  g.scene.updateMatrixWorld(true); const groups=new Map(), singles=[];
  g.scene.traverse(o=>{ if(!o.isMesh)return; const n=(o.material.name||'').replace(/\.\d+$/,'');
    const gm=/^gear_([a-z]+)_(head|spine_03|hand_r|pelvis)_/.exec(o.name||'');
    if(gm){ if(!M.arma)M.arma=new THREE.MeshStandardMaterial({color:0x4a4e58,roughness:0.32,metalness:0.85,envMapIntensity:1.6}); const c=new THREE.Mesh(o.geometry,gm[1]==='cuttlas'&&gm[2]==='hand_r'?M.arma:(M[n.slice(3)]||o.material));   /* la pistola de Cuttlas, de acero pavonado: se distingue del traje negro */ c.applyMatrix4(o.matrixWorld); c.castShadow=true; c.receiveShadow=true; scene.add(c); GEAR.push({who:gm[1],bone:gm[2],mesh:c,m0:c.matrix.clone(),mat:n.slice(3)}); stats.meshes++; return; }
    if(n.indexOf('lh_')===0&&M[n.slice(3)])o.material=M[n.slice(3)];
    else if(/^(cuttlas|ibarra|moya|peris)_/.test(n))fixPersona(o.material,n);
    else { const m=o.material; if(m.map)m.map.anisotropy=4; m.roughness=Math.min(1,(m.roughness||1)*0.72); if(m.emissiveMap||m.name.toLowerCase().indexOf('glass')>=0){ } m.envMapIntensity=0.7; }
    o.userData.noShadow=/street_lamp|wall_lamp/i.test(o.material.name||'')||['bombilla','foco','baliza','ventana_on'].indexOf(n.slice(3))>=0;
    const k=o.geometry.uuid+'|'+o.material.uuid; if(!groups.has(k))groups.set(k,[]); groups.get(k).push(o); });
  groups.forEach(list=>{ const o=list[0]; stats.tris+=(o.geometry.index?o.geometry.index.count:o.geometry.attributes.position.count)/3*list.length;
    if(list.length<3){ list.forEach(m=>{ const c=new THREE.Mesh(m.geometry,m.material); c.applyMatrix4(m.matrixWorld); c.castShadow=!m.userData.noShadow; c.receiveShadow=true; scene.add(c); stats.meshes++; }); return; }
    const im=new THREE.InstancedMesh(o.geometry,o.material,list.length); list.forEach((m,i)=>im.setMatrixAt(i,m.matrixWorld)); im.instanceMatrix.needsUpdate=true; im.frustumCulled=false; im.castShadow=!o.userData.noShadow; im.receiveShadow=true; scene.add(im); stats.meshes++; stats.inst+=list.length; });
  lamps.forEach(L=>{ if(L.castShadow)L.shadow.needsUpdate=true; });
  loadPeople(()=>{ ready=true; MS.sig=[MS.key,MS.door,MS.code,MS.vault,MS.file].join(); const cont=load(); el('load').textContent=cont?'CLIC PARA CONTINUAR · N EMPIEZA DE NUEVO':'CLIC PARA ENTRAR'; el('intro').classList.add('ok'); });
},e=>{ el('load').textContent='No se pudo cargar la escena: '+(e&&e.message||e); });

// ---------- resplandor
// ---------- interiores vestidos sin gastar tamaño: todo se dibuja en lienzos. Zócalo pintado en cada pared, carteles, plano de la base, tablón, cuadro de turnos y pantallas en las bombillas.
function deco(){ const cv=(w,h,fn)=>{ const c=document.createElement('canvas'); c.width=w; c.height=h; const x=c.getContext('2d'); fn(x,w,h); const t=new THREE.CanvasTexture(c); t.encoding=THREE.sRGBEncoding; t.anisotropy=4; return t; };
  const grime=(x,w,h,n,a)=>{ for(let i=0;i<n;i++){ x.fillStyle='rgba('+(20+Math.random()*30|0)+','+(16+Math.random()*20|0)+',10,'+(Math.random()*a)+')'; const r=4+Math.random()*26; x.beginPath(); x.ellipse(Math.random()*w,Math.random()*h,r,r*(0.4+Math.random()),Math.random()*3,0,6.3); x.fill(); } };
  const paper=(x,w,h,col)=>{ x.fillStyle=col||'#cfc3a0'; x.fillRect(0,0,w,h); grime(x,w,h,26,0.12); x.strokeStyle='rgba(60,40,20,0.35)'; x.lineWidth=2; x.strokeRect(1,1,w-2,h-2); };
  const lines=(x,x0,y0,w,n,gap)=>{ x.fillStyle='rgba(30,26,20,0.75)'; for(let i=0;i<n;i++)x.fillRect(x0,y0+i*gap,w*(0.55+0.45*Math.random()),2); };
  const T_=[
   cv(256,352,(x,w,h)=>{ paper(x,w,h,'#c9b98c'); x.fillStyle='#8a1a12'; x.fillRect(0,0,w,74); x.fillStyle='#efe6c8'; x.font='bold 30px sans-serif'; x.textAlign='center'; x.fillText('ZONA',w/2,34); x.fillText('RESTRINGIDA',w/2,64); x.fillStyle='#1c1814'; x.font='bold 22px sans-serif'; x.fillText('DESTACAMENTO',w/2,120); x.font='bold 46px serif'; x.fillText('TARSIS',w/2,168); x.strokeStyle='#1c1814'; x.lineWidth=5; x.beginPath(); x.arc(w/2,236,40,0,6.3); x.moveTo(w/2-28,236+28); x.lineTo(w/2+28,236-28); x.stroke(); x.font='15px sans-serif'; x.fillText('Prohibido el paso sin',w/2,304); x.fillText('autorización escrita',w/2,324); }),
   cv(384,288,(x,w,h)=>{ x.fillStyle='#1d3350'; x.fillRect(0,0,w,h); grime(x,w,h,18,0.1); x.strokeStyle='rgba(190,215,240,0.25)'; x.lineWidth=1; for(let i=0;i<w;i+=24){ x.beginPath(); x.moveTo(i,0); x.lineTo(i,h); x.stroke(); } for(let i=0;i<h;i+=24){ x.beginPath(); x.moveTo(0,i); x.lineTo(w,i); x.stroke(); }
     const k=Math.min((w-40)/COLS,(h-64)/ROWS), ox=(w-COLS*k)/2, oy=40; for(let y=0;y<ROWS;y++)for(let c=0;c<COLS;c++){ const ch=MAP[y][c]; if('#WLV'.indexOf(ch)>=0){ x.fillStyle='rgba(215,232,250,0.9)'; x.fillRect(ox+c*k,oy+y*k,k+0.5,k+0.5); } else if(ch==='T'){ x.fillStyle='rgba(240,190,90,0.9)'; x.fillRect(ox+c*k,oy+y*k,k,k); } else if('_z'.indexOf(ch)>=0){ x.fillStyle='rgba(215,232,250,0.16)'; x.fillRect(ox+c*k,oy+y*k,k+0.5,k+0.5); } }
     x.fillStyle='#dfeaf6'; x.font='bold 17px monospace'; x.fillText('DESTACAMENTO TARSIS · PLANTA GENERAL',16,26); x.font='11px monospace'; x.fillText('E 1:400 · USO INTERNO',16,h-8); }),
   cv(384,256,(x,w,h)=>{ x.fillStyle='#5a3d22'; x.fillRect(0,0,w,h); x.fillStyle='#9a7648'; x.fillRect(10,10,w-20,h-20); for(let i=0;i<900;i++){ x.fillStyle='rgba(60,36,14,'+Math.random()*0.35+')'; x.fillRect(10+Math.random()*(w-20),10+Math.random()*(h-20),2,2); }
     [[26,24,96,128,'#d8cfae'],[136,30,110,78,'#e2dcc6'],[262,22,96,138,'#cdbf96'],[140,124,104,108,'#d9d2b8'],[30,166,92,66,'#e6dfc0'],[266,172,90,58,'#c9b88c']].forEach((q,i)=>{ x.save(); x.translate(q[0]+q[2]/2,q[1]+q[3]/2); x.rotate((i%3-1)*0.035); x.fillStyle='rgba(0,0,0,0.3)'; x.fillRect(-q[2]/2+3,-q[3]/2+3,q[2],q[3]); x.fillStyle=q[4]; x.fillRect(-q[2]/2,-q[3]/2,q[2],q[3]); lines(x,-q[2]/2+8,-q[3]/2+14,q[2]-16,Math.floor(q[3]/11)-2,10); x.fillStyle=i%2?'#a02018':'#28466e'; x.beginPath(); x.arc(0,-q[3]/2+6,4,0,6.3); x.fill(); x.restore(); }); }),
   cv(320,256,(x,w,h)=>{ paper(x,w,h,'#d6cca8'); x.fillStyle='#1c1814'; x.font='bold 19px sans-serif'; x.fillText('SERVICIO DE GUARDIA',14,28); x.font='12px monospace'; ['TURNO','PUESTO','NOMBRE'].forEach((t,i)=>x.fillText(t,14+i*100,52)); x.strokeStyle='rgba(30,26,20,0.7)'; x.lineWidth=1; for(let i=0;i<8;i++){ x.beginPath(); x.moveTo(10,60+i*24); x.lineTo(w-10,60+i*24); x.stroke(); } [110,210].forEach(v=>{ x.beginPath(); x.moveTo(v,40); x.lineTo(v,228); x.stroke(); });
     [['22-02','PATIO N','IBARRA'],['22-02','PATIO S','MOYA'],['22-02','PORTÓN','VEGA'],['22-02','BARRACÓN','RAMOS'],['02-06','RETÉN','PERIS'],['02-06','TORRE','—'],['02-06','ARCHIVO','—']].forEach((r,i)=>r.forEach((t,j)=>x.fillText(t,14+j*100,78+i*24))); x.fillStyle='#8a1a12'; x.font='bold 13px sans-serif'; x.fillText('NOVEDADES A CONTROL CADA MEDIA HORA',14,248); }),
   cv(256,256,(x,w,h)=>{ x.clearRect(0,0,w,h); x.fillStyle='#22201c'; x.beginPath(); x.arc(128,128,122,0,6.3); x.fill(); x.fillStyle='#d9d2bc'; x.beginPath(); x.arc(128,128,108,0,6.3); x.fill(); x.fillStyle='#1c1814'; for(let i=0;i<12;i++){ const a=i*Math.PI/6; x.save(); x.translate(128+Math.sin(a)*92,128-Math.cos(a)*92); x.rotate(a); x.fillRect(-3,-9,6,18); x.restore(); } x.lineCap='round'; x.strokeStyle='#1c1814'; x.lineWidth=8; x.beginPath(); x.moveTo(128,128); x.lineTo(128-50,128-28); x.stroke(); x.lineWidth=5; x.beginPath(); x.moveTo(128,128); x.lineTo(128+34,128-74); x.stroke(); x.fillStyle='#8a1a12'; x.beginPath(); x.arc(128,128,7,0,6.3); x.fill(); })];
  const SZ=[[0.62,0.85],[1.25,0.94],[1.3,0.87],[0.95,0.76],[0.42,0.42]];
  const mats=T_.map((t,i)=>new THREE.MeshStandardMaterial({map:t,color:0xa8a8a8,roughness:0.92,metalness:0,transparent:i===4,alphaTest:i===4?0.5:0}));
  // zócalo: media pared pintada de verde cuartel con su cenefa y roña cerca del suelo
  const zt=cv(256,256,(x,w,h)=>{ x.clearRect(0,0,w,h); x.fillStyle='rgb(58,70,52)'; x.fillRect(0,14,w,h-14); x.fillStyle='rgba(24,28,22,0.95)'; x.fillRect(0,8,w,7); x.fillStyle='rgba(18,16,12,0.9)'; x.fillRect(0,h-22,w,22); const g=x.createLinearGradient(0,h-110,0,h); g.addColorStop(0,'rgba(20,16,10,0)'); g.addColorStop(1,'rgba(20,16,10,0.6)'); x.fillStyle=g; x.fillRect(0,h-110,w,110); grime(x,w,h,40,0.16); for(let i=0;i<14;i++){ x.fillStyle='rgba(150,150,130,'+(0.05+Math.random()*0.1)+')'; x.fillRect(Math.random()*w,30+Math.random()*(h-70),1+Math.random()*2,6+Math.random()*30); } x.clearRect(0,0,w,8); });
  zt.wrapS=THREE.RepeatWrapping; const zm=new THREE.MeshStandardMaterial({map:zt,roughness:0.6,metalness:0,alphaTest:0.5,polygonOffset:true,polygonOffsetFactor:-2});
  const faces=[]; for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++){ if('_z'.indexOf(MAP[y][x])<0)continue; for(const d of [[1,0],[-1,0],[0,1],[0,-1]]){ const n=(MAP[y+d[1]]||'')[x+d[0]]; if(n==='W'||n==='#')faces.push([x,y,d[0],d[1]]); } }
  const im=new THREE.InstancedMesh(new THREE.PlaneGeometry(T,1.25),zm,faces.length), o=new THREE.Object3D(); faces.forEach((f,i)=>{ o.position.set(f[0]*T+T/2+f[2]*(T/2-0.012),0.625,f[1]*T+T/2+f[3]*(T/2-0.012)); o.rotation.set(0,Math.atan2(-f[2],-f[3]),0); o.updateMatrix(); im.setMatrixAt(i,o.matrix); }); im.receiveShadow=true; im.frustumCulled=false; scene.add(im);
  // carteles: uno de cada cinco paños de pared, lejos de puertas y sin mueble alto delante; el tipo sale de la casilla, así que siempre están en el mismo sitio
  const hh=(a,b,c)=>{ const v=Math.sin(a*127.1+b*311.7+c*74.7)*43758.5453; return v-Math.floor(v); }; let cnt=0;
  faces.forEach(f=>{ const [x,y,dx,dy]=f; if(hh(x,y,dx*2+dy)>0.24)return; for(const d of [[1,0],[-1,0],[0,1],[0,-1],[0,0]]){ const n=(MAP[y+d[1]]||'')[x+d[0]]; if('DLVdb'.indexOf(n)>=0)return; } const px=x*T+T/2+dx*(T/2-0.02), pz=y*T+T/2+dy*(T/2-0.02); if(gObst(px-dx*0.35,pz-dy*0.35))return;
    const k=Math.floor(hh(x,y,7)*5), m=new THREE.Mesh(new THREE.PlaneGeometry(SZ[k][0],SZ[k][1]),mats[k]); m.position.set(px,k===4?2.45:1.95,pz); m.rotation.y=Math.atan2(-dx,-dy); m.rotation.z=(hh(x,y,3)-0.5)*0.03; m.receiveShadow=true; scene.add(m); cnt++; });
  // pantalla de chapa sobre cada bombilla
  const sm=new THREE.MeshStandardMaterial({color:0x2c3a2e,roughness:0.5,metalness:0.6,side:THREE.DoubleSide}); LIT.forEach(s=>{ if(s.R!==7.5)return; const c=new THREE.Mesh(new THREE.ConeGeometry(0.24,0.16,18,1,true),sm); c.position.set(s.x,s.y+0.1,s.z); scene.add(c); });
  if(renderer.initTexture)T_.concat([zt]).forEach(t=>{ try{ renderer.initTexture(t); }catch(e){} });   // subir las texturas ya, no al entrar en la habitación
  stats.deco=cnt; }
// ---------- patio vestido, todo dibujado en lienzos y en mallas instanciadas (pocas llamadas de dibujo): hierbajos al pie de los muros, manchas y grietas, tapas de alcantarilla con vapor y hojas que arrastra el viento
const STEAM=[];
function patio(){ const hh=(a,b,c)=>{ const v=Math.sin(a*127.1+b*311.7+c*74.7)*43758.5453; return v-Math.floor(v); }, out=(x,y)=>'.sl'.indexOf((MAP[y]||'')[x]||'#')>=0, o=new THREE.Object3D();
  const cv=(w,h,fn)=>{ const c=document.createElement('canvas'); c.width=w; c.height=h; const x=c.getContext('2d'); fn(x,w,h); const t=new THREE.CanvasTexture(c); t.encoding=THREE.sRGBEncoding; t.anisotropy=4; if(renderer.initTexture)try{ renderer.initTexture(t); }catch(e){} return t; };
  // hierbajos: mata de briznas en dos planos cruzados
  const gt=cv(128,128,(x,w,h)=>{ for(let i=0;i<46;i++){ const bx=14+Math.random()*(w-28), ht=30+Math.random()*86, lean=(Math.random()-0.5)*46, g=60+Math.random()*60|0; x.strokeStyle='rgb('+(g*0.62|0)+','+g+','+(g*0.35|0)+')'; x.lineWidth=1.5+Math.random()*2.2; x.beginPath(); x.moveTo(bx,h); x.quadraticCurveTo(bx+lean*0.3,h-ht*0.6,bx+lean,h-ht); x.stroke(); } for(let i=0;i<5;i++){ x.fillStyle='rgb(150,140,70)'; x.fillRect(20+Math.random()*88,20+Math.random()*50,3,3); } });
  const gg=new THREE.BufferGeometry(), P_=[],U_=[],N_=[],I_=[]; [0,Math.PI/2].forEach((a,k)=>{ const c=Math.cos(a)*0.5, sn=Math.sin(a)*0.5; P_.push(-c,0,-sn, c,0,sn, c,1,sn, -c,1,-sn); U_.push(0,0,1,0,1,1,0,1); for(let i=0;i<4;i++)N_.push(0,1,0); I_.push(k*4,k*4+1,k*4+2,k*4,k*4+2,k*4+3); });
  gg.setAttribute('position',new THREE.Float32BufferAttribute(P_,3)); gg.setAttribute('uv',new THREE.Float32BufferAttribute(U_,2)); gg.setAttribute('normal',new THREE.Float32BufferAttribute(N_,3)); gg.setIndex(I_);
  const spots=[]; for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++){ if(!out(x,y))continue; for(const d of [[1,0],[-1,0],[0,1],[0,-1]]){ const n=(MAP[y+d[1]]||'')[x+d[0]]; if(n!=='W'&&n!=='#')continue; const k=Math.floor(hh(x,y,d[0]*3+d[1])*4); for(let i=0;i<k;i++){ const u=hh(x,y,i*7+d[0])-0.5, px=x*T+T/2+d[0]*(T/2-0.12-hh(x,i,2)*0.2)+(d[0]?0:u*T), pz=y*T+T/2+d[1]*(T/2-0.12-hh(y,i,3)*0.2)+(d[1]?0:u*T); spots.push([px,pz,0.28+hh(x+i,y,5)*0.42]); } }
    if(hh(x,y,31)<0.1)for(let i=0;i<3;i++)spots.push([x*T+hh(x,y,40+i)*T,y*T+hh(x,y,50+i)*T,0.16+hh(x,y,60+i)*0.2]); }
  const gm=new THREE.MeshStandardMaterial({map:gt,alphaTest:0.4,side:THREE.DoubleSide,roughness:0.9,metalness:0,color:0x6f7a62}), gi=new THREE.InstancedMesh(gg,gm,spots.length); spots.forEach((q,i)=>{ o.position.set(q[0],0,q[1]); o.rotation.set(0,hh(q[0],q[1],1)*3,0); o.scale.set(q[2]*1.5,q[2],q[2]*1.5); o.updateMatrix(); gi.setMatrixAt(i,o.matrix); }); gi.frustumCulled=false; gi.receiveShadow=true; scene.add(gi);
  // manchas, grietas y rodadas: calcomanías planas sobre el asfalto
  const blob=(x,w,h,col,n)=>{ for(let i=0;i<n;i++){ const r=10+Math.random()*44, g=x.createRadialGradient(0,0,0,0,0,r); g.addColorStop(0,col); g.addColorStop(1,'rgba(0,0,0,0)'); x.save(); x.translate(w/2+(Math.random()-0.5)*w*0.5,h/2+(Math.random()-0.5)*h*0.5); x.scale(1,0.5+Math.random()*0.8); x.fillStyle=g; x.beginPath(); x.arc(0,0,r,0,6.3); x.fill(); x.restore(); } };
  const DT=[cv(256,256,(x,w,h)=>{ blob(x,w,h,'rgba(6,5,4,0.85)',14); }),
    cv(256,256,(x,w,h)=>{ x.strokeStyle='rgba(8,7,6,0.9)'; for(let k=0;k<3;k++){ let px=30+Math.random()*40, py=30+Math.random()*190; x.lineWidth=2.4; x.beginPath(); x.moveTo(px,py); for(let i=0;i<14;i++){ px+=10+Math.random()*10; py+=(Math.random()-0.5)*26; x.lineTo(px,py); if(i%5===2){ x.lineTo(px+12,py+(Math.random()-0.5)*50); x.moveTo(px,py); } } x.stroke(); } }),
    cv(128,512,(x,w,h)=>{ for(const u of [22,86]){ for(let i=0;i<h;i+=7){ x.fillStyle='rgba(8,7,6,'+(0.25+Math.random()*0.4)+')'; x.fillRect(u+Math.sin(i*0.02)*4,i,20,4); } } const g=x.createLinearGradient(0,0,0,h); g.addColorStop(0,'rgba(0,0,0,1)'); g.addColorStop(0.2,'rgba(0,0,0,0)'); g.addColorStop(0.8,'rgba(0,0,0,0)'); g.addColorStop(1,'rgba(0,0,0,1)'); x.globalCompositeOperation='destination-out'; x.fillStyle=g; x.fillRect(0,0,w,h); }),
    cv(128,128,(x,w,h)=>{ x.fillStyle='#1b1a18'; x.beginPath(); x.arc(64,64,62,0,6.3); x.fill(); x.fillStyle='#3a3833'; x.beginPath(); x.arc(64,64,54,0,6.3); x.fill(); x.strokeStyle='#161514'; x.lineWidth=5; for(let i=-3;i<=3;i++){ x.beginPath(); x.moveTo(64+i*15,18); x.lineTo(64+i*15,110); x.stroke(); } x.lineWidth=3; x.beginPath(); x.arc(64,64,40,0,6.3); x.stroke(); })];
  const DS=[[2.6,2.6],[3.2,3.2],[1.7,6.5],[0.9,0.9]], lists=[[],[],[],[]];
  for(let y=1;y<ROWS-1;y++)for(let x=1;x<COLS-1;x++){ if(!out(x,y))continue; const r=hh(x,y,90); if(r<0.1)lists[0].push([x,y]); else if(r<0.2)lists[1].push([x,y]); else if(r<0.235&&out(x,y+1)&&out(x,y-1))lists[2].push([x,y]); }
  // alcantarillas: pocas, en casillas despejadas y separadas entre sí
  for(let y=2;y<ROWS-2&&lists[3].length<5;y++)for(let x=2;x<COLS-2;x++){ if(hh(x,y,123)>0.035)continue; let ok=true; for(let a=-1;a<=1;a++)for(let b=-1;b<=1;b++)if(MAP[y+b][x+a]!=='.')ok=false; if(ok&&lists[3].every(q=>Math.abs(q[0]-x)+Math.abs(q[1]-y)>9))lists[3].push([x,y]); }
  lists.forEach((L,k)=>{ if(!L.length)return; const m=new THREE.MeshStandardMaterial({map:DT[k],transparent:true,depthWrite:false,roughness:k===0?0.12:0.8,metalness:k===3?0.5:0,polygonOffset:true,polygonOffsetFactor:-3,polygonOffsetUnits:-3}), g=new THREE.PlaneGeometry(DS[k][0],DS[k][1]); g.rotateX(-Math.PI/2); const im=new THREE.InstancedMesh(g,m,L.length);
    L.forEach((q,i)=>{ o.position.set(q[0]*T+T/2+(k===3?0:(hh(q[0],q[1],4)-0.5)),0.02+k*0.004,q[1]*T+T/2+(k===3?0:(hh(q[0],q[1],6)-0.5))); o.rotation.set(0,k===2?(hh(q[0],q[1],8)-0.5)*0.2:hh(q[0],q[1],8)*6.28,0); o.scale.set(1,1,1); o.updateMatrix(); im.setMatrixAt(i,o.matrix); }); im.frustumCulled=false; im.receiveShadow=true; im.renderOrder=1; scene.add(im); });
  // vapor: unas pocas volutas por alcantarilla y junto al generador, que suben, se ensanchan y se deshacen
  const st=cv(64,64,(x,w,h)=>{ const g=x.createRadialGradient(32,32,2,32,32,31); g.addColorStop(0,'rgba(255,255,255,0.55)'); g.addColorStop(0.5,'rgba(255,255,255,0.2)'); g.addColorStop(1,'rgba(255,255,255,0)'); x.fillStyle=g; x.fillRect(0,0,w,h); });
  const src=lists[3].map(q=>[q[0]*T+T/2,q[1]*T+T/2]); for(let y=0;y<ROWS;y++){ const i=MAP[y].indexOf('g'); if(i>=0)src.push([i*T+T/2+0.9,y*T+T/2+0.6]); }
  src.forEach((q,k)=>{ for(let i=0;i<5;i++){ const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:st,color:0xb9b2a6,transparent:true,depthWrite:false,opacity:0})); sp.position.set(q[0],0.1,q[1]); scene.add(sp); STEAM.push({sp,x:q[0],z:q[1],ph:i/5+k*0.13}); } });
  // hojas y papeles: puntos que el viento arrastra a ras de suelo alrededor de la cámara
  const NL=LOW?40:90, lp=new Float32Array(NL*3), ls=new Float32Array(NL); for(let i=0;i<NL;i++){ lp[i*3]=Math.random()*40; lp[i*3+1]=Math.random(); lp[i*3+2]=Math.random()*40; ls[i]=Math.random(); }
  const lg=new THREE.BufferGeometry(); lg.setAttribute('position',new THREE.BufferAttribute(lp,3)); lg.setAttribute('seed',new THREE.BufferAttribute(ls,1));
  const lm=new THREE.ShaderMaterial({transparent:true,depthWrite:false,uniforms:{time:RIP,cam:{value:new THREE.Vector3()},fogD:{value:0.034}},
    vertexShader:'uniform float time; uniform vec3 cam; attribute float seed; varying float vS; varying float vD; void main(){ vS=seed; float sp=1.6+seed*2.4; vec3 p=position; p.x=mod(p.x+time*sp+sin(time*0.7+seed*30.0)*1.5-cam.x,40.0)-20.0+cam.x; p.z=mod(p.z+time*sp*0.35+cos(time*0.5+seed*17.0)*1.2-cam.z,40.0)-20.0+cam.z; float gust=max(0.0,sin(time*0.6+seed*12.0)); p.y=0.04+gust*gust*(0.25+seed*0.9)*abs(sin(time*2.0+seed*40.0)); vec4 mv=modelViewMatrix*vec4(p,1.0); vD=-mv.z; gl_Position=projectionMatrix*mv; gl_PointSize=min(26.0,(2.6+seed*3.2)*(22.0/max(2.0,vD))); }',
    fragmentShader:'uniform float time; uniform float fogD; varying float vS; varying float vD; void main(){ vec2 c=gl_PointCoord-0.5; float a=time*(2.0+vS*5.0)+vS*20.0; c=mat2(cos(a),-sin(a),sin(a),cos(a))*c; if(abs(c.x)>0.45||abs(c.y)>0.16+0.2*step(0.85,vS))discard; vec3 col=vS>0.85?vec3(0.34,0.32,0.27):mix(vec3(0.16,0.1,0.04),vec3(0.3,0.2,0.07),fract(vS*7.0)); float f=exp(-fogD*fogD*vD*vD); gl_FragColor=vec4(col*0.55*f,f*0.95); }'});
  const pts=new THREE.Points(lg,lm); pts.frustumCulled=false; scene.add(pts); STEAM.leaf=lm; stats.patio=spots.length; }
function patioTick(dt,t){ if(STEAM.leaf)STEAM.leaf.uniforms.cam.value.copy(camera.position); for(const s of STEAM){ const k=(t*0.16+s.ph)%1, sc=0.5+k*2.4; s.sp.position.set(s.x+Math.sin(t*0.5+s.ph*9)*0.25*k+k*0.7,0.15+k*3.0,s.z+k*0.25); s.sp.scale.set(sc,sc,1); s.sp.material.opacity=Math.sin(Math.min(1,k*1.3)*Math.PI)*0.2; } }
let composer=null, bloom=null, useBloom=!LOW;
// El compositor trabaja en lineal y con margen (medio flotante); la última pasada hace el revelado: exposición, curva ACES, viñeta y grano.
const FINAL={uniforms:{tDiffuse:{value:null},exposure:{value:0.8},time:{value:0},tS:{value:new THREE.Vector3(1,1,1)},tH:{value:new THREE.Vector3(1,1,1)},sat:{value:1},con:{value:1}},vertexShader:'varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
  fragmentShader:`uniform sampler2D tDiffuse; uniform float exposure; uniform float time; uniform vec3 tS; uniform vec3 tH; uniform float sat; uniform float con; varying vec2 vUv;
vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.0,1.0); }
void main(){ vec2 o=(vUv-0.5); float r2=dot(o,o); vec2 k=o*r2*0.012; vec3 c=vec3(texture2D(tDiffuse,vUv+k).r,texture2D(tDiffuse,vUv).g,texture2D(tDiffuse,vUv-k).b)*exposure; c=aces(c); c=pow(c,vec3(1.0/2.2));
  { float l=dot(c,vec3(0.299,0.587,0.114)); c=mix(vec3(l),c,sat); c*=mix(tS,tH,smoothstep(0.05,0.75,l)); c=(c-0.5)*con+0.5; }   /* paleta: saturación, tinte de sombras y de luces, contraste */
  float d=distance(vUv,vec2(0.5)); c*=1.0-0.55*smoothstep(0.35,0.95,d);
  float g=fract(sin(dot(vUv*vec2(1920.0,1080.0)+time*60.0,vec2(12.9898,78.233)))*43758.5453); c+=(g-0.5)*0.022; gl_FragColor=vec4(c,1.0); }`};
let finalPass=null;
// paletas (tecla P): no cambian la escena, solo el revelado final, así que el cambio es instantáneo y no cuesta rendimiento
const PALS=[['TARSIS',[1,1,1],[1,1,1],1,1],['NOCHE FRÍA',[0.78,0.98,1.12],[1.08,1.0,0.9],1.08,1.06],['SODIO',[1.05,0.95,0.82],[1.1,0.98,0.8],0.8,1.04],['ACERO',[0.88,0.96,1.08],[0.98,1.0,1.04],0.5,1.1],['VERDE TÁCTICO',[0.8,1.06,0.86],[0.94,1.08,0.9],0.55,1.08],['CINE NEGRO',[0.97,0.99,1.03],[1.03,1.0,0.96],0.04,1.18],['TECHNICOLOR',[0.95,0.95,1.05],[1.05,1.0,0.95],1.45,1.1]];
let palI=0; try{ palI=(+localStorage.getItem('lh-paleta')||0)%PALS.length; }catch(e){}
function setPal(i,quiet){ palI=((i%PALS.length)+PALS.length)%PALS.length; const q=PALS[palI]; if(finalPass){ const u=finalPass.uniforms; u.tS.value.fromArray(q[1]); u.tH.value.fromArray(q[2]); u.sat.value=q[3]; u.con.value=q[4]; } try{ localStorage.setItem('lh-paleta',palI); }catch(e){} if(!quiet){ ALERT.info=true; ALERT.msg='PALETA: '+q[0]; ALERT.msgT=1.8; const m=el('aviso'); if(m&&el('estado').hidden){ m.textContent=ALERT.msg; m.className='ok'; clearTimeout(setPal.t); setPal.t=setTimeout(()=>{ if(el('estado').hidden)m.textContent=''; },1800); } } }
addEventListener('keydown',e=>{ if(e.code==='KeyP')setPal(palI+(e.shiftKey?-1:1)); });
function mkComposer(){ const pr=renderer.getPixelRatio(); const rt=new THREE.WebGLRenderTarget(innerWidth*pr,innerHeight*pr,{type:THREE.HalfFloatType,minFilter:THREE.LinearFilter,magFilter:THREE.LinearFilter,format:THREE.RGBAFormat});
  composer=new THREE.EffectComposer(renderer,rt); composer.addPass(new THREE.RenderPass(scene,camera)); bloom=new THREE.UnrealBloomPass(new THREE.Vector2(innerWidth,innerHeight),0.7,0.8,1.0); composer.addPass(bloom);
  finalPass=new THREE.ShaderPass(FINAL); composer.addPass(finalPass); }
if(THREE.EffectComposer&&THREE.UnrealBloomPass)mkComposer(); else useBloom=false; setPal(palI,true);

// ---------- recorrido a pie: WASD y ratón, con las paredes del plano
const OBST=(INFO.obst||[]).filter(o=>o[3]>0.15&&o[4]>0.15); deco(); patio();
const solid=(x,y)=>{ if(x<0||y<0||x>=COLS||y>=ROWS)return true; return '#WLVb'.indexOf(MAP[y][x])>=0; };   // cajas, camiones y generador ya no tapan la casilla entera: chocan con su huella real (OBST)
const P={x:0,z:0,yaw:0,pitch:0,vy:0,bob:0}; (function(){ let sx=2,sy=2; MAP.forEach((r,y)=>{ const i=r.indexOf('P'); if(i>=0){ sx=i; sy=y; } }); P.x=sx*T+T/2; P.z=sy*T+T/2; P.yaw=-2.2; })();
const keys={}; addEventListener('keydown',e=>{ keys[e.code]=true; if(e.code==='KeyB'&&composer){ useBloom=!useBloom; } if(e.code==='KeyH'){ el('hud').hidden=!el('hud').hidden; }
  if(e.code==='KeyF')scene.fog.density=Math.max(0.004,scene.fog.density-0.003); if(e.code==='KeyG')scene.fog.density=Math.min(0.09,scene.fog.density+0.003);
  if(finalPass){ const u=finalPass.uniforms.exposure; if(e.code==='KeyJ')u.value=Math.max(0.3,u.value-0.05); if(e.code==='KeyK')u.value=Math.min(2,u.value+0.05); } }); addEventListener('keyup',e=>{ keys[e.code]=false; });
let locked=false; const cv=renderer.domElement;
el('intro').addEventListener('click',()=>{ if(!ready)return; sRain(); if(cv.requestPointerLock)cv.requestPointerLock(); el('intro').hidden=true; locked=true; if(PL.p&&!MS.intro&&msStep()===0&&!MS.done)startStory(); });
document.addEventListener('pointerlockchange',()=>{ locked=document.pointerLockElement===cv; if(!locked&&!TOUCH){ el('intro').hidden=false; } });
addEventListener('mousemove',e=>{ if(document.pointerLockElement!==cv)return; const k=0.0022*(1-0.45*PL.aim); P.yaw-=e.movementX*k; P.pitch=Math.max(-1.3,Math.min(1.3,P.pitch-e.movementY*k)); });
// táctil: arrastrar la mitad derecha gira, la izquierda camina
const TOUCH='ontouchstart' in window; const touch={mx:0,mz:0,ids:{}};
if(TOUCH){ cv.addEventListener('touchstart',e=>{ for(const t of e.changedTouches)touch.ids[t.identifier]={x:t.clientX,y:t.clientY,left:t.clientX<innerWidth/2,ox:t.clientX,oy:t.clientY}; e.preventDefault(); },{passive:false});
  cv.addEventListener('touchmove',e=>{ for(const t of e.changedTouches){ const s=touch.ids[t.identifier]; if(!s)continue; if(s.left){ touch.mx=Math.max(-1,Math.min(1,(t.clientX-s.ox)/60)); touch.mz=Math.max(-1,Math.min(1,(t.clientY-s.oy)/60)); } else { P.yaw-=(t.clientX-s.x)*0.005; P.pitch=Math.max(-1.3,Math.min(1.3,P.pitch-(t.clientY-s.y)*0.005)); } s.x=t.clientX; s.y=t.clientY; } e.preventDefault(); },{passive:false});
  const end=e=>{ for(const t of e.changedTouches){ const s=touch.ids[t.identifier]; if(s&&s.left){ touch.mx=0; touch.mz=0; } delete touch.ids[t.identifier]; } }; cv.addEventListener('touchend',end); cv.addEventListener('touchcancel',end); }
// Con Cuttlas cargado se le maneja en tercera persona (V alterna con la cámara libre): C se agacha o se levanta, Mayús aprieta el paso.
const PL={hp:100,mag:8,res:16,rel:0,drag:null,p:null,third:false,crouch:false,act:'idle',yaw:0,dist:3.0,aim:0,aiming:false,eye:1.66};
// Primera persona: la pistola con silenciador a la vista; el botón derecho la sube a la línea de mira y cierra el campo.
const VM=new THREE.Group(); (function(){ scene.add(camera); camera.add(VM);
  // materiales con luz propia (matcap): el foco de la torreta no debe quemar el arma a un palmo de la cámara
  const mc=document.createElement('canvas'); mc.width=mc.height=64; const mx=mc.getContext('2d'), gr=mx.createRadialGradient(24,20,2,32,32,34); gr.addColorStop(0,'#fff'); gr.addColorStop(0.25,'#9a9a9a'); gr.addColorStop(0.7,'#4a4a4a'); gr.addColorStop(1,'#1c1c1c'); mx.fillStyle=gr; mx.fillRect(0,0,64,64);
  const mct=new THREE.CanvasTexture(mc), cap=c=>new THREE.MeshMatcapMaterial({color:c,matcap:mct,fog:false});
  const mG=cap(0x3a3d45), mS=cap(0x202226), mH=cap(0x3f2c20), mT=cap(0x262b21);   // acero, polímero, guante de cuero, manga
  const add=(g,m,x,y,z,rx)=>{ const o=new THREE.Mesh(g,m); o.position.set(x,y,z); if(rx)o.rotation.x=rx; o.frustumCulled=false; VM.add(o); return o; }, B=(w,h,d)=>new THREE.BoxGeometry(w,h,d);
  // perfil lateral (x hacia delante, y arriba) extruido a lo ancho y con canto redondeado
  const ext=(pts,w,bev)=>{ const sh=new THREE.Shape(); pts.forEach((q,k)=>k?sh.lineTo(q[0],q[1]):sh.moveTo(q[0],q[1])); sh.closePath(); const g=new THREE.ExtrudeGeometry(sh,{depth:w-2*bev,bevelEnabled:true,bevelSize:bev,bevelThickness:bev,bevelSegments:3,curveSegments:4}); g.translate(0,0,-(w-2*bev)/2); g.rotateY(Math.PI/2); return g; };
  const fing=(r,len,m,x,y,z,rx,rz)=>{ const g=new THREE.Group(); const c=new THREE.Mesh(new THREE.CylinderGeometry(r,r,len,10),m); g.add(c); for(const sg of [-1,1]){ const e=new THREE.Mesh(new THREE.SphereGeometry(r,10,8),m); e.position.y=sg*len/2; g.add(e); } g.traverse(o=>{ o.frustumCulled=false; }); g.position.set(x,y,z); g.rotation.set(rx||0,0,rz||0); VM.add(g); return g; };
  add(ext([[0.004,-0.016],[0.2,-0.016],[0.203,-0.008],[0.203,0.01],[0.196,0.017],[0.012,0.017],[0.002,0.008]],0.027,0.003),mG,0,0,0);            // corredera
  add(ext([[0.012,-0.036],[0.168,-0.036],[0.176,-0.016],[0.006,-0.016]],0.025,0.003),mS,0,0,0);                                                  // armazón
  add(ext([[0.004,-0.03],[0.05,-0.03],[0.036,-0.128],[-0.018,-0.122]],0.029,0.005),mS,0,0,0);                                                     // empuñadura
  const tg=add(new THREE.TorusGeometry(0.019,0.003,6,14,Math.PI),mG,0,-0.036,-0.078); tg.rotation.set(Math.PI,Math.PI/2,0);                          // guardamonte
  add(B(0.005,0.02,0.006),mG,0,-0.044,-0.07,0.3);                                                                                                    // gatillo
  add(new THREE.CylinderGeometry(0.0172,0.0172,0.17,20),mS,0,0.001,-0.288,Math.PI/2); add(new THREE.CylinderGeometry(0.0182,0.0182,0.012,20),mG,0,0.001,-0.21,Math.PI/2); add(new THREE.CylinderGeometry(0.0182,0.0165,0.01,20),mG,0,0.001,-0.376,Math.PI/2);
  add(B(0.005,0.007,0.007),mG,0.008,0.0205,-0.012); add(B(0.005,0.007,0.007),mG,-0.008,0.0205,-0.012); add(B(0.0035,0.007,0.007),mG,0,0.0205,-0.194);   // alza y punto de mira
  for(let k=0;k<6;k++)add(B(0.0285,0.02,0.0025),mS,0,0.002,-0.022-k*0.006);                                                                           // estrías de la corredera
  // mano enguantada: palma tras la empuñadura, tres dedos que la abrazan, índice al gatillo y pulgar por el costado
  add(ext([[-0.034,-0.04],[0.01,-0.032],[0.004,-0.128],[-0.042,-0.124]],0.062,0.014),mH,0,0,0);   // dorso y palma
  for(let k=0;k<3;k++)fing(0.0105,0.036,mH,0.0,-0.066-k*0.021,-0.052+k*0.004,0,Math.PI/2);
  fing(0.0095,0.05,mH,0.021,-0.04,-0.045,Math.PI/2+0.15,0); fing(0.0088,0.042,mH,-0.0205,-0.022,-0.02,Math.PI/2-0.1,0);
  const fa=add(new THREE.CylinderGeometry(0.027,0.038,0.42,14),mT,0,0,0); const a=new THREE.Vector3(0.004,-0.1,0.028), b=new THREE.Vector3(0.11,-0.3,0.42); fa.position.copy(a).add(b).multiplyScalar(0.5); fa.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),a.clone().sub(b).normalize());
  // mano de apoyo: la izquierda envuelve a la derecha por delante de la empuñadura, pulgar adelantado bajo la corredera
  add(ext([[0.052,-0.05],[0.062,-0.118],[-0.01,-0.13],[-0.016,-0.058]],0.026,0.01),mH,-0.027,0,0);
  for(let k=0;k<4;k++)fing(0.0105,0.05,mH,-0.004,-0.058-k*0.0205,-0.071+k*0.005,0,Math.PI/2);
  fing(0.0095,0.055,mH,-0.024,-0.03,-0.07,Math.PI/2-0.12,0);
  { const f2=add(new THREE.CylinderGeometry(0.027,0.038,0.44,14),mT,0,0,0), a2=new THREE.Vector3(-0.03,-0.105,0.0), b2=new THREE.Vector3(-0.27,-0.3,0.3); f2.position.copy(a2).add(b2).multiplyScalar(0.5); f2.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),a2.clone().sub(b2).normalize()); }
  VM.visible=false; })();
renderer.domElement.addEventListener('contextmenu',e=>e.preventDefault());
addEventListener('mousedown',e=>{ if(e.button===2)PL.aiming=true; }); addEventListener('mouseup',e=>{ if(e.button===2)PL.aiming=false; });

// Disparo: un tiro con silenciador por clic izquierdo. El rayo sale del centro de la vista; se oye a pocos metros y el impacto también hace ruido donde da.
const FX={flash:null,hits:[],ac:null}; (function(){ const m=new THREE.MeshBasicMaterial({color:0xffc27a,transparent:true,opacity:0.5,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide,fog:false}); const g=new THREE.Group();
  for(let i=0;i<3;i++){ const q=new THREE.Mesh(new THREE.PlaneGeometry(0.036,0.036),m); q.rotation.z=i*Math.PI/3; q.frustumCulled=false; g.add(q); } g.position.set(0,0.002,-0.385); g.visible=false; VM.add(g); FX.flash=g;
  const hm=new THREE.MeshBasicMaterial({color:0xffe2b0,fog:false}); for(let i=0;i<4;i++){ const h=new THREE.Mesh(new THREE.SphereGeometry(0.035,6,5),hm); h.visible=false; scene.add(h); FX.hits.push({m:h,t:0}); } })();
function pfft(){ try{ const AC=window.AudioContext||window.webkitAudioContext; if(!AC)return; const ac=FX.ac||(FX.ac=new AC()); const n=Math.floor(ac.sampleRate*0.16), buf=ac.createBuffer(1,n,ac.sampleRate), d=buf.getChannelData(0); for(let i=0;i<n;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/n,3);
    const src=ac.createBufferSource(); src.buffer=buf; const f=ac.createBiquadFilter(); f.type='bandpass'; f.frequency.value=1500; f.Q.value=0.7; const g=ac.createGain(); g.gain.value=0.5; src.connect(f); f.connect(g); g.connect(ac.destination); src.start(); }catch(e){} }
// distracción: Q lanza un casquillo hacia donde miras; el ruido cae allí, no donde estás
function toss(){ if(!PL.p||ALERT.caught||PL.drag||(PL.tossT||0)>0)return null; PL.tossT=1.4; const o=new THREE.Vector3(), d=new THREE.Vector3(); camera.getWorldPosition(o); camera.getWorldDirection(d); d.y=Math.max(d.y,-0.05)+0.12; d.normalize(); let x=o.x, y=o.y, z=o.z, vy=d.y*9;
  for(let k=0;k<160;k++){ const nx=x+d.x*0.12, nz=z+d.z*0.12; vy-=0.03; y+=vy*0.013; const row=MAP[Math.floor(nz/T)], c=row&&row[Math.floor(nx/T)]; if(!c||'#WTLVb'.indexOf(c)>=0||('cg'.indexOf(c)>=0&&y<1.25))break; x=nx; z=nz; if(y<=0.05||Math.hypot(x-o.x,z-o.z)>15)break; }
  setTimeout(()=>{ NOISES.push({x,z,r:9}); PL.ping={x,z,t:1.2}; click(2400,0.05); click(3100,0.03); const h=FX.hits[0]; h.m.position.set(x,0.05,z); h.m.visible=true; h.t=0.14; },450); return [x,z]; }
addEventListener('keydown',e=>{ if(e.code==='KeyQ')toss(); });
function reload(){ if(!PL.p||PL.rel>0||PL.mag>=8||PL.res<=0||PL.drag)return; PL.rel=1.5; click(900,0.04); }
function click(f,g){ try{ const AC=window.AudioContext||window.webkitAudioContext; if(!AC)return; const ac=FX.ac||(FX.ac=new AC()), o=ac.createOscillator(), v=ac.createGain(); o.type='square'; o.frequency.value=f; v.gain.setValueAtTime(g,ac.currentTime); v.gain.exponentialRampToValueAtTime(0.0001,ac.currentTime+0.05); o.connect(v); v.connect(ac.destination); o.start(); o.stop(ac.currentTime+0.06); }catch(e){} }
function shoot(){ if(!PL.p||ALERT.caught||PL.cd>0||PL.rel>0||PL.drag)return null; if(PL.mag<=0){ PL.cd=0.3; click(1400,0.05); if(PL.res>0)reload(); return 'vacío'; } PL.mag--; PL.cd=0.42; PL.kick=1; PL.flashT=0.045; FX.flash.rotation.z=Math.random()*3; pfft(); PL.shots=(PL.shots||0)+1;
  const o=new THREE.Vector3(), d=new THREE.Vector3(); camera.getWorldPosition(o); camera.getWorldDirection(d); NOISES.push({x:P.x,z:P.z,r:4.5}); let hit=null, who=null;
  for(let s=0.3;s<60&&!hit;s+=0.08){ const x=o.x+d.x*s, y=o.y+d.y*s, z=o.z+d.z*s; if(y<=0.02){ hit=[x,0.03,z]; break; } if(y>7)break;
    if(y>1.9){ const lp=LIT.find(q=>q.on&&Math.abs(q.x-x)<0.4&&Math.abs(q.z-z)<0.4&&Math.abs(q.y-y)<0.45); if(lp){ lampOff(lp); hit=[x,y,z]; break; } }
    for(const p of PEOPLE){ if(p===PL.p||p.dead||p.q.npc||p.q.name==='roig')continue; const r=p.root.position; if(y<1.86&&Math.hypot(x-r.x,z-r.z)<(y>1.5?0.17:0.3)){ who=p; hit=[x,y,z]; break; } }
    if(!hit)for(const dg of DOGS){ if(dg.dead)continue; const r=dg.root.position; if(y<0.95&&Math.hypot(x-r.x,z-r.z)<0.42){ dogDown(dg); hit=[x,y,z]; break; } }
    if(hit)break; const row=MAP[Math.floor(z/T)], c=row&&row[Math.floor(x/T)]; if(!c||'#WTLVb'.indexOf(c)>=0||('cg'.indexOf(c)>=0&&y<1.25))hit=[x-d.x*0.1,y-d.y*0.1,z-d.z*0.1]; }
  if(hit){ const h=FX.hits[PL.shots%FX.hits.length]; h.m.position.set(hit[0],hit[1],hit[2]); h.m.visible=true; h.t=0.14; }
  if(who){ MS.kill=(MS.kill||0)+1; who.dead=true; who.found=false; who.path=null; if(who.acts.down){ const a=who.acts[who.act], b=who.acts.down; b.reset(); b.play(); if(a)a.crossFadeTo(b,0.12,false); who.act='down'; } NOISES.push({x:hit[0],z:hit[2],r:5}); }
  else if(hit)NOISES.push({x:hit[0],z:hit[2],r:6});
  return who?who.q.name:(hit?'impacto':null); }
function bodyC(o){ const r=o.root.position; return [r.x-Math.sin(o.yaw)*0.95,r.z-Math.cos(o.yaw)*0.95]; }   // centro del cuerpo tendido: cae de espaldas, la cabeza queda detrás de los pies
function nearBody(){ let best=null, bd=1.9; PEOPLE.forEach(o=>{ if(!o.dead)return; const c=bodyC(o), d=Math.min(Math.hypot(c[0]-P.x,c[1]-P.z),Math.hypot(o.root.position.x-P.x,o.root.position.z-P.z)); if(d<bd){ bd=d; best=o; } }); return best; }
function coverAt(x,z){ const tx=Math.floor(x/T), ty=Math.floor(z/T); for(const d of [[1,0],[-1,0],[0,1],[0,-1]]){ const c=(MAP[ty+d[1]]||'')[tx+d[0]]; if(c&&'cgT'.indexOf(c)>=0)return true; } return false; }
// ---------- misión: llave de Ibarra, despacho, clave, archivo, expediente LH-07 y salida por la verja
const MS={key:false,door:false,code:false,vault:false,file:false,done:0}, DOORS={}, PTS={};
(function(){ for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++){ const c=MAP[y][x]; if(c==='L'||c==='V'){ const horiz='W#'.indexOf(MAP[y][x-1])>=0&&'W#'.indexOf(MAP[y][x+1])>=0, piv=new THREE.Group(), cx=x*T+T/2, cz=y*T+T/2;
      const leaf=new THREE.Mesh(horiz?new THREE.BoxGeometry(1.3,2.2,0.07):new THREE.BoxGeometry(0.07,2.2,1.3),M.hierro), knob=new THREE.Mesh(new THREE.BoxGeometry(0.12,0.2,0.12),M.oscuro||M.hierro);
      if(horiz){ piv.position.set(cx-0.65,0,cz); leaf.position.set(0.65,1.1,0); knob.position.set(1.1,1.05,0); } else { piv.position.set(cx,0,cz-0.65); leaf.position.set(0,1.1,0.65); knob.position.set(0,1.05,1.1); }
      leaf.castShadow=leaf.receiveShadow=true; piv.add(leaf); piv.add(knob); scene.add(piv); DOORS[c]={piv,x,y,cx,cz,open:0,want:0}; }
      if(c==='b'){ const piv=new THREE.Group(), cx=x*T+T/2, cz=y*T+T/2; piv.position.set(cx-0.65,0,cz); for(let k=0;k<9;k++){ const b=new THREE.Mesh(new THREE.CylinderGeometry(0.016,0.016,2.2,8),M.hierro); b.position.set(0.05+k*0.15,1.1,0); b.castShadow=true; piv.add(b); } [0.35,1.9].forEach(h=>{ const b=new THREE.Mesh(new THREE.BoxGeometry(1.3,0.05,0.05),M.hierro); b.position.set(0.65,h,0); piv.add(b); }); const lk=new THREE.Mesh(new THREE.BoxGeometry(0.16,0.22,0.09),M.oscuro||M.hierro); lk.position.set(1.15,1.05,0); piv.add(lk); scene.add(piv); DOORS.b={piv,x,y,cx,cz,open:0,want:0}; PTS.bars=[cx,cz+1.2]; PTS.hallo=[cx+1.6,cz+1.6]; PTS.losa=[cx-2.1,cz+1.6]; }
      if(c==='G')PTS.exit=[x*T+T/2,y*T+T/2]; }
  PTS.note=[3*T+T/2,17*T+T/2+0.2]; PTS.file=[9*T+T/2,17*T+T/2]; OBST.push(['peana',PTS.file[0],-PTS.file[1],0.25,0.25,0]);
  const paper=new THREE.Mesh(new THREE.BoxGeometry(0.21,0.004,0.3),new THREE.MeshStandardMaterial({color:0xd8cfb8,roughness:0.9,emissive:0x2a261c})); paper.position.set(PTS.note[0],0.79,PTS.note[1]); paper.rotation.y=0.4; scene.add(paper); MS.paper=paper;
  const folder=new THREE.Mesh(new THREE.BoxGeometry(0.24,0.03,0.33),new THREE.MeshStandardMaterial({color:0x8a2a1e,roughness:0.8,emissive:0x2a0c08})); folder.position.set(PTS.file[0],0.62,PTS.file[1]); folder.rotation.y=-0.3; scene.add(folder); MS.folder=folder;
  const st=new THREE.Mesh(new THREE.BoxGeometry(0.5,0.6,0.5),M.madera||M.hierro); st.position.set(PTS.file[0],0.3,PTS.file[1]); st.castShadow=st.receiveShadow=true; scene.add(st);
  MS.mk=mark('◆','#ffb060'); MS.mk.visible=false; scene.add(MS.mk); })();
function setH(e,h){ if(e._h!==h){ e._h=h; e.innerHTML=h; } }
function say(t,s){ ALERT.msg=t; ALERT.msgT=s||3; ALERT.info=true; }
function openDoor(c){ const d=DOORS[c]; if(!d||d.want)return; d.want=1; MAP[d.y]=MAP[d.y].slice(0,d.x)+'d'+MAP[d.y].slice(d.x+1); click(260,0.06); }
const KP={open:false,buf:'',fails:0,err:0};
function kpTick(dt){ const t=el('tec'); if(!t)return; if(KP.open&&(!near([DOORS.V.cx,DOORS.V.cz],2.4)||ALERT.caught||!locked&&!TOUCH&&!window.__ESC_TEST))KP.open=false; t.hidden=!KP.open; if(!KP.open)return; if(KP.err>0)KP.err-=dt;
  el('tecD').textContent=KP.err>0?'ERROR':(KP.buf+'____').slice(0,4).split('').join(' '); el('tecD').className=KP.err>0?'err':''; el('tecP').textContent=MS.code?'Nota del despacho: «De profundis», salmo 129':'No tienes la clave. Puede que esté en el despacho.'; }
function kpKey(d){ if(!KP.open||KP.err>0)return; if(d==='<'){ KP.buf=KP.buf.slice(0,-1); return; } KP.buf+=d; click(1100+d*40,0.04); if(KP.buf.length<4)return;
  if(KP.buf==='0129'){ KP.open=false; KP.fails=0; MS.vault=true; MS.code=true; openDoor('V'); sTone(880,0.25,0.06,'sine',0.1); titles([['<span>PSALMUS CXXIX</span>DE PROFUNDIS CLAMAVI AD TE',3.2]],()=>doc('ARCHIVO ABIERTO','<p>Ciento veintinueve. Alarcón cuenta como Roma.</p><p>Dentro huele a papel y a gasóleo.</p>',()=>codec(CODEC.vault))); return; }
  { const tr=KP.buf; KP.bad=(KP.bad||0)+1; if(tr==='0130')say('NADA. CIENTO TREINTA ES COMO CUENTAN LOS PROTESTANTES',4); else if(tr==='1983')say('NADA. DEMASIADO FÁCIL PARA UN HOMBRE QUE REZA',4); }
  KP.buf=''; KP.err=0.8; KP.fails++; sTone(180,0.4,0.09,'square'); if(KP.fails>=3){ KP.fails=0; KP.open=false; NOISES.push({x:DOORS.V.cx,z:DOORS.V.cz,r:18}); ALERT.info=false; ALERT.msg='EL TECLADO PITA. TE HAN OÍDO'; ALERT.msgT=3; } }
addEventListener('keydown',e=>{ if(!KP.open)return; const m=/^(?:Digit|Numpad)(\d)$/.exec(e.code); if(m)kpKey(+m[1]); else if(e.code==='Backspace')kpKey('<'); },true);
// ---------- guion de la misión 1 «De profundis», traído del juego original (src/07-codec.js, 10-actions.js, 12-cinematics.js, 13-endings.js): rótulos de entrada, códec con Control y la Fuente, documentos que se leen y final según cómo hayas salido
const DLG={q:null,i:0,n:0,t:0,done:null}, TIT={q:null,i:0,t:0,done:null}, FIN={on:false};
const hold=()=>!!DLG.q||!!TIT.q||FIN.on;
function codec(lines,done){ if(!lines||!lines.length){ if(done)done(); return; } ALERT.msgT=0; DLG.q=lines; DLG.i=0; DLG.done=done||null; PL.aiming=false; el('dlg').hidden=false; [0,0.12,0.24].forEach(a=>sTone(1800,0.06,0.035,'sine',a)); dlgShow(); }
function doc(title,html,done){ codec([{who:title,html,doc:true}],done); }
function dlgShow(){ const L=DLG.q[DLG.i]; DLG.n=L.doc?1e9:0; DLG.t=0; el('dlg').className=L.doc?'doc':(L.f?'fuente':''); el('dlgW').textContent=L.who; el('dlgF').textContent=L.doc?'':(L.f?'000.00':L.freq||'141.12'); el('dlgT').innerHTML=L.doc?L.html:''; el('dlgK').textContent=L.doc?'E cerrar':'E continuar'; }
function dlgTick(raw){ if(TIT.q){ TIT.t-=raw; if(TIT.t<=0)titNext(); } if(!DLG.q)return; const L=DLG.q[DLG.i]; if(L.doc||DLG.n>=L.text.length)return; DLG.t+=raw; let ch=false; while(DLG.t>0.022&&DLG.n<L.text.length){ DLG.t-=0.022; DLG.n++; ch=true; if(DLG.n%3===0)sTone(L.f?220:900,0.02,0.01,'square'); } if(ch)el('dlgT').textContent=L.text.slice(0,DLG.n); }
function dlgNext(){ if(TIT.q){ titNext(); return true; } if(FIN.on){ FIN.on=false; el('fin').hidden=true; newGame(); return true; } if(!DLG.q)return false; const L=DLG.q[DLG.i]; if(L.opts)return true; if(!L.doc&&DLG.n<L.text.length){ DLG.n=L.text.length; el('dlgT').textContent=L.text; return true; }
  DLG.i++; if(DLG.i>=DLG.q.length){ DLG.q=null; el('dlg').hidden=true; const d=DLG.done; DLG.done=null; if(d)d(); return true; } dlgShow(); return true; }
function titles(list,done){ TIT.q=list; TIT.i=-1; TIT.done=done||null; el('titulo').hidden=false; titNext(); }
function titNext(){ TIT.i++; if(TIT.i>=TIT.q.length){ TIT.q=null; el('titulo').hidden=true; const d=TIT.done; TIT.done=null; if(d)d(); return; } el('titulo').innerHTML=TIT.q[TIT.i][0]+'<small>E para seguir</small>'; TIT.t=TIT.q[TIT.i][1]; }
addEventListener('keydown',e=>{ if((e.code==='Space'||e.code==='Enter')&&hold()){ dlgNext(); e.preventDefault(); } },true);
const C_=t=>({who:'CONTROL',text:t}), F_=t=>({who:'———',f:true,text:t}), Y_=t=>({who:'CUTTLAS',text:t});
const CODEC={
  start:[C_('Cuttlas. Estás en el patio norte. El edificio bajo, con la antena, es comunicaciones. El archivo está detrás, puerta blindada.'),C_('Quiero el expediente LH-07. Está en el archivo, dentro del despacho de Alarcón: el edificio del oeste. La llave del despacho la lleva el cabo Ibarra, que ronda el patio norte.'),C_('El archivo tiene un teclado. La clave no te la voy a dar porque no la tengo: sácasela a la base. No hables con nadie que no haga falta. No leas lo que no es tuyo.'),Y_('...¿Y qué es mío?'),C_('La teniente Roig entra contigo y espera junto al muro norte hasta que la llames. No figura en esta misión. No figura en ninguna.'),C_('Esta noche, el expediente. Corto.')],
  warn:[C_('Llevas demasiado dentro. A las 02:19 sueltan la perrera: siete perros. No les ganas corriendo; o los paras o te paran.')],
  dogs:[C_('Perrera abierta. Siete. Si te cogen vivo, lo que venga después no es cosa nuestra.')],
  cell:[C_('...'),F_('te han bajado un piso. otro más y me oyes sin radio. el que reza fuera tiene un hermano aquí conmigo.')],
  vault:[C_('Puerta abierta. Coge el expediente y sal por la puerta sureste. No lo leas, Cuttlas. Eso no está en la misión.')],
  file:[C_('...Te dije que no lo leyeras.'),C_('Da igual. Mañana no te acordarás. Sal por la puerta sureste y entrégalo. Corto.'),F_('de profundis clamavi ad te. te oigo contar. tú también cuentas como ellos. baja. baja. baja.'),{who:'CUTTLAS',f:true,text:'¿Quién habla?'},F_('la que también clama. nadie la oye. tú sí.')]};
function startStory(){ MS.intro=true; titles([['<span>DOCUMENTO DESCLASIFICADO · 2026</span>LAURA SOROLLA, PERIODISTA:<br>«LO QUE SIGUE LO RECONSTRUÍ A PARTIR DEL EXPEDIENTE LH-07.»',5],['<span>ANDREW CUTTLAS · SUJETO LH-07</span>MISIÓN 1<b>DE PROFUNDIS</b>',5]],()=>codec(CODEC.start)); }
// llamada a Control (X): la pista depende de por dónde vas; nunca da la clave, pero a la segunda equivocación Roig la deja a un paso
function callControl(){ if(!PL.p||hold()||KP.open||ALERT.caught)return; if(CELL.on){ codec(CODEC.cell); return; } if(ALERT.level===2){ say('AHORA NO: TE ESTÁN BUSCANDO',2); return; } MS.calls=(MS.calls||0)+1; const k=msStep(), L=[];
  if(k===0){ L.push(C_('La llave del despacho la lleva un cabo, Ibarra. Llega por detrás y túmbalo. Si prefieres el silenciador, que no lo vea nadie caer.'),Y_('¿Y si grita?'),C_('Entonces no habrás llegado por detrás.')); }
  else if(k===1)L.push(C_('Tienes la llave. El despacho de Alarcón es la puerta del edificio del oeste. Entra, cierra la boca y mira lo que haya en la mesa.'));
  else if(k<=3){ L.push(C_('El archivo pide cuatro cifras y Alarcón no apunta nada: reza. Lee lo que tenga en la mesa y escucha a quien le haya oído rezar.'),C_('Y recuerda: ese hombre cuenta en latín.')); if(KP.bad>=2)L.push({who:'ROIG',freq:'140.85',text:'De profundis. Mi madre lo rezaba: es el ciento treinta... en nuestra Biblia. Alarcón no usa la nuestra. La suya va uno por detrás.'}); }
  else if(k===4)L.push(C_('Dentro del archivo, el archivador. Coge LH-07 y no lo leas, Cuttlas.'));
  else L.push(C_('Puerta sureste. Es lo único que te queda. '+(MS.kill>0?'Deja los muertos donde están; la Compañía ya sabe que funcionas.':'Sin muertos. Así se sale de los sitios sin haber estado.')));
  const ex=[()=>L.push(C_('¿Me oyes bien? Esta frecuencia no está en ningún manual. Está en el dorso de la caja. Siempre la tendrás ahí.')),()=>L.push(C_('Guardo lo que haces cuando pasa algo importante. Si caes, vuelves al último punto. No preguntes cómo; yo tampoco lo sé.')),()=>L.push(Y_('¿Quién eres?'),C_('La voz que te dice adónde ir. Antes había otra. Tú la apagaste, o te la apagaron.'))]; ex[(MS.calls-1)%ex.length](); L.push(C_('Corto.')); codec(L); }
addEventListener('keydown',e=>{ if(e.code==='KeyX')callControl(); });
function ending(){ const k=MS.kill||0, a=MS.alarms||0; let h, p; ALERT.msgT=0; ALERT.msg='';
  if(k===0&&a===0){ h='EL HOMBRE QUE BORRARON'; p='Sales de Tarsis sin que nadie sepa que has pasado. Llevas el expediente, un nombre que no es Cuttlas y la certeza de que abajo hay algo que descansa cuando apagan la luz.'; }
  else if(k>=2){ h='EL ARMA QUE FABRICARON'; p='Sales dejando '+k+' cuerpos. La Compañía ya sabe que funcionas. El expediente no te dice quién eras; te confirma lo que eres.'; }
  else { h='ENTRE DOS MEMORIAS'; p='Sales con la base revuelta. Hay recuerdos de dos vidas y no encajan. Eso, de momento, es lo más parecido a ser alguien.'; }
  el('fin').innerHTML='<h2>'+h+'</h2><p>'+p+'</p>'+(ROIG.ko>0?'<p>Roig durmió a '+ROIG.ko+(ROIG.ko===1?' hombre':' hombres')+' sin que nadie supiera desde dónde. En su informe no aparece. En el tuyo, tampoco.</p>':'')+(MS.cellEsc?'<p>Vidal te vio cruzar el patio y miró a otro lado. Halloran se quedó en la celda por decisión propia: «Alguien tiene que contarlo desde dentro.»</p>':'')+'<p class="m">Laura Sorolla, 2026: «El expediente dice que volvió. No dice adónde.»</p><p class="m">Derribos: '+(MS.ko||0)+' · Muertes: '+k+' · Alarmas: '+a+' · Interrogatorios: '+(MS.interro||0)+(DOG.out?' · Perros: '+DOG.kills+' de 7':'')+'</p><small>E para empezar de nuevo</small>'; el('fin').hidden=false; FIN.on=true; try{ localStorage.removeItem('lh-tarsis'); }catch(e){} }
// ---------- la perrera (src/10-actions.js, 15-loop.js): a los siete minutos avisa Control y a los nueve sueltan siete pastores; se paran a tiros o de una patada (E)
const DOGS=[], DOG={proto:null,t:0,warned:false,out:false,done:false,kills:0};
if(D.dog)new THREE.GLTFLoader().parse(b64(D.dog),'',g=>{ const m=new THREE.MeshStandardMaterial({vertexColors:true,roughness:0.88,metalness:0}); g.scene.traverse(o=>{ if(o.isMesh){ o.material=m; o.castShadow=true; o.frustumCulled=false; } }); DOG.proto=g.scene; });
function dogsClear(){ DOGS.forEach(d=>scene.remove(d.root)); DOGS.length=0; }
function dogDown(d){ d.dead=true; d.root.rotation.z=Math.PI/2; d.root.position.y=0.12; DOG.kills++; sNoise(0.14,500,2,0.18); }
function releaseDogs(n,quiet){ if(!DOG.proto)return; dogsClear(); DOG.out=true; for(let i=0;i<(n||7);i++){ const root=DOG.proto.clone(true); root.position.set((20+i*1.5)*T+T/2,0,1*T+T/2); scene.add(root); DOGS.push({root,yaw:0,path:null,acts:{},wps:[],q:{name:'perro'},legs:['pata_dl','pata_tr','pata_dr','pata_tl'].map(k=>root.getObjectByName(k)).filter(Boolean),ph:i,stun:0,bite:0.4+i*0.1,dead:false,v:4.3+((i*37)%10)*0.05}); }
  if(!quiet)titles([['<span>PATIO NORTE</span>LA PERRERA',3]],()=>codec(CODEC.dogs)); }
function dogTick(dt){ const live=PL.p&&!ALERT.caught&&!CELL.on&&!MS.done;
  if(live&&MS.intro&&!DOG.done&&!DOG.out&&!hold()){ DOG.t+=dt; if(DOG.t>420&&!DOG.warned){ DOG.warned=true; codec(CODEC.warn); } else if(DOG.t>540)releaseDogs(); }
  if(DOG.bcd>0)DOG.bcd-=dt;
  for(const d of DOGS){ if(d.dead)continue; const r=d.root.position; if(d.stun>0){ d.stun-=dt; d.root.rotation.z=Math.PI/2; r.y=0.12; if(d.stun<=0){ d.root.rotation.z=0; r.y=0; } continue; }
    if(!live)continue; const dd=Math.hypot(P.x-r.x,P.z-r.z); let mv=false;
    if(dd>0.95){ goTo(d,P.x,P.z,d.v,dt); mv=true; DOGS.forEach(o=>{ if(o===d||o.dead)return; const q=o.root.position, ex=r.x-q.x, ez=r.z-q.z, e=Math.hypot(ex,ez); if(e<0.55&&e>0.001){ r.x+=ex/e*dt*0.8; r.z+=ez/e*dt*0.8; } }); }
    else { face(d,Math.atan2(P.x-r.x,P.z-r.z),dt,6); d.bite-=dt; if(d.bite<=0&&!(DOG.bcd>0)){ d.bite=1.2; DOG.bcd=0.45; PL.hp-=10; PL.hurt=1; PL.hpT=0; sNoise(0.16,700,2,0.3); if(PL.hp<=0){ PL.hp=0; ALERT.caught=3.2; ALERT.info=false; ALERT.msg='LA PERRERA TE ALCANZA'; ALERT.msgT=3.2; PL.drag=null; } } }
    if(mv)d.ph+=dt*15; const sn=mv?Math.sin(d.ph):0; d.legs.forEach((l,i)=>{ l.rotation.x=(i<2?sn:-sn)*0.75; }); r.y=mv?Math.abs(Math.sin(d.ph))*0.04:0; } }
// ---------- Roig, la compañera: espera donde la dejas o te sigue (Z); los guardias no reparan en ella y solo dispara si te han descubierto (src/11-team.js)
const ROIG={mode:'wait',cd:0,n:0,ko:0,saidK:false};
function roigHome(p){ ROIG.mode='wait'; p.root.position.x=p.q.pos[0]; p.root.position.z=-p.q.pos[1]; p.yaw=p.q.rz; p.root.rotation.y=p.yaw; p.path=null; if(p.act)gAct(p,'idle'); }
function roigTick(p,dt,live){ if(!p.act)p.act='idle'; const r=p.root.position, d=Math.hypot(P.x-r.x,P.z-r.z);
  if(ROIG.mode==='follow'&&live&&!CELL.on&&d>2.4){ gAct(p,'walk',d>7?1.5:1); goTo(p,P.x,P.z,d>7?3.2:1.7,dt); } else gAct(p,'idle');
  if(ROIG.cd>0)ROIG.cd-=dt; else if(live)for(const g of PEOPLE){ if(g.state!=='chase'||g.dead)continue; const q=g.root.position; if(Math.hypot(q.x-r.x,q.z-r.z)>14||blocked(r.x,r.z,q.x,q.z,false))continue;
    ROIG.cd=2.6; p.yaw=Math.atan2(q.x-r.x,q.z-r.z); p.root.rotation.y=p.yaw; pfft(); if(Math.random()<0.7){ const k=PL.kick; koGuard(g); MS.ko--; PL.kick=k; ROIG.ko++; ALERT.sub='<b>Roig</b> Uno menos. No me des las gracias.'; ALERT.subT=2.6; } break; } }
function roigLines(){ const n=ROIG.n++, L=[], RR=t=>L.push({who:'ROIG',freq:'140.85',text:t});
  RR(ROIG.mode==='wait'?'Estoy donde me dejaste. Si disparo es porque os han visto. Si me quieres detrás, ya sabes cómo pedirlo.':'Estoy a dos pasos. Si disparo es porque os han visto; si no disparo, agradécemelo luego.');
  if(MS.kill>0&&!ROIG.saidK){ ROIG.saidK=true; RR('Has matado a uno. Antes no lo hacías. O sí, y no te acuerdas. Yo sí me acuerdo.'); }
  else if(!MS.vault&&(MS.code||(MS.clues||{}).rezo)&&n>=1)RR('De profundis. Mi madre lo rezaba: es el ciento treinta... en nuestra Biblia. Alarcón no usa la nuestra. La suya va uno por detrás.');
  else RR(['Cuando esto acabe te llevo a esa cocina que sueñas. Si existe. Si no, a otra.','Cuttlas: la luz de la tarde no existe aquí. Solo llueve. Lo digo por si te orientas por eso.','Hablas dormido. Cuentas. Siempre te paras en ciento veintinueve y vuelves a empezar.'][n%3]); return L; }
addEventListener('keydown',e=>{ if(e.code!=='KeyZ'||!PL.p||hold()||KP.open||CELL.on)return; if(!PEOPLE.some(o=>o.q.name==='roig'))return; ROIG.mode=ROIG.mode==='wait'?'follow':'wait'; say(ROIG.mode==='follow'?'ROIG TE SIGUE':'ROIG ESPERA AQUÍ',2); });
// ---------- diálogos con opciones (1-9 o tocar), interrogatorios por la espalda y la celda con Vidal y Halloran, traídos de src/04-state.js y src/10-actions.js
const CELL={on:false,vis:false,back:false,stage:0,fail:0,gone:false,key:false,slab:false};
function choose(who,html,opts){ ALERT.msgT=0; PL.aiming=false; DLG.q=[{who,doc:true,opts,html:html+'<ol class="op">'+opts.map((o,i)=>'<li data-i="'+i+'">'+o.t+'</li>').join('')+'</ol>'}]; DLG.i=0; DLG.done=null; el('dlg').hidden=false; dlgShow(); el('dlg').className='ask'; el('dlgK').textContent='1 a '+opts.length+' para elegir'; }
function pick(i){ const L=DLG.q&&DLG.q[DLG.i]; if(!L||!L.opts||!L.opts[i])return false; DLG.q=null; el('dlg').hidden=true; click(900,0.04); const f=L.opts[i].f; if(f)f(); return true; }
addEventListener('keydown',e=>{ const m=/^(?:Digit|Numpad)(\d)$/.exec(e.code); if(m&&DLG.q&&DLG.q[DLG.i].opts){ pick(+m[1]-1); e.stopImmediatePropagation(); e.preventDefault(); } },true);
el('dlg').addEventListener('click',e=>{ const li=e.target.closest&&e.target.closest('li[data-i]'); if(li){ pick(+li.dataset.i); e.stopPropagation(); } });
const clue=k=>{ (MS.clues=MS.clues||{})[k]=true; };
const GEN={nerve:2,clave:[[0,'Ni idea. Yo soy de la garita, la clave es cosa de Alarcón.']],llave:[[0,'La del despacho la tiene el cabo Ibarra. Pregúntale a él, si te deja.']],templo:[[0,'De eso no se habla.'],[2,'Dicen que canta. Por la noche, cuando paran los generadores. Yo no quiero oírlo.','fuente']]};
const GQ={
  peris:{nerve:2,clave:[[0,'Yo hago el rancho. La clave la pone el coronel y no la suelta.'],[1,'No la sé, de verdad. Pero el coronel reza en el despacho y se le oye por la pared: «desde lo profundo», siempre lo mismo. Ibarra dice que la clave es eso, el rezo.','rezo']],llave:[[0,'La del despacho la lleva Ibarra, el cabo. Siempre encima.']],templo:[[0,'No bajo. Nadie de cocina baja.'],[2,'Se oye. Cuando apagan el generador se oye algo que respira abajo. Lo llaman «la carga». Los que bajan vuelven sordos, o no vuelven.','fuente']]},
  ibarra:{nerve:3,clave:[[0,'Pregúntaselo a Alarcón. Yo no soy el archivo.'],[2,'Es el salmo que reza, hombre. El De profundis. El ciento treinta. Lo sabe media base, no es un secreto.','rezo']],llave:[[0,'¿Qué llave?'],[1,'La llevo yo. Bolsillo izquierdo. Cógela y acaba de una vez.','llave']],templo:[[0,'Combustible. Un depósito.'],[3,'Yo bajo con los partes. Hay algo ahí que no es combustible. Alarcón le reza a eso, no a Dios.','fuente']]},
  moya:{nerve:4,clave:[[0,'Mil novecientos ochenta y tres. El año. Métela y lárgate.'],[3,'...Vale. Vale. No es el número que crees. El coronel reza en latín, con la Vulgata. Cuenta los salmos como Roma, no como los protestantes. Uno menos.','rezo']],llave:[[0,'Ibarra. El cabo. Siempre la lleva él.']],templo:[[0,'Un almacén.'],[2,'Yo llevo los partes a la Compañía. Cuatro bajas este mes por «voces». Lo que hay abajo no es combustible. Y Halloran lo sabía antes que nadie; por eso está en la celda.','partes']]}};
function koGuard(g){ MS.ko=(MS.ko||0)+1; g.frz=false; g.dead=true; g.found=false; g.path=null; if(g.acts.down){ const a=g.acts[g.act], b=g.acts.down; b.reset(); b.play(); if(a)a.crossFadeTo(b,0.12,false); g.act='down'; } sNoise(0.12,220,1,0.16); PL.kick=0.6; }
function grab(g){ g.frz=true; g.fear=1; g.path=null; gAct(g,'idle'); MS.interro=(MS.interro||0)+1; sTone(200,0.1,0.05,'square'); const go=()=>interro(g,'Lo agarras por el cuello desde atrás. No grita. Todavía.');
  if(!MS.memI){ MS.memI=true; doc('RECUERDO · EL PROGRAMA','<p>Sabes exactamente cuánto apretar para que hable y cuánto para que no vuelva a hablar.</p><p>Nadie te lo enseñó. Alguien te lo enseñó.</p>',go); } else go(); }
function interro(g,last){ const q=(!g.q.src&&GQ[g.q.name])||GEN, nv=q.nerve, f=g.fear, r=g.root.position, ft=f>=nv?'Está al límite. Si aprietas más, grita.':f>=nv-1?'Tiembla. Le cuesta respirar.':f>=2?'Respira rápido.':'Aguanta. Te mide.';
  const ask=k=>()=>{ const L=q[k]; let b=L[0]; L.forEach(e=>{ if(e[0]<=g.fear)b=e; }); let t='«'+b[1]+'»'; if(b[2]){ clue(b[2]); if(b[2]==='partes')clue('fuente'); if(b[2]==='llave'&&!MS.key){ MS.key=true; t+=' <i>Le quitas la llave.</i>'; } } interro(g,t); };
  choose(gName(g).toUpperCase()+' · MIEDO '+f+'/'+nv,'<p>'+last+'</p><p class="st">'+ft+'</p>',[{t:'«¿La clave del archivo?»',f:ask('clave')},{t:'«¿Quién tiene la llave del despacho?»',f:ask('llave')},{t:'«¿Qué hay bajo el templo?»',f:ask('templo')},
    {t:'Apretar',f:()=>{ g.fear++; if(g.fear>nv){ koGuard(g); NOISES.push({x:r.x,z:r.z,r:22}); gWary(60); MS.alarms=(MS.alarms||0)+1; say('GRITA ANTES DE CAER. LA BASE LO HA OÍDO',4); return; } sTone(120,0.1,0.05,'sawtooth'); interro(g,'Aprietas. Se le doblan las rodillas.'); }},
    {t:'Dormirlo',f:()=>koGuard(g)},{t:'Soltarlo',f:()=>{ g.frz=false; g.seen=[P.x,P.z]; g.meter=0.8; g.wary=60; setState(g,'search'); say('LO SUELTAS. AVISARÁ EN CUANTO RESPIRE',3); }}]); }
// la primera vez que te cogen despiertas en el calabozo; la segunda vuelves al último punto guardado
function toCell(){ resetStealth(); MS.cellDone=true; Object.assign(CELL,{on:true,vis:true,back:false,stage:0,fail:0,gone:false,key:false,slab:false}); const d=DOORS.b; d.want=0; MAP[d.y]=MAP[d.y].slice(0,d.x)+'b'+MAP[d.y].slice(d.x+1); P.x=d.cx; P.z=d.cz+3.4; P.yaw=0; P.pitch=0; PL.crouch=false; PL.mag=0; PL.res=0; ALERT.msgT=0; save();
  doc('CALABOZO','<p>Despiertas en el calabozo, sin pistola. Al otro lado de los barrotes, el cabo Vidal hace guardia y reza en voz baja.</p><p>Por la rejilla del tabique, una voz de mujer: «Ha tardado, Cuttlas. Siempre tarda.»</p>',()=>codec(CODEC.cell)); }
function openCell(viaKey){ CELL.on=false; CELL.back=true; MS.cellEsc=true; openDoor('b'); DOORS.b.noted=true; if(!viaKey)PL.mag=4; sTone(500,0.1,0.05,'square');
  doc('CELDA ABIERTA',viaKey?'<p>La llave del hermano gira sin ruido. Vidal no se vuelve.</p><p>Sales sin balas.</p>':'<p>Vidal te devuelve la pistola con cuatro balas y se queda rezando de cara a la pared.</p><p>«Yo no le he visto.»</p>'); }
const HAL='DRA. HALLORAN · POR LA REJILLA';
function hallo(){ const o=[{t:'«¿Quién es usted?»',f:()=>choose(HAL,'<p>«Marion Halloran. Firmé su expediente, Cuttlas. Luego firmé que lo que hay abajo está vivo y sufre, y por eso estoy aquí. Nadie cree a quien lo dice primero.»</p>',o)},
  {t:'«¿Qué hay bajo el templo?»',f:()=>{ clue('fuente'); choose(HAL,'<p>«Una fuente. De energía, dicen ellos; de algo más, digo yo. Responde a los sujetos del programa. Cuando paran el generador deja de gritar; no es que se calle, es que descansa.»</p>',o); }},
  {t:'«¿Cómo entro en el archivo?»',f:()=>{ clue('hallo'); choose(HAL,'<p>«La clave de Alarcón es su rezo, el salmo que repite. Pero reza con la Vulgata, en latín. Si cuenta usted como un protestante, se equivocará de salmo.»</p>',o); }},
  {t:'«¿Y si Vidal no cede?»',f:()=>{ CELL.slab=true; choose(HAL,'<p>«El que ocupó ese catre antes que usted dejó algo bajo la losa suelta del rincón, a su izquierda según mira a la reja. Yo no lo he tocado: no era mío. Si Vidal no abre, ábrala usted.»</p>',o); }},{t:'Dejarlo'}];
  choose(HAL,'<p>«Vidal reza porque su hermano bajó en octubre y volvió sordo; luego no volvió. No le amenace, Cuttlas: a los que amenazan ya los ha visto. Háblele de lo que oye por las noches. Y si sabe rezar, rece.»</p>',o); }
const VIDAL=[{q:'Vidal no te mira. Mueve los labios: reza.',o:[
   ['«Abre, o cuando salga te busco a ti primero.»',0,'«Amenace. Aquí dentro no cuesta nada.» Se aleja un paso.'],
   ['«¿Lo oyes por las noches? Lo de abajo.»',1,'Deja de rezar. «Todos lo oímos. Nadie lo dice.»'],
   ['«Alarcón te ascenderá si me sueltas. Yo se lo diré.»',0,'«Alarcón no asciende. Alarcón baja gente.» Vuelve al rezo.']]},
 {q:'«¿Y usted qué sabe de lo de abajo?»',o:[
   ['«Es combustible. Un depósito. Me lo dijo Ibarra.»',0,'«Ibarra dice lo que le mandan.» Pierde interés.'],
   [()=>MS.clues.fuente||MS.clues.hallo?'«Que está vivo y sufre. Halloran lo escribió y por eso está aquí dentro.»':'«Que grita.»',()=>MS.clues.fuente||MS.clues.hallo,'Mira hacia la rejilla. «Mi hermano bajó en octubre. Volvió sordo. Luego no volvió.»','«Eso lo sabe cualquiera que haya dormido aquí.» No basta. «Pregúntele a la doctora. Ella sí sabe lo que es.»'],
   ['«Que son los perros. Nada más.»',0,'Casi sonríe. «Los perros los suelto yo. No son eso.»']]},
 {q:'«Aunque le creyera. ¿Por qué iba a abrir?»',o:[
   [()=>MS.file?'«Alarcón firmó mi traslado a la excavación. Lee el expediente: el siguiente en bajar lleva tu apellido.»':'«Los partes hablan de cuatro bajas por voces. A vosotros no os lo cuentan.»',()=>MS.file||MS.clues.partes,'Le tiemblan las manos. «Vidal, J. Octubre.» Saca la llave.','«Palabras.» Halloran, bajo: «Dele algo que haya leído, Cuttlas. O rece con él.»'],
   [()=>MS.code||MS.clues.rezo||MS.clues.hallo?'«Reza conmigo. De profundis clamavi ad te, Domine.»':'«Reza conmigo.»',()=>MS.code||MS.clues.rezo||MS.clues.hallo,'Se le quiebra la voz en el segundo verso. «Desde lo profundo...» Abre sin mirarte. «Ella también clama, ¿verdad?»','«Usted no reza.» Vuelve la espalda.'],
   ['«Te daré el expediente. Véndelo.»',0,'«¿Y qué hago yo con eso?» Se va.']]}];
function vidal(){ MS.clues=MS.clues||{}; const st=VIDAL[CELL.stage], v=x=>typeof x==='function'?x():x;
  choose('CABO VIDAL · '+(CELL.stage+1)+'/3','<p>'+st.q+'</p>',st.o.map(o=>({t:v(o[0]),f:()=>{ if(v(o[1])){ CELL.stage++; if(CELL.stage>=VIDAL.length)doc('CABO VIDAL','<p>'+o[2]+'</p>',()=>openCell(false)); else doc('CABO VIDAL','<p>'+o[2]+'</p>',vidal); }
    else { CELL.fail++; CELL.gone=CELL.fail>=3; if(CELL.gone)CELL.back=true; doc('CABO VIDAL','<p>'+(o[3]||o[2])+'</p><p class="st">'+(CELL.gone?'Vidal no volverá a escucharte. Halloran: «Hay otra manera. La losa del rincón.»':'Vuelve al rezo, pero sigue ahí. Intentos fallidos: '+CELL.fail+' de 3')+'</p>'); } }})).concat([{t:'Dejarlo'}])); }
function cellUse(test){ if(near(PTS.hallo,1.1)){ if(!test)hallo(); return 'E hablar por la rejilla'; }
  if(!CELL.key&&(CELL.slab||CELL.gone)&&near(PTS.losa,1.2)){ if(!test)choose('LOSA SUELTA','<p>Una losa del rincón baila bajo el pie. Debajo, envuelta en un trapo, hay una llave de hierro y una medalla con un nombre rayado a punta de navaja: <b>VIDAL, J.</b></p><p>Halloran: «El hermano. La escondió antes de bajar. No llegó a usarla.»</p>',[{t:'Coger la llave',f:()=>{ CELL.key=true; say('LLAVE DE LA CELDA',3); }},{t:'Dejarla'}]); return 'E losa suelta'; }
  if(near(PTS.bars,1.5)){ if(!test){ if(CELL.key)openCell(true); else if(CELL.gone)doc('CABO VIDAL','<p>Reza de cara a la pared y no se vuelve.</p><p>Halloran, por la rejilla: «Ya no. Busque la losa del rincón.»</p>'); else vidal(); } return CELL.key?'E abrir la reja con la llave':CELL.gone?'Vidal ya no escucha':'E hablar con el cabo Vidal'; }
  return null; }
function msStep(){ return !MS.key?0:!MS.door?1:!MS.code?2:!MS.vault?3:!MS.file?4:5; }
function msTarget(){ if(CELL.on)return PTS.bars; const k=msStep(), ib=PEOPLE.find(o=>o.q.name==='ibarra'); return k===0?(ib?[ib.root.position.x,ib.root.position.z]:null):k===1?[DOORS.L.cx,DOORS.L.cz]:k===2?PTS.note:k===3?[DOORS.V.cx,DOORS.V.cz]:k===4?PTS.file:PTS.exit; }
const MS_TXT=['Consigue la llave del cabo Ibarra, que ronda el patio norte: abátelo de un tiro o agárralo por la espalda','Abre el despacho de Alarcón con la llave de Ibarra','Registra el escritorio de Alarcón: la clave del archivo no está apuntada','Abre el archivo. La clave es el rezo de Alarcón, contado como lo cuenta él','Coge el expediente LH-07 del archivador','Sal por la puerta sureste con el expediente'];
function near(pt,r){ return pt&&Math.hypot(pt[0]-P.x,pt[1]-P.z)<(r||1.9); }
function msUse(test){ const ib=PEOPLE.find(o=>o.q.name==='ibarra'); if(MS.done)return null; if(CELL.on)return cellUse(test);
  for(const g of PEOPLE){ if(g===PL.p||g.dead||!g.state||g.state==='chase')continue; const r=g.root.position, dx=P.x-r.x, dz=P.z-r.z, d=Math.hypot(dx,dz); if(d>1.5)continue; let da=Math.atan2(dx,dz)-g.yaw; while(da>Math.PI)da-=2*Math.PI; while(da<-Math.PI)da+=2*Math.PI; if(Math.abs(da)<2.0)continue;
    if(!test)grab(g); return 'E agarrarlo'; }
  for(const dg of DOGS){ if(dg.dead||dg.stun>0)continue; const r=dg.root.position, dd=Math.hypot(r.x-P.x,r.z-P.z); if(dd>1.8)continue; if(!test){ dg.stun=5; dg.bite=1; r.x+=(r.x-P.x)/(dd||1)*0.8; r.z+=(r.z-P.z)/(dd||1)*0.8; sNoise(0.1,300,1,0.2); say('PATADA. CINCO SEGUNDOS, NO MÁS',2); } return 'E patada'; }
  { const ro=PEOPLE.find(o=>o.q.name==='roig'); if(ro&&near([ro.root.position.x,ro.root.position.z],1.7)){ if(!test)codec(roigLines()); return 'E hablar con Roig'; } }
  if(!MS.door&&near([DOORS.L.cx,DOORS.L.cz],2.1)){ if(!test){ if(MS.key){ MS.door=true; openDoor('L'); } else say('CERRADA. LA LLAVE LA LLEVA EL CABO IBARRA'); } return 'E abrir el despacho'; }
  if(!MS.code&&near(PTS.note)){ if(!test){ MS.code=true; doc('ESCRITORIO DE ALARCÓN','<p>Una <b>Biblia Sacra Vulgata</b> abierta, muy usada. La cinta marca <b>PSALMUS CXXIX</b>: «De profundis clamavi ad te, Domine».</p><p>En el margen, a lápiz: «Ella también clama. Nadie la oye. — A.»</p><p>Debajo, una nota: «Clave: la de siempre. No apuntar.»</p>'); } return 'E registrar el escritorio'; }
  if(MS.code&&!MS.vault&&near(PTS.note)){ if(!test)doc('ESCRITORIO DE ALARCÓN','<p>La Vulgata sigue abierta por el <b>PSALMUS CXXIX</b>.</p><p>«Clave: la de siempre. No apuntar.»</p>'); return 'E releer el escritorio'; }
  if(!MS.vault&&near([DOORS.V.cx,DOORS.V.cz],2.1)){ if(!test){ KP.open=true; KP.buf=''; KP.err=0; } return 'E teclado del archivo'; }
  if(!MS.file&&near(PTS.file)){ if(!test){ MS.file=true; MS.folder.visible=false; doc('EXPEDIENTE LH-07','<p>SUJETO: CUTTLAS, A. · ESTADO: OPERATIVO · MEMORIA: BORRADA (3ª SESIÓN).</p><p>«Tras cada sesión el sujeto recupera un mismo fragmento: una cocina, luz de tarde, una voz femenina que lo llama por otro nombre. Se recomienda una cuarta sesión y el traslado a la excavación: la carga responde a los sujetos del programa.»</p><p>Firma: Halloran, M. (anulada). Contrafirma: Alarcón.</p>',()=>doc('RECUERDO','<p>La cocina. La voz dice el nombre entero y por primera vez lo oyes: no es Cuttlas.</p><p>Lo escribieron ellos.</p>',()=>codec(CODEC.file))); } return 'E abrir el archivador'; }
  return null; }
function save(){ try{ localStorage.setItem('lh-tarsis',JSON.stringify({v:1,cd:!!MS.cellDone,cl:MS.clues||{},ms:[MS.key,MS.door,MS.code,MS.vault,MS.file],mag:PL.mag,res:PL.res,p:[P.x,P.z,P.yaw]})); }catch(e){} }
function load(){ let d=null; try{ d=JSON.parse(localStorage.getItem('lh-tarsis')||'null'); }catch(e){} if(!d||d.v!==1||!d.ms.some(Boolean))return false; [MS.key,MS.door,MS.code,MS.vault,MS.file]=d.ms; if(MS.door)openDoor('L'); if(MS.vault)openDoor('V'); MS.folder.visible=!MS.file; MS.intro=true; MS.cellDone=!!d.cd; MS.clues=d.cl||{};
  PL.mag=d.mag; PL.res=d.res; P.x=d.p[0]; P.z=d.p[1]; P.yaw=d.p[2]; MS.spawn=d.p; MS.sig=d.ms.join(); return true; }
function newGame(){ try{ localStorage.removeItem('lh-tarsis'); }catch(e){} lampsOn(); MS.spawn=null; msReset(); resetStealth(); MS.sig=[MS.key,MS.door,MS.code,MS.vault,MS.file].join(); }
addEventListener('keydown',e=>{ if(e.code==='KeyN'&&PL.p&&!KP.open&&!locked){ newGame(); say('PARTIDA NUEVA',2); } });
function msReset(){ MS.key=MS.door=MS.code=MS.vault=MS.file=false; MS.done=0; MS.intro=false; MS.kill=MS.ko=MS.alarms=MS.calls=0; MS.alarmSaid=false; KP.bad=0; MS.cellDone=MS.cellEsc=MS.memI=false; MS.interro=0; MS.clues={}; Object.assign(CELL,{on:false,vis:false,back:false}); Object.assign(ROIG,{mode:'wait',cd:0,n:0,ko:0,saidK:false}); dogsClear(); Object.assign(DOG,{t:0,warned:false,out:false,done:false,kills:0}); MS.paper.visible=MS.folder.visible=true; for(const c in DOORS){ const d=DOORS[c]; d.want=0; d.noted=false; MAP[d.y]=MAP[d.y].slice(0,d.x)+c+MAP[d.y].slice(d.x+1); } }
function msTick(dt){ dogTick(dt); { const sig=[MS.key,MS.door,MS.code,MS.vault,MS.file].join(); if(PL.p&&MS.sig!==undefined&&sig!==MS.sig&&!MS.done){ MS.sig=sig; MS.spawn=[P.x,P.z,P.yaw]; save(); el('guard').hidden=false; MS.gT=1.6; } if(MS.gT>0){ MS.gT-=dt; if(MS.gT<=0)el('guard').hidden=true; } } for(const c in DOORS){ const d=DOORS[c]; d.open+=(d.want-d.open)*Math.min(1,dt*3); d.piv.rotation.y=-1.7*d.open; }
  const ib=PEOPLE.find(o=>o.q.name==='ibarra'); if(PL.p&&!MS.key&&ib&&ib.dead&&near(bodyC(ib),1.7)){ MS.key=true; say('LLAVE DE IBARRA',2.2); }
  if(PL.p&&MS.file&&!MS.done&&near(PTS.exit,2.6)){ MS.done=1e9; ending(); }
  const o=el('obj'), tg=PL.p&&!MS.done?msTarget():null; if(o){ o.hidden=!PL.p; setH(o,MS.done?'':CELL.on?(CELL.key?'Abre la reja con la llave':CELL.gone?'Busca otra salida de la celda':'Habla con Halloran por la rejilla y convence al cabo Vidal'):MS_TXT[msStep()]); }
  MS.mk.visible=!!tg; if(tg){ const d=Math.hypot(tg[0]-camera.position.x,tg[1]-camera.position.z), k=Math.max(0.35,Math.min(2.4,d*0.03)); MS.mk.position.set(tg[0],msStep()===0?2.6:2.5,tg[1]); MS.mk.scale.set(k,k,1); } }
function useKey(){ if(dlgNext())return; if(!PL.p||ALERT.caught)return; if(KP.open){ KP.open=false; return; } if(!PL.drag&&msUse(false))return; if(PL.drag){ const o=PL.drag, c=bodyC(o); PL.drag=null; o.hidden=coverAt(c[0],c[1]); ALERT.msg=o.hidden?'CUERPO OCULTO':''; ALERT.msgT=o.hidden?1.8:0; return; } const o=nearBody(); if(o&&PL.rel<=0){ PL.drag=o; o.hidden=false; PL.aiming=false; } }
function dragTick(dt){ const o=PL.drag; if(o){ const r=o.root.position, dx=P.x-r.x, dz=P.z-r.z, d=Math.hypot(dx,dz); o.yaw=Math.atan2(dx,dz); o.root.rotation.y=o.yaw; if(d>0.75){ const k=(d-0.75)/d, nx=r.x+dx*k, nz=r.z+dz*k; if(!solid(Math.floor(nx/T),Math.floor(nz/T))){ r.x=nx; r.z=nz; } else if(d>2.2)PL.drag=null; } }
  const t=el('mun'); if(t){ t.hidden=!PL.p; const mu=!PL.drag&&msUse(true), nb=!PL.drag&&!mu&&nearBody(); setH(t,(PL.rel>0?'RECARGANDO':PL.mag+' <i>/ '+PL.res+'</i>')+(PL.drag?'<u>E soltar el cuerpo</u>':mu?'<u>'+mu+'</u>':nb?'<u>E arrastrar el cuerpo</u>':PL.mag<8&&PL.res>0&&PL.rel<=0?'<u>R recargar</u>':'')); } }
addEventListener('keydown',e=>{ if(e.code==='KeyR')reload(); if(e.code==='KeyE')useKey(); });
// ---------- radar: plano girado con la vista, muros, guardias con su cono de visión, cuerpos y el objetivo. Con la alarma se llena de interferencias.
const RAD={n:0,R:20};
function radarTick(){ const cvs=el('radar'); if(!cvs)return; cvs.hidden=!PL.p; if(!PL.p||(RAD.n++%3))return; const x=cvs.getContext('2d'), W=cvs.width, c=W/2, k=c/RAD.R; x.setTransform(1,0,0,1,0,0); x.clearRect(0,0,W,W);
  x.save(); x.beginPath(); x.arc(c,c,c-1,0,7); x.clip(); x.fillStyle='rgba(6,14,10,0.72)'; x.fillRect(0,0,W,W);
  if(ALERT.level===2){ for(let i=0;i<70;i++){ x.fillStyle='rgba(120,255,160,'+(Math.random()*0.35)+')'; x.fillRect(0,Math.random()*W,W,1+Math.random()*2); } x.fillStyle='#ff4a3a'; x.font='bold 13px monospace'; x.textAlign='center'; x.fillText('INTERFERENCIA',c,c+4); x.restore(); return; }
  x.translate(c,c); x.rotate(P.yaw); x.scale(k,k); x.translate(-P.x,-P.z);
  const x0=Math.max(0,Math.floor((P.x-RAD.R)/T)), x1=Math.min(COLS-1,Math.floor((P.x+RAD.R)/T)), y0=Math.max(0,Math.floor((P.z-RAD.R)/T)), y1=Math.min(ROWS-1,Math.floor((P.z+RAD.R)/T));
  for(let ty=y0;ty<=y1;ty++)for(let tx=x0;tx<=x1;tx++){ const ch=MAP[ty][tx]; const col='#W'.indexOf(ch)>=0?'rgba(120,220,150,0.8)':'TcgbLV'.indexOf(ch)>=0?'rgba(120,220,150,0.38)':'_zd'.indexOf(ch)>=0?'rgba(120,220,150,0.1)':null; if(col){ x.fillStyle=col; x.fillRect(tx*T,ty*T,T,T); } }
  if(PL.nz>0.3){ x.strokeStyle='rgba(255,255,255,0.55)'; x.lineWidth=0.25; x.beginPath(); x.arc(P.x,P.z,PL.nz,0,7); x.stroke(); } if(PL.ping){ x.strokeStyle='rgba(255,176,96,'+Math.min(1,PL.ping.t)+')'; x.lineWidth=0.3; x.beginPath(); x.arc(PL.ping.x,PL.ping.z,9*(1.2-PL.ping.t)/1.2,0,7); x.stroke(); }
  PEOPLE.forEach(o=>{ if(o===PL.p||!o.state)return; const r=o.root.position; if(o.dead){ const b=bodyC(o); x.fillStyle=o.hidden?'rgba(150,150,150,0.5)':'#bdbdbd'; x.fillRect(b[0]-0.35,b[1]-0.35,0.7,0.7); return; }
    const col=o.state==='chase'?'255,70,50':(o.state==='suspect'||o.state==='search')?'255,210,58':'120,200,255', a=Math.atan2(Math.cos(o.yaw),Math.sin(o.yaw)), rg=(PL.crouch?7:13)*(0.45+0.55*(PL.lit===undefined?1:PL.lit));
    x.fillStyle='rgba('+col+',0.2)'; x.beginPath(); x.moveTo(r.x,r.z); x.arc(r.x,r.z,rg,a-0.85,a+0.85); x.closePath(); x.fill(); x.fillStyle='rgb('+col+')'; x.beginPath(); x.arc(r.x,r.z,0.6,0,7); x.fill(); });
  x.restore(); x.save(); x.beginPath(); x.arc(c,c,c-1,0,7); x.strokeStyle='rgba(120,220,150,0.5)'; x.lineWidth=1.5; x.stroke();
  const tg=!MS.done&&msTarget(); if(tg){ const dx=tg[0]-P.x, dz=tg[1]-P.z, cs=Math.cos(P.yaw), sn=Math.sin(P.yaw); let sx=(dx*cs-dz*sn)*k, sy=(dx*sn+dz*cs)*k; const d=Math.hypot(sx,sy), m=c-7; if(d>m){ sx*=m/d; sy*=m/d; }
    x.translate(c+sx,c+sy); x.rotate(Math.PI/4); x.fillStyle='#ffb060'; x.fillRect(-3.5,-3.5,7,7); x.setTransform(1,0,0,1,0,0); }
  x.fillStyle='#fff'; x.beginPath(); x.moveTo(c,c-6); x.lineTo(c+4.5,c+5); x.lineTo(c-4.5,c+5); x.closePath(); x.fill(); x.restore(); }
function fxTick(dt){ PL.tossT=Math.max(0,(PL.tossT||0)-dt); if(PL.ping){ PL.ping.t-=dt; if(PL.ping.t<=0)PL.ping=null; } PL.nz=Math.max(NOISE.r||0,(PL.nz||0)-dt*8); radarTick(); if(PL.rel>0){ PL.rel-=dt; if(PL.rel<=0){ const n=Math.min(8-PL.mag,PL.res); PL.mag+=n; PL.res-=n; click(700,0.05); } } dragTick(dt); msTick(dt); hpTick(dt); sndTick(dt); kpTick(dt); PL.cd=Math.max(0,(PL.cd||0)-dt); PL.kick=(PL.kick||0)*Math.max(0,1-dt*9); PL.flashT=(PL.flashT||0)-dt; FX.flash.visible=PL.flashT>0&&VM.visible; FX.hits.forEach(h=>{ if(h.t>0){ h.t-=dt; h.m.scale.setScalar(Math.max(0.05,h.t/0.14)); if(h.t<=0)h.m.visible=false; } }); }
addEventListener('mousedown',e=>{ if(e.button===0&&document.pointerLockElement===renderer.domElement){ if(hold())dlgNext(); else shoot(); } });
function plAct(name){ const p=PL.p; if(!p||PL.act===name||!p.acts[name])return; const a=p.acts[PL.act], b=p.acts[name]; b.reset(); b.play(); if(a)a.crossFadeTo(b,0.22,false); PL.act=name; }
addEventListener('keydown',e=>{ if(e.code==='KeyV'&&PL.p){ PL.third=!PL.third; } if(e.code==='KeyC'&&PL.p){ PL.crouch=!PL.crouch; } });
function move(dt){ let f=(keys.KeyW||keys.ArrowUp?1:0)-(keys.KeyS||keys.ArrowDown?1:0)-touch.mz, s=(keys.KeyD||keys.ArrowRight?1:0)-(keys.KeyA||keys.ArrowLeft?1:0)+touch.mx; if((PL.p&&PL.third&&ALERT.caught)||KP.open){ f=0; s=0; } const l=Math.hypot(f,s); if(l>1){ f/=l; s/=l; }
  const third=PL.p&&PL.third, fast=keys.ShiftLeft||keys.ShiftRight;
  PL.aim+=((PL.aiming&&!third&&!PL.drag&&!(PL.rel>0)?1:0)-PL.aim)*Math.min(1,dt*11); const A=PL.aim; const fov=68-22*A; if(Math.abs(camera.fov-fov)>0.05){ camera.fov=fov; camera.updateProjectionMatrix(); }
  const sp=(third?(PL.drag?0.7:PL.crouch?0.78:(fast?1.85:1.12)):(PL.drag?1.05:PL.crouch?1.3:(fast?6.2:2.6))*(1-0.5*A))*dt; const sin=Math.sin(P.yaw), cos=Math.cos(P.yaw); const dx=(-sin*f+cos*s)*sp, dz=(-cos*f-sin*s)*sp; const R=0.32;
  const inObst=(x,z)=>OBST.some(o=>{ const dx=x-o[1], dz=z+o[2], c=Math.cos(o[5]), sn=Math.sin(o[5]), u=dx*c-dz*sn, v=-dx*sn-dz*c; return Math.abs(u)<o[3]+0.24&&Math.abs(v)<o[4]+0.24; });
  const free0=(x,z)=>!solid(Math.floor((x-R)/T),Math.floor((z-R)/T))&&!solid(Math.floor((x+R)/T),Math.floor((z-R)/T))&&!solid(Math.floor((x-R)/T),Math.floor((z+R)/T))&&!solid(Math.floor((x+R)/T),Math.floor((z+R)/T));
  const free=(x,z)=>free0(x,z)&&(!inObst(x,z)||inObst(P.x,P.z)); window.__ESC&&(window.__ESC.canStand=(x,z)=>free0(x,z)&&!inObst(x,z));   // los muebles estorban; si ya estás dentro de uno, te deja salir
  if(free(P.x+dx,P.z))P.x+=dx; if(free(P.x,P.z+dz))P.z+=dz; if(l>0.05)P.bob+=dt*(fast?13:8.5); sStep(l>0.05,fast);
  camera.rotation.set(0,0,0); camera.rotation.order='YXZ'; camera.rotation.y=P.yaw; camera.rotation.x=P.pitch;
  VM.visible=!third&&!!PL.p; const mira=el('mira'); if(mira)mira.hidden=!(A>0.6);
  if(!third){ PL.eye+=((PL.crouch?1.05:1.66)-PL.eye)*Math.min(1,dt*8); const lm=Math.min(1,l); camera.position.set(P.x,PL.eye+Math.sin(P.bob)*0.028*lm*(1-0.6*A),P.z);
    VM.position.set(0.17*(1-A)+Math.cos(P.bob*0.5)*0.005*lm*(1-A),-0.165*(1-A)-0.0255*A+Math.sin(P.bob)*0.006*lm*(1-0.7*A),-0.42+0.08*A); VM.rotation.set(0.02*(1-A)+(PL.kick||0)*0.16,0.07*(1-A),0); { const dn=PL.drag?1:(PL.rel>0?Math.min(1,Math.min(PL.rel,1.5-PL.rel)*5):0); PL.low=(PL.low||0)+(dn-(PL.low||0))*Math.min(1,dt*10); VM.position.y-=PL.low*0.2; VM.rotation.x-=PL.low*0.7; } VM.position.z+=(PL.kick||0)*0.035; VM.position.y+=(PL.kick||0)*0.012;
    if(PL.p){ PL.p.root.visible=false; PL.p.root.position.set(P.x,PL.p.q.pos[2],P.z); if(l>0.05&&!PL.crouch){ NOISE.x=P.x; NOISE.z=P.z; NOISE.r=fast?7:2; } } return; }
  const p=PL.p, moving=l>0.05; if(moving){ const want=Math.atan2(dx,dz); let da=want-PL.yaw; while(da>Math.PI)da-=2*Math.PI; while(da<-Math.PI)da+=2*Math.PI; PL.yaw+=Math.max(-9*dt,Math.min(9*dt,da)); }
  if(moving&&!PL.crouch){ NOISE.x=P.x; NOISE.z=P.z; NOISE.r=fast?7:2; }
  plAct(moving?(PL.crouch?'sneak':'walk'):(PL.crouch?'idle':'stand')); if(p.acts.walk)p.acts.walk.timeScale=fast?1.65:1;
  p.root.position.set(P.x,p.q.pos[2],P.z); p.root.rotation.y=PL.yaw; p.root.visible=PL.dist>0.85;   /* pegado a una pared no se ve a sí mismo */
  // cámara detrás, por encima del hombro; se acerca si hay una pared entre medias
  const ty=PL.crouch?1.15:1.55, cp=Math.cos(P.pitch), bx=sin*cp, bz=cos*cp, by=-Math.sin(P.pitch); let d=0.5;
  while(d<3.0){ const nx=P.x+bx*(d+0.3), nz=P.z+bz*(d+0.3), c=MAP[Math.floor(nz/T)]&&MAP[Math.floor(nz/T)][Math.floor(nx/T)]; if(!c||'#W'.indexOf(c)>=0||(('Tcg'.indexOf(c)>=0)&&ty+by*d<1.7))break; d+=0.2; }
  PL.dist+=(d-PL.dist)*Math.min(1,dt*(d<PL.dist?14:4)); const D_=PL.dist;
  camera.position.set(P.x+bx*D_+cos*0.38,Math.max(0.35,ty+by*D_),P.z+bz*D_-sin*0.38); }
// vista inicial y vistas fijas (teclas 1 a 4) para comparar con los renders de Blender
const VIEWS=[[3,11.4,-0.95,0.02],[18.4,18.0,0.9,0.04],[40.2,13.4,-1.75,0.03],[25,40,0.5,0.05]];
addEventListener('keydown',e=>{ const i=KP.open||(PL.p&&!e.altKey)?-1:['Digit1','Digit2','Digit3','Digit4'].indexOf(e.code); if(i>=0){ const v=VIEWS[i]; P.x=v[0]; P.z=v[1]; P.yaw=v[2]; P.pitch=v[3]; } });
if(Q.get('v')){ const v=VIEWS[(+Q.get('v')||1)-1]; P.x=v[0]; P.z=v[1]; P.yaw=v[2]; P.pitch=v[3]; }

addEventListener('resize',()=>{ camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth,innerHeight); if(composer)composer.setSize(innerWidth,innerHeight); });
let last=performance.now(), fpsT=0, fpsN=0, t=0;
// vigilancia de fluidez: si va por debajo de 27 fps baja la calidad por pasos (sombras del foco, resplandor, resolución, lluvia)
const PERF={t:0,n:0,bad:0,step:0,wait:5,k:0};
function perfTick(raw){ PERF.k++; SPOTS.forEach((L,i)=>{ if(L.castShadow&&(PERF.k+i*5)%10===0)L.shadow.needsUpdate=true; }); if(LOW||!locked)return; if(PERF.wait>0){ PERF.wait-=raw; return; } PERF.t+=raw; PERF.n++; if(PERF.t<2)return; const f=PERF.n/PERF.t; PERF.t=0; PERF.n=0; PERF.bad=f<27?PERF.bad+1:0; if(PERF.bad<2||PERF.step>=4)return; PERF.bad=0; PERF.step++; PERF.wait=3;
  if(PERF.step===1){ SPOTS.forEach(L=>{ L.castShadow=false; }); scene.traverse(o=>{ if(o.material){ (Array.isArray(o.material)?o.material:[o.material]).forEach(m=>{ m.needsUpdate=true; }); } }); }
  else if(PERF.step===2){ useBloom=false; }
  else { const pr=PERF.step===3?1:0.75; renderer.setPixelRatio(pr); renderer.setSize(innerWidth,innerHeight); if(composer){ if(composer.setPixelRatio)composer.setPixelRatio(pr); composer.setSize(innerWidth,innerHeight); } if(PERF.step===4)rainGeo.setDrawRange(0,RAIN_N); } }
function frame(now){ const raw=(now-last)/1000, dt=hold()?0:Math.min(0.1,raw); last=now; dlgTick(Math.min(0.1,raw));   /* mientras se lee o se habla, el mundo espera */ perfTick(raw); t+=dt; move(dt); fxTick(dt); rainTick(dt); spotTick(t); skyTick(dt,t); peopleTick(dt);
  if(finalPass)finalPass.uniforms.time.value=t; if(composer){ bloom.enabled=useBloom; composer.render(); } else renderer.render(scene,camera);
  fpsT+=raw; fpsN++; if(fpsT>0.5){ el('fps').textContent=Math.round(fpsN/fpsT)+' fps · '+Math.round(stats.tris/1000)+' mil triángulos · niebla '+scene.fog.density.toFixed(3)+' (F/G) · exposición '+(finalPass?finalPass.uniforms.exposure.value.toFixed(2):'1')+' (J/K)'; fpsT=0; fpsN=0; }
  requestAnimationFrame(frame); }
requestAnimationFrame(frame);
window.__ESC={DOGS,DOG,releaseDogs,dogTick,ROIG,roigLines,DLG,CELL,choose,pick,toCell,grab,cellUse,TIT,FIN,codec,dlgNext,callControl,startStory,msUse,ending,MUS,musTick,STEAM,SKY,skyTick,setPal,PALS,shade,hpTick,RADIO,radioTick,gObst,stepTo,goTo,openDoor,LIT,lampOff,spots,toss,PERF,gFire,setState,save,load,newGame,OBST,KP,kpKey,SND,MS,DOORS,PTS,msStep,MAP,shoot,useKey,reload,bodyC,blocked,NOISES,ALERT,PL,PEOPLE,GEAR,peopleTick,scene,camera,renderer,P,stats,M,isReady:()=>ready,spotTick,frameOnce:()=>{ move(0); if(composer)composer.render(); else renderer.render(scene,camera); }};
})();
