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
const lamps=[], spots=[], beams=[];
// los focos de las torres barren despacio a un lado y a otro
const UP=new THREE.Vector3(0,1,0), DOWN=new THREE.Vector3(0,-1,0);
function spotTick(t){ spots.forEach(s=>{ const d=s.d.clone().applyAxisAngle(UP,Math.sin(t*0.16+s.phase)*0.42); s.L.target.position.copy(s.p).add(d.clone().multiplyScalar(40)); s.L.target.updateMatrixWorld(); s.cone.position.copy(s.p).add(d.clone().multiplyScalar(s.len/2)); s.cone.quaternion.setFromUnitVectors(DOWN,d); }); beams.forEach(b=>{ b.uniforms.time.value=t; }); }
INFO.lights.forEach(l=>{ const p=B(l.pos), col=new THREE.Color(l.color[0],l.color[1],l.color[2]);
  if(l.kind==='POINT'&&l.name==='farola'){ const L=new THREE.PointLight(col,110,34,2); L.position.copy(p); scene.add(L); lamps.push(L);
    if(!LOW){ L.castShadow=true; L.shadow.mapSize.set(1024,1024); L.shadow.camera.near=0.25; L.shadow.camera.far=34; L.shadow.bias=-0.003; L.shadow.normalBias=0.05; L.shadow.autoUpdate=false; } /* la escena no se mueve: la sombra se calcula una vez */ halo(p,0xffa24a,2.6,0.95); halo(p,0xff9038,12,0.26); }
  else if(l.kind==='POINT'&&l.name==='aplique'){ if(!LOW){ const L=new THREE.PointLight(col,7,9,2); L.position.copy(p); scene.add(L); } halo(p,0xffb870,1.3,0.9); halo(p,0xffa860,5,0.3); }
  else if(l.kind==='POINT'&&l.name==='interior'){ const L=new THREE.PointLight(col,l.power/120*24,9.5,1.6); L.position.copy(p); scene.add(L); halo(p.clone().add(new THREE.Vector3(0,0.18,0)),0xffd9a0,0.9,0.9); }
  else if(l.kind==='SPOT'){ const d=B(l.dir).normalize(); const A=THREE.MathUtils.degToRad(6.5); const L=new THREE.SpotLight(0xcfe0ff,2600,110,A*1.9,0.9,1.4); L.position.copy(p); scene.add(L); scene.add(L.target);
    if(!LOW){ L.castShadow=true; L.shadow.mapSize.set(2048,2048); L.shadow.camera.near=2; L.shadow.camera.far=110; L.shadow.bias=-0.0006; L.shadow.normalBias=0.03; }
    const h1=halo(p,0xdde8ff,4.5,1), h2=halo(p,0xbfd4ff,16,0.4);
    // haz del foco en la niebla: varias capas anchas y tenues, sin borde, que se apagan con la distancia
    const len=70, cone=new THREE.Group();
    [[0.55,0.5],[1.0,0.3],[1.7,0.16],[2.6,0.09]].forEach(([w,k])=>{ const m=new THREE.Mesh(new THREE.ConeGeometry(Math.tan(A*w)*len,len,40,24,true),new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,side:THREE.DoubleSide,
      uniforms:{c:{value:new THREE.Color(0x9fb8e6)},k:{value:k},time:{value:0}},vertexShader:'varying float h; varying vec3 n; varying vec3 v; varying vec3 wp; void main(){ h=uv.y; n=normalize(normalMatrix*normal); vec4 mv=modelViewMatrix*vec4(position,1.0); v=normalize(-mv.xyz); wp=(modelMatrix*vec4(position,1.0)).xyz; gl_Position=projectionMatrix*mv; }',
      fragmentShader:'uniform vec3 c; uniform float k; uniform float time; varying float h; varying vec3 n; varying vec3 v; varying vec3 wp; void main(){ float e=pow(abs(dot(normalize(n),normalize(v))),3.2); float f=pow(h,2.6)*smoothstep(0.0,0.12,h)*smoothstep(1.0,0.985,h); float s=0.8+0.2*sin(wp.x*0.7+time*0.6)*sin(wp.z*0.5-time*0.4+wp.y); gl_FragColor=vec4(c*e*f*k*s*0.42,1.0); }'}));
      cone.add(m); beams.push(m.material); });
    scene.add(cone); spots.push({L,cone,p,d,len,phase:spots.length*2.1}); }
});
scene.add(new THREE.HemisphereLight(0x27344f,0x0b0906,0.36));
const moon=new THREE.DirectionalLight(0x8fa8d8,0.22); moon.position.set(-30,50,20); scene.add(moon);
const balizaHalo=[];

// ---------- lluvia: rayas que caen alrededor de la cámara
const RAIN_N=LOW?2000:4500, RAIN_R=22, RAIN_H=16; const rainGeo=new THREE.BufferGeometry(); const rp=new Float32Array(RAIN_N*6), rs=new Float32Array(RAIN_N);
for(let i=0;i<RAIN_N;i++){ const x=(Math.random()*2-1)*RAIN_R, z=(Math.random()*2-1)*RAIN_R, y=Math.random()*RAIN_H; rs[i]=17+Math.random()*9; rp.set([x,y,z,x+0.05,y+0.55,z],i*6); }
rainGeo.setAttribute('position',new THREE.BufferAttribute(rp,3));
const rain=new THREE.LineSegments(rainGeo,new THREE.LineBasicMaterial({color:0xc8d4e0,transparent:true,opacity:0.075,depthWrite:false,fog:true})); rain.frustumCulled=false; scene.add(rain);
function rainTick(dt){ const cx=camera.position.x, cz=camera.position.z; for(let i=0;i<RAIN_N;i++){ const d=rs[i]*dt; let y=rp[i*6+1]-d; if(y<0){ y+=RAIN_H; } rp[i*6+1]=y; const c=(MAP[Math.floor((cz+rp[i*6+2])/T)]||'')[Math.floor((cx+rp[i*6])/T)]; rp[i*6+4]=y+(y<INFO.HB+0.2&&'_zLVWDb'.indexOf(c||'.')>=0?0:0.55); } rainGeo.attributes.position.needsUpdate=true; rain.position.set(cx,0,cz); }   // bajo techo no llueve: la gota que cae sobre un edificio se queda sin trazo

// ---------- escena de Blender
const b64=s=>{ const bin=atob(s); const u=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i); return u.buffer; };
let ready=false; const stats={meshes:0,inst:0,tris:0};
// ---------- personas: mallas con esqueleto, reposo y andar; el equipo (casco, capote, arma) se cuelga del hueso que le toca
const GEAR=[], PEOPLE=[];
function fixPersona(m,n){ const tela=/suit|pants|boots/.test(n); m.roughness=tela?0.82:0.62; m.metalness=0; m.envMapIntensity=0.35; if(/casualsuit/.test(n))m.color.setScalar(1.2); if(m.transparent){ m.transparent=false; m.alphaTest=0.35; m.depthWrite=true; } }
function loadPeople(done){ const list=(D.info.people||[]).filter(q=>D.people&&D.people[q.name]); let left=list.length; if(!left)return done();
  list.forEach(q=>new THREE.GLTFLoader().parse(b64(D.people[q.name]),'',g=>{ const root=g.scene; root.position.set(q.pos[0],q.pos[2],-q.pos[1]); root.rotation.y=q.rz; scene.add(root);
    root.traverse(o=>{ if(o.isMesh){ o.frustumCulled=false; o.castShadow=true; o.receiveShadow=true; fixPersona(o.material,(o.material.name||'').replace(/\.\d+$/,'')); if(o.material.map)o.material.map.anisotropy=4; stats.tris+=(o.geometry.index?o.geometry.index.count:o.geometry.attributes.position.count)/3; } });
    const mixer=new THREE.AnimationMixer(root), acts={}; g.animations.forEach(c=>{ acts[c.name]=mixer.clipAction(c); }); if(acts.idle)acts.idle.play(); if(acts.down){ acts.down.setLoop(THREE.LoopOnce,1); acts.down.clampWhenFinished=true; } mixer.update(0); root.updateMatrixWorld(true);
    GEAR.filter(x=>x.who===q.name).forEach(x=>{ const b=root.getObjectByName(x.bone); if(b)b.attach(x.mesh); });
    const p={q,root,mixer,acts,i:0,yaw:q.rz,wps:(q.wps||[]).map(w=>[w[0]*T+T/2,w[1]*T+T/2])};
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
  gAct(p,'walk',(turning?0.5:1)*v/WALK_V); const s=Math.min((turning?0.25:1)*v*dt,d); r.x+=Math.sin(p.yaw)*s; r.z+=Math.cos(p.yaw)*s; return false; }
function goTo(p,tx,tz,v,dt){ const r=p.root.position, a=cellOf(r.x,r.z), b=cellOf(tx,tz); if((a[0]===b[0]&&a[1]===b[1])||!blocked(r.x,r.z,tx,tz,true))return stepTo(p,tx,tz,v,dt);
  p.pathT=(p.pathT||0)-dt; if(!p.path||p.pathT<=0||p.pathK!==b[0]+','+b[1]){ p.path=bfs(a,b); p.pathT=0.5; p.pathK=b[0]+','+b[1]; } if(!p.path||p.path.length<2){ gAct(p,'idle'); return true; }
  let n=p.path[1]; if(p.path.length>2&&n[0]===a[0]&&n[1]===a[1])n=p.path[2]; stepTo(p,n[0]*T+T/2,n[1]*T+T/2,v,dt); return false; }
function sees(p){ const r=p.root.position, dx=P.x-r.x, dz=P.z-r.z, d=Math.hypot(dx,dz), range=PL.crouch?10:16; if(d>range)return 0;
  let da=Math.atan2(dx,dz)-p.yaw; while(da>Math.PI)da-=2*Math.PI; while(da<-Math.PI)da+=2*Math.PI; if(Math.abs(da)>(p.state==='chase'?1.4:0.95)&&d>1.6)return 0;
  if(blocked(r.x,r.z,P.x,P.z,PL.crouch))return 0; return (0.3+1.5*(1-d/range))*(PL.crouch?0.6:1); }
function setState(p,st){ p.state=st; p.stT=0; p.q1.visible=st==='suspect'||st==='search'; p.q2.visible=st==='chase'; }
function resetStealth(){ PEOPLE.forEach(p=>{ if(p===PL.p)return; p.dead=false; p.found=false; p.meter=0; p.lost=0; p.path=null; const h=p.wps.length?p.wps[0]:[p.q.pos[0],-p.q.pos[1]]; p.root.position.x=h[0]; p.root.position.z=h[1]; p.i=p.wps.length>1?1:0; p.yaw=p.q.rz; p.root.rotation.y=p.yaw; setState(p,'patrol'); gAct(p,p.wps.length>1?'walk':'idle'); });
  const q=PL.p.q; P.x=q.pos[0]; P.z=-q.pos[1]; P.yaw=q.rz+Math.PI; P.pitch=-0.12; PL.yaw=q.rz; PL.crouch=PL.third; NOISE.r=0; }
function peopleTick(dt){ const live=PL.p&&!ALERT.caught; let top=0;
  if(ALERT.caught){ ALERT.caught-=dt; if(ALERT.caught<=0){ ALERT.caught=0; resetStealth(); } }
  PEOPLE.forEach(p=>{ p.mixer.update(dt); if(p===PL.p)return; if(!p.q1){ p.q1=mark('?','#ffd23a'); p.q2=mark('!','#ff3b2f'); p.root.add(p.q1); p.root.add(p.q2); p.state='patrol'; p.stT=0; p.meter=0; p.act=p.wps.length>1&&p.acts.walk?'walk':'idle'; p.home=p.wps.length?null:[p.q.pos[0],-p.q.pos[1]]; }
    const r=p.root.position; if(p.dead){ p.q1.visible=p.q2.visible=false; return; } const vis=live?sees(p):0; p.stT+=dt;
    if(live&&p.state!=='chase')PEOPLE.forEach(o=>{ if(!o.dead||o.found)return; const b=o.root.position, dx=b.x-r.x, dz=b.z-r.z, d=Math.hypot(dx,dz); if(d>13)return; let da=Math.atan2(dx,dz)-p.yaw; while(da>Math.PI)da-=2*Math.PI; while(da<-Math.PI)da+=2*Math.PI; if((Math.abs(da)>0.95&&d>2)||blocked(r.x,r.z,b.x,b.z,false))return;
      o.found=true; p.seen=[b.x,b.z]; p.meter=Math.max(p.meter,0.6); setState(p,'search'); ALERT.msg='¡HOMBRE CAÍDO! ¡DAD LA VOZ!'; ALERT.msgT=3; });
    if(vis>0){ p.meter=Math.min(1.2,p.meter+vis*dt*(p.state==='chase'?3:1.15)); p.seen=[P.x,P.z]; p.lost=0; } else { p.meter=Math.max(0,p.meter-dt*0.3); p.lost=(p.lost||0)+dt; }
    if(live&&p.state!=='chase')for(const N of [NOISE].concat(NOISES)){ if(!(N.r>0))continue; const d=Math.hypot(N.x-r.x,N.z-r.z); if(d<N.r*(blocked(r.x,r.z,N.x,N.z,false)?0.5:1)){ p.seen=[N.x,N.z]; if(p.state==='patrol'||p.state==='return')setState(p,'suspect'); } }
    if(live&&p.meter>=1&&p.state!=='chase'){ setState(p,'chase'); ALERT.msg='¡ALTO! ¡INTRUSO EN EL PATIO!'; ALERT.msgT=3; PEOPLE.forEach(o=>{ if(o!==p&&o!==PL.p&&o.state&&o.state!=='chase'&&Math.hypot(o.root.position.x-r.x,o.root.position.z-r.z)<30){ o.seen=p.seen.slice(); setState(o,'search'); } }); }
    else if(live&&p.meter>0.35&&p.state==='patrol')setState(p,'suspect');
    if(p.state==='patrol'){ if(p.wps.length>1&&p.acts.walk){ const w=p.wps[p.i]; if(stepTo(p,w[0],w[1],WALK_V,dt))p.i=(p.i+1)%p.wps.length; } else { gAct(p,'idle'); face(p,p.q.rz,dt,2); } }
    else if(p.state==='suspect'){ gAct(p,'idle'); if(p.seen)face(p,Math.atan2(p.seen[0]-r.x,p.seen[1]-r.z),dt,3); if(p.stT>1.6)setState(p,'search'); }
    else if(p.state==='search'){ if(!p.seen||goTo(p,p.seen[0],p.seen[1],1.6,dt)||p.stT>14){ gAct(p,'idle'); p.look=(p.look||0)+dt; p.yaw+=Math.sin(p.look*1.6)*dt*1.2; p.root.rotation.y=p.yaw; if(p.look>3.5){ p.look=0; setState(p,'return'); } } }
    else if(p.state==='chase'){ const d=Math.hypot(P.x-r.x,P.z-r.z); if(!live){ setState(p,'return'); } else if(vis>0&&d<1.25){ gAct(p,'idle'); ALERT.caught=3.2; ALERT.msg='CAPTURADO'; ALERT.msgT=3.2; }
      else { const tgt=p.lost<1.5?[P.x,P.z]:p.seen; goTo(p,tgt[0],tgt[1],2.3,dt); if(p.lost>6){ p.meter=0.3; setState(p,'search'); } } }
    else if(p.state==='return'){ const h=p.home||p.wps[p.i]; if(goTo(p,h[0],h[1],WALK_V,dt)||p.stT>40)setState(p,'patrol'); }
    top=Math.max(top,p.state==='chase'?2:(p.state==='suspect'||p.state==='search')?1:0); ALERT.meter=Math.max(ALERT.meter||0,p.state==='chase'?1:p.meter); });
  NOISE.r=0; NOISES.length=0; ALERT.level=top; if(ALERT.msgT>0)ALERT.msgT-=dt;
  const st=el('estado'); if(st){ st.hidden=!PL.p; st.className=['ok','sos','ale'][top]; el('estadoT').textContent=['SIGILO','SOSPECHA','ALERTA'][top]; el('estadoB').style.width=Math.round(Math.min(1,ALERT.meter||0)*100)+'%'; ALERT.meter=0;
    const m=el('aviso'); m.textContent=ALERT.msgT>0?ALERT.msg:''; m.className=ALERT.caught?'cap':''; } }
new THREE.GLTFLoader().parse(b64(D.glb),'',g=>{
  g.scene.updateMatrixWorld(true); const groups=new Map(), singles=[];
  g.scene.traverse(o=>{ if(!o.isMesh)return; const n=(o.material.name||'').replace(/\.\d+$/,'');
    const gm=/^gear_([a-z]+)_(head|spine_03|hand_r|pelvis)_/.exec(o.name||'');
    if(gm){ const c=new THREE.Mesh(o.geometry,M[n.slice(3)]||o.material); c.applyMatrix4(o.matrixWorld); c.castShadow=true; c.receiveShadow=true; scene.add(c); GEAR.push({who:gm[1],bone:gm[2],mesh:c}); stats.meshes++; return; }
    if(n.indexOf('lh_')===0&&M[n.slice(3)])o.material=M[n.slice(3)];
    else if(/^(cuttlas|ibarra|moya|peris)_/.test(n))fixPersona(o.material,n);
    else { const m=o.material; if(m.map)m.map.anisotropy=4; m.roughness=Math.min(1,(m.roughness||1)*0.72); if(m.emissiveMap||m.name.toLowerCase().indexOf('glass')>=0){ } m.envMapIntensity=0.7; }
    o.userData.noShadow=/street_lamp|wall_lamp/i.test(o.material.name||'')||['bombilla','foco','baliza','ventana_on'].indexOf(n.slice(3))>=0;
    const k=o.geometry.uuid+'|'+o.material.uuid; if(!groups.has(k))groups.set(k,[]); groups.get(k).push(o); });
  groups.forEach(list=>{ const o=list[0]; stats.tris+=(o.geometry.index?o.geometry.index.count:o.geometry.attributes.position.count)/3*list.length;
    if(list.length<3){ list.forEach(m=>{ const c=new THREE.Mesh(m.geometry,m.material); c.applyMatrix4(m.matrixWorld); c.castShadow=!m.userData.noShadow; c.receiveShadow=true; scene.add(c); stats.meshes++; }); return; }
    const im=new THREE.InstancedMesh(o.geometry,o.material,list.length); list.forEach((m,i)=>im.setMatrixAt(i,m.matrixWorld)); im.instanceMatrix.needsUpdate=true; im.frustumCulled=false; im.castShadow=!o.userData.noShadow; im.receiveShadow=true; scene.add(im); stats.meshes++; stats.inst+=list.length; });
  lamps.forEach(L=>{ if(L.castShadow)L.shadow.needsUpdate=true; });
  loadPeople(()=>{ ready=true; el('load').textContent='CLIC PARA ENTRAR'; el('intro').classList.add('ok'); });
},e=>{ el('load').textContent='No se pudo cargar la escena: '+(e&&e.message||e); });

// ---------- resplandor
let composer=null, bloom=null, useBloom=!LOW;
// El compositor trabaja en lineal y con margen (medio flotante); la última pasada hace el revelado: exposición, curva ACES, viñeta y grano.
const FINAL={uniforms:{tDiffuse:{value:null},exposure:{value:0.8},time:{value:0}},vertexShader:'varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
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
const solid=(x,y)=>{ if(x<0||y<0||x>=COLS||y>=ROWS)return true; return '#WTcgLVb'.indexOf(MAP[y][x])>=0; };
const P={x:0,z:0,yaw:0,pitch:0,vy:0,bob:0}; (function(){ let sx=2,sy=2; MAP.forEach((r,y)=>{ const i=r.indexOf('P'); if(i>=0){ sx=i; sy=y; } }); P.x=sx*T+T/2; P.z=sy*T+T/2; P.yaw=-2.2; })();
const keys={}; addEventListener('keydown',e=>{ keys[e.code]=true; if(e.code==='KeyB'&&composer){ useBloom=!useBloom; } if(e.code==='KeyH'){ el('hud').hidden=!el('hud').hidden; }
  if(e.code==='KeyF')scene.fog.density=Math.max(0.004,scene.fog.density-0.003); if(e.code==='KeyG')scene.fog.density=Math.min(0.09,scene.fog.density+0.003);
  if(finalPass){ const u=finalPass.uniforms.exposure; if(e.code==='KeyJ')u.value=Math.max(0.3,u.value-0.05); if(e.code==='KeyK')u.value=Math.min(2,u.value+0.05); } }); addEventListener('keyup',e=>{ keys[e.code]=false; });
let locked=false; const cv=renderer.domElement;
el('intro').addEventListener('click',()=>{ if(!ready)return; if(cv.requestPointerLock)cv.requestPointerLock(); el('intro').hidden=true; locked=true; });
document.addEventListener('pointerlockchange',()=>{ locked=document.pointerLockElement===cv; if(!locked&&!TOUCH){ el('intro').hidden=false; } });
addEventListener('mousemove',e=>{ if(document.pointerLockElement!==cv)return; const k=0.0022*(1-0.45*PL.aim); P.yaw-=e.movementX*k; P.pitch=Math.max(-1.3,Math.min(1.3,P.pitch-e.movementY*k)); });
// táctil: arrastrar la mitad derecha gira, la izquierda camina
const TOUCH='ontouchstart' in window; const touch={mx:0,mz:0,ids:{}};
if(TOUCH){ cv.addEventListener('touchstart',e=>{ for(const t of e.changedTouches)touch.ids[t.identifier]={x:t.clientX,y:t.clientY,left:t.clientX<innerWidth/2,ox:t.clientX,oy:t.clientY}; e.preventDefault(); },{passive:false});
  cv.addEventListener('touchmove',e=>{ for(const t of e.changedTouches){ const s=touch.ids[t.identifier]; if(!s)continue; if(s.left){ touch.mx=Math.max(-1,Math.min(1,(t.clientX-s.ox)/60)); touch.mz=Math.max(-1,Math.min(1,(t.clientY-s.oy)/60)); } else { P.yaw-=(t.clientX-s.x)*0.005; P.pitch=Math.max(-1.3,Math.min(1.3,P.pitch-(t.clientY-s.y)*0.005)); } s.x=t.clientX; s.y=t.clientY; } e.preventDefault(); },{passive:false});
  const end=e=>{ for(const t of e.changedTouches){ const s=touch.ids[t.identifier]; if(s&&s.left){ touch.mx=0; touch.mz=0; } delete touch.ids[t.identifier]; } }; cv.addEventListener('touchend',end); cv.addEventListener('touchcancel',end); }
// Con Cuttlas cargado se le maneja en tercera persona (V alterna con la cámara libre): C se agacha o se levanta, Mayús aprieta el paso.
const PL={p:null,third:false,crouch:false,act:'idle',yaw:0,dist:3.0,aim:0,aiming:false,eye:1.66};
// Primera persona: la pistola con silenciador a la vista; el botón derecho la sube a la línea de mira y cierra el campo.
const VM=new THREE.Group(); (function(){ scene.add(camera); camera.add(VM);
  // materiales con luz propia (matcap): el foco de la torreta no debe quemar el arma a un palmo de la cámara
  const mc=document.createElement('canvas'); mc.width=mc.height=64; const mx=mc.getContext('2d'), gr=mx.createRadialGradient(24,20,2,32,32,34); gr.addColorStop(0,'#fff'); gr.addColorStop(0.25,'#9a9a9a'); gr.addColorStop(0.7,'#4a4a4a'); gr.addColorStop(1,'#1c1c1c'); mx.fillStyle=gr; mx.fillRect(0,0,64,64);
  const mct=new THREE.CanvasTexture(mc), cap=c=>new THREE.MeshMatcapMaterial({color:c,matcap:mct,fog:false});
  const mG=cap(0x34373e), mS=cap(0x1e2024), mH=cap(0x2b2e36), mT=cap(0x1c2028);
  const add=(g,m,x,y,z,rx)=>{ const o=new THREE.Mesh(g,m); o.position.set(x,y,z); if(rx)o.rotation.x=rx; o.frustumCulled=false; VM.add(o); return o; }, B=(w,h,d)=>new THREE.BoxGeometry(w,h,d);
  add(B(0.028,0.034,0.2),mG,0,0,-0.1); add(B(0.026,0.022,0.17),mG,0,-0.026,-0.085); add(B(0.027,0.1,0.045),mG,0,-0.075,-0.012,0.22);
  add(B(0.008,0.006,0.05),mG,0,-0.056,-0.075); add(B(0.008,0.03,0.006),mG,0,-0.045,-0.1); add(B(0.006,0.014,0.01),mG,0,-0.045,-0.07,0.3);
  add(new THREE.CylinderGeometry(0.0175,0.0175,0.17,14),mS,0,0.002,-0.285,Math.PI/2);
  add(B(0.006,0.008,0.008),mG,0.0085,0.021,-0.008); add(B(0.006,0.008,0.008),mG,-0.0085,0.021,-0.008); add(B(0.004,0.008,0.008),mG,0,0.021,-0.192);
  add(B(0.03,0.004,0.06),mS,0,0.0175,-0.11);   // estrías de la corredera
  add(B(0.078,0.082,0.062),mH,0.003,-0.082,0.0,0.22); add(B(0.074,0.05,0.03),mH,0.0,-0.075,-0.042,0.22); add(B(0.022,0.022,0.07),mH,-0.036,-0.028,-0.03); add(B(0.02,0.02,0.05),mH,0.03,-0.05,-0.085,0.5);
  const fa=add(new THREE.CylinderGeometry(0.034,0.046,0.42,12),mT,0,0,0); const a=new THREE.Vector3(0.012,-0.11,0.03), b=new THREE.Vector3(0.11,-0.3,0.42); fa.position.copy(a).add(b).multiplyScalar(0.5); fa.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),a.clone().sub(b).normalize());
  VM.visible=false; })();
renderer.domElement.addEventListener('contextmenu',e=>e.preventDefault());
addEventListener('mousedown',e=>{ if(e.button===2)PL.aiming=true; }); addEventListener('mouseup',e=>{ if(e.button===2)PL.aiming=false; });

// Disparo: un tiro con silenciador por clic izquierdo. El rayo sale del centro de la vista; se oye a pocos metros y el impacto también hace ruido donde da.
const FX={flash:null,hits:[],ac:null}; (function(){ const m=new THREE.MeshBasicMaterial({color:0xffc27a,transparent:true,opacity:0.5,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide,fog:false}); const g=new THREE.Group();
  for(let i=0;i<3;i++){ const q=new THREE.Mesh(new THREE.PlaneGeometry(0.036,0.036),m); q.rotation.z=i*Math.PI/3; q.frustumCulled=false; g.add(q); } g.position.set(0,0.002,-0.385); g.visible=false; VM.add(g); FX.flash=g;
  const hm=new THREE.MeshBasicMaterial({color:0xffe2b0,fog:false}); for(let i=0;i<4;i++){ const h=new THREE.Mesh(new THREE.SphereGeometry(0.035,6,5),hm); h.visible=false; scene.add(h); FX.hits.push({m:h,t:0}); } })();
function pfft(){ try{ const AC=window.AudioContext||window.webkitAudioContext; if(!AC)return; const ac=FX.ac||(FX.ac=new AC()); const n=Math.floor(ac.sampleRate*0.16), buf=ac.createBuffer(1,n,ac.sampleRate), d=buf.getChannelData(0); for(let i=0;i<n;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/n,3);
    const src=ac.createBufferSource(); src.buffer=buf; const f=ac.createBiquadFilter(); f.type='bandpass'; f.frequency.value=1500; f.Q.value=0.7; const g=ac.createGain(); g.gain.value=0.5; src.connect(f); f.connect(g); g.connect(ac.destination); src.start(); }catch(e){} }
function shoot(){ if(!PL.p||ALERT.caught||PL.cd>0)return null; PL.cd=0.42; PL.kick=1; PL.flashT=0.045; FX.flash.rotation.z=Math.random()*3; pfft(); PL.shots=(PL.shots||0)+1;
  const o=new THREE.Vector3(), d=new THREE.Vector3(); camera.getWorldPosition(o); camera.getWorldDirection(d); NOISES.push({x:P.x,z:P.z,r:4.5}); let hit=null, who=null;
  for(let s=0.3;s<60&&!hit;s+=0.08){ const x=o.x+d.x*s, y=o.y+d.y*s, z=o.z+d.z*s; if(y<=0.02){ hit=[x,0.03,z]; break; } if(y>7)break;
    for(const p of PEOPLE){ if(p===PL.p||p.dead)continue; const r=p.root.position; if(y<1.86&&Math.hypot(x-r.x,z-r.z)<(y>1.5?0.17:0.3)){ who=p; hit=[x,y,z]; break; } }
    if(hit)break; const row=MAP[Math.floor(z/T)], c=row&&row[Math.floor(x/T)]; if(!c||'#WTLVb'.indexOf(c)>=0||('cg'.indexOf(c)>=0&&y<1.25))hit=[x-d.x*0.1,y-d.y*0.1,z-d.z*0.1]; }
  if(hit){ const h=FX.hits[PL.shots%FX.hits.length]; h.m.position.set(hit[0],hit[1],hit[2]); h.m.visible=true; h.t=0.14; }
  if(who){ who.dead=true; who.found=false; who.path=null; if(who.acts.down){ const a=who.acts[who.act], b=who.acts.down; b.reset(); b.play(); if(a)a.crossFadeTo(b,0.12,false); who.act='down'; } NOISES.push({x:hit[0],z:hit[2],r:5}); }
  else if(hit)NOISES.push({x:hit[0],z:hit[2],r:6});
  return who?who.q.name:(hit?'impacto':null); }
function fxTick(dt){ PL.cd=Math.max(0,(PL.cd||0)-dt); PL.kick=(PL.kick||0)*Math.max(0,1-dt*9); PL.flashT=(PL.flashT||0)-dt; FX.flash.visible=PL.flashT>0&&VM.visible; FX.hits.forEach(h=>{ if(h.t>0){ h.t-=dt; h.m.scale.setScalar(Math.max(0.05,h.t/0.14)); if(h.t<=0)h.m.visible=false; } }); }
addEventListener('mousedown',e=>{ if(e.button===0&&document.pointerLockElement===renderer.domElement)shoot(); });
function plAct(name){ const p=PL.p; if(!p||PL.act===name||!p.acts[name])return; const a=p.acts[PL.act], b=p.acts[name]; b.reset(); b.play(); if(a)a.crossFadeTo(b,0.22,false); PL.act=name; }
addEventListener('keydown',e=>{ if(e.code==='KeyV'&&PL.p){ PL.third=!PL.third; } if(e.code==='KeyC'&&PL.p){ PL.crouch=!PL.crouch; } });
function move(dt){ let f=(keys.KeyW||keys.ArrowUp?1:0)-(keys.KeyS||keys.ArrowDown?1:0)-touch.mz, s=(keys.KeyD||keys.ArrowRight?1:0)-(keys.KeyA||keys.ArrowLeft?1:0)+touch.mx; if(PL.p&&PL.third&&ALERT.caught){ f=0; s=0; } const l=Math.hypot(f,s); if(l>1){ f/=l; s/=l; }
  const third=PL.p&&PL.third, fast=keys.ShiftLeft||keys.ShiftRight;
  PL.aim+=((PL.aiming&&!third?1:0)-PL.aim)*Math.min(1,dt*11); const A=PL.aim; const fov=68-22*A; if(Math.abs(camera.fov-fov)>0.05){ camera.fov=fov; camera.updateProjectionMatrix(); }
  const sp=(third?(PL.crouch?0.78:(fast?1.85:1.12)):(PL.crouch?1.3:(fast?6.2:2.6))*(1-0.5*A))*dt; const sin=Math.sin(P.yaw), cos=Math.cos(P.yaw); const dx=(-sin*f+cos*s)*sp, dz=(-cos*f-sin*s)*sp; const R=0.32;
  const free=(x,z)=>!solid(Math.floor((x-R)/T),Math.floor((z-R)/T))&&!solid(Math.floor((x+R)/T),Math.floor((z-R)/T))&&!solid(Math.floor((x-R)/T),Math.floor((z+R)/T))&&!solid(Math.floor((x+R)/T),Math.floor((z+R)/T));
  if(free(P.x+dx,P.z))P.x+=dx; if(free(P.x,P.z+dz))P.z+=dz; if(l>0.05)P.bob+=dt*(fast?13:8.5);
  camera.rotation.set(0,0,0); camera.rotation.order='YXZ'; camera.rotation.y=P.yaw; camera.rotation.x=P.pitch;
  VM.visible=!third&&!!PL.p; const mira=el('mira'); if(mira)mira.hidden=!(A>0.6);
  if(!third){ PL.eye+=((PL.crouch?1.05:1.66)-PL.eye)*Math.min(1,dt*8); const lm=Math.min(1,l); camera.position.set(P.x,PL.eye+Math.sin(P.bob)*0.028*lm*(1-0.6*A),P.z);
    VM.position.set(0.17*(1-A)+Math.cos(P.bob*0.5)*0.005*lm*(1-A),-0.165*(1-A)-0.0255*A+Math.sin(P.bob)*0.006*lm*(1-0.7*A),-0.42+0.08*A); VM.rotation.set(0.02*(1-A)+(PL.kick||0)*0.16,0.07*(1-A),0); VM.position.z+=(PL.kick||0)*0.035; VM.position.y+=(PL.kick||0)*0.012;
    if(PL.p){ PL.p.root.visible=false; PL.p.root.position.set(P.x,PL.p.q.pos[2],P.z); if(l>0.05&&!PL.crouch){ NOISE.x=P.x; NOISE.z=P.z; NOISE.r=fast?9:3.2; } } return; }
  const p=PL.p, moving=l>0.05; if(moving){ const want=Math.atan2(dx,dz); let da=want-PL.yaw; while(da>Math.PI)da-=2*Math.PI; while(da<-Math.PI)da+=2*Math.PI; PL.yaw+=Math.max(-9*dt,Math.min(9*dt,da)); }
  if(moving&&!PL.crouch){ NOISE.x=P.x; NOISE.z=P.z; NOISE.r=fast?9:3.2; }
  plAct(moving?(PL.crouch?'sneak':'walk'):(PL.crouch?'idle':'stand')); if(p.acts.walk)p.acts.walk.timeScale=fast?1.65:1;
  p.root.position.set(P.x,p.q.pos[2],P.z); p.root.rotation.y=PL.yaw; p.root.visible=PL.dist>0.85;   /* pegado a una pared no se ve a sí mismo */
  // cámara detrás, por encima del hombro; se acerca si hay una pared entre medias
  const ty=PL.crouch?1.15:1.55, cp=Math.cos(P.pitch), bx=sin*cp, bz=cos*cp, by=-Math.sin(P.pitch); let d=0.5;
  while(d<3.0){ const nx=P.x+bx*(d+0.3), nz=P.z+bz*(d+0.3), c=MAP[Math.floor(nz/T)]&&MAP[Math.floor(nz/T)][Math.floor(nx/T)]; if(!c||'#W'.indexOf(c)>=0||(('Tcg'.indexOf(c)>=0)&&ty+by*d<1.7))break; d+=0.2; }
  PL.dist+=(d-PL.dist)*Math.min(1,dt*(d<PL.dist?14:4)); const D_=PL.dist;
  camera.position.set(P.x+bx*D_+cos*0.38,Math.max(0.35,ty+by*D_),P.z+bz*D_-sin*0.38); }
// vista inicial y vistas fijas (teclas 1 a 4) para comparar con los renders de Blender
const VIEWS=[[3,11.4,-0.95,0.02],[18.4,18.0,0.9,0.04],[40.2,13.4,-1.75,0.03],[25,40,0.5,0.05]];
addEventListener('keydown',e=>{ const i=['Digit1','Digit2','Digit3','Digit4'].indexOf(e.code); if(i>=0){ const v=VIEWS[i]; P.x=v[0]; P.z=v[1]; P.yaw=v[2]; P.pitch=v[3]; } });
if(Q.get('v')){ const v=VIEWS[(+Q.get('v')||1)-1]; P.x=v[0]; P.z=v[1]; P.yaw=v[2]; P.pitch=v[3]; }

addEventListener('resize',()=>{ camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth,innerHeight); if(composer)composer.setSize(innerWidth,innerHeight); });
let last=performance.now(), fpsT=0, fpsN=0, t=0;
function frame(now){ const dt=Math.min(0.05,(now-last)/1000); last=now; t+=dt; move(dt); fxTick(dt); rainTick(dt); spotTick(t); peopleTick(dt);
  if(finalPass)finalPass.uniforms.time.value=t; if(composer){ bloom.enabled=useBloom; composer.render(); } else renderer.render(scene,camera);
  fpsT+=dt; fpsN++; if(fpsT>0.5){ el('fps').textContent=Math.round(fpsN/fpsT)+' fps · '+Math.round(stats.tris/1000)+' mil triángulos · niebla '+scene.fog.density.toFixed(3)+' (F/G) · exposición '+(finalPass?finalPass.uniforms.exposure.value.toFixed(2):'1')+' (J/K)'; fpsT=0; fpsN=0; }
  requestAnimationFrame(frame); }
requestAnimationFrame(frame);
window.__ESC={shoot,blocked,NOISES,ALERT,PL,PEOPLE,GEAR,peopleTick,scene,camera,renderer,P,stats,M,isReady:()=>ready,spotTick,frameOnce:()=>{ move(0); if(composer)composer.render(); else renderer.render(scene,camera); }};
})();
