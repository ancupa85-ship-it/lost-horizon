'use strict';
// Lost Horizon: La Torre — nivel autocontenido (bloque 4 del GDD: patio, torre de vigilancia,
// centro de comunicaciones con el archivo en la primera planta y azotea con tirolina).
// Un solo archivo sobre Three.js r128. Coordenadas: x este, z sur, y arriba; 1 unidad = 1 m.
(function(){
if(!window.THREE){ document.body.innerHTML='<p style="color:#fff;font:20px monospace;padding:20px">No se pudo cargar Three.js.</p>'; return; }
const TEST=/[?&]test\b/.test(location.search);
const MUSIC_SRC={sigilo:'../assets/music/sigilo.mp3',accion:'../assets/music/accion.mp3'};
const $=id=>document.getElementById(id);
const clamp=(v,a,b)=>v<a?a:v>b?b:v, lerp=(a,b,t)=>a+(b-a)*t;
const angDiff=(a,b)=>{ let d=b-a; while(d>Math.PI)d-=2*Math.PI; while(d<-Math.PI)d+=2*Math.PI; return d; };
const dist2=(ax,az,bx,bz)=>Math.hypot(ax-bx,az-bz);

// ================================================================ RENDER
const cv=$('gl');
const renderer=new THREE.WebGLRenderer({canvas:cv,antialias:false,powerPreference:'high-performance'});
const GPU=(()=>{ try{ const c=renderer.getContext(); const e=c.getExtension('WEBGL_debug_renderer_info'); return e?String(c.getParameter(e.UNMASKED_RENDERER_WEBGL)):''; }catch(e){ return ''; } })();
const WEAK=!/gfx=full/.test(location.search)&&/swiftshader|llvmpipe|software|basic render/i.test(GPU);
let SCALE=WEAK?0.6:Math.min(devicePixelRatio||1,1.25);
renderer.shadowMap.enabled=!WEAK; renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const scene=new THREE.Scene(); scene.background=new THREE.Color(0x0a1019); scene.fog=new THREE.FogExp2(0x0a1019,0.022);
const camera=new THREE.PerspectiveCamera(62,1,0.1,170); camera.rotation.order='YXZ';
const grad=(()=>{ const c=document.createElement('canvas'); c.width=4; c.height=1; const x=c.getContext('2d'); ['#2a2a2a','#707070','#b8b8b8','#ffffff'].forEach((col,i)=>{ x.fillStyle=col; x.fillRect(i,0,1,1); }); const t=new THREE.CanvasTexture(c); t.minFilter=t.magFilter=THREE.NearestFilter; return t; })();
const toon=(c,o)=>new THREE.MeshToonMaterial(Object.assign({color:c,gradientMap:grad},o||{}));
// postproceso: contornos por profundidad y color (estética cel-shading de De Profundis)
let rt=null; const post=new THREE.ShaderMaterial({uniforms:{tD:{value:null},tZ:{value:null},res:{value:new THREE.Vector2(1,1)},near:{value:camera.near},far:{value:camera.far},hurt:{value:0}},
  vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.0,1.0);}',
  fragmentShader:`varying vec2 vUv;uniform sampler2D tD,tZ;uniform vec2 res;uniform float near,far,hurt;
  float lz(vec2 uv){float z=texture2D(tZ,uv).r*2.0-1.0;return (2.0*near*far)/(far+near-z*(far-near));}
  void main(){vec2 px=1.0/res;float d=lz(vUv);
    float dx=max(abs(lz(vUv+vec2(px.x,0.0))-d),abs(lz(vUv-vec2(px.x,0.0))-d));float dy=max(abs(lz(vUv+vec2(0.0,px.y))-d),abs(lz(vUv-vec2(0.0,px.y))-d));
    float e=step(0.02*d+0.04,max(dx,dy))*step(d,90.0);
    vec4 c=texture2D(tD,vUv);vec3 c1=texture2D(tD,vUv+vec2(px.x,0.0)).rgb;vec3 c2=texture2D(tD,vUv+vec2(0.0,px.y)).rgb;
    float le=step(0.3,max(length(c.rgb-c1),length(c.rgb-c2)))*step(d,50.0);
    vec3 col=c.rgb*(1.0-max(e,le*0.5)*0.9);
    float v=length(vUv-0.5);col*=1.0-0.55*v*v;col=mix(col,vec3(0.6,0.05,0.02),hurt*0.45);
    gl_FragColor=vec4(col,1.0);}`});
const postScene=new THREE.Scene(), postCam=new THREE.OrthographicCamera(-1,1,1,-1,0,1);
postScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2,2),post));
function resize(){ const w=innerWidth,h=innerHeight; renderer.setPixelRatio(SCALE); renderer.setSize(w,h,false); camera.aspect=w/h; camera.updateProjectionMatrix();
  const W=Math.max(1,Math.floor(w*SCALE)),H=Math.max(1,Math.floor(h*SCALE)); if(rt)rt.dispose(); rt=new THREE.WebGLRenderTarget(W,H); rt.texture.minFilter=rt.texture.magFilter=THREE.NearestFilter;
  rt.depthTexture=new THREE.DepthTexture(W,H); rt.depthTexture.type=THREE.UnsignedIntType; post.uniforms.tD.value=rt.texture; post.uniforms.tZ.value=rt.depthTexture; post.uniforms.res.value.set(W,H); }
addEventListener('resize',resize); resize();

const M={concrete:toon(0x80837b),concreteD:toon(0x5d615b),wall:toon(0x9a9a8c),metal:toon(0x57616b),rust:toon(0x6e4b33),wood:toon(0x7a5b36),crate:toon(0x4f5c3b),crateB:toon(0x6b5a3a),
  asphalt:toon(0x3d3e42),mud:toon(0x2c3024),water:toon(0x0d1a22),reed:toon(0x5b6a3c),fence:toon(0x9aa1a8,{transparent:true,opacity:0.55}),dark:toon(0x1d2024),paper:toon(0xece3c8),
  red:toon(0xa3271c),truck:toon(0x48553a),glass:toon(0x1b2a33),stripe:toon(0xc9a227),lampOn:new THREE.MeshBasicMaterial({color:0xffc070}),bible:toon(0x3a1d14)};

// luces: luna fría, ambiente y farolas de sodio
scene.add(new THREE.HemisphereLight(0x46578a,0x16160f,0.9));
scene.add(new THREE.AmbientLight(0x2a3350,0.45));
const moon=new THREE.DirectionalLight(0x9fb0e0,0.55); moon.position.set(-30,50,25); moon.target.position.set(0,0,0); scene.add(moon,moon.target);
if(renderer.shadowMap.enabled){ moon.castShadow=true; moon.shadow.mapSize.set(2048,2048); const sc=moon.shadow.camera; sc.left=-60; sc.right=60; sc.top=60; sc.bottom=-60; sc.near=1; sc.far=140; moon.shadow.bias=-0.0008; }

// ================================================================ MUNDO
const SOLID=[];
const BOXG=new THREE.BoxGeometry(1,1,1);
function box(x0,y0,z0,x1,y1,z1,mat,o){ o=o||{};
  const b={x0:Math.min(x0,x1),y0:Math.min(y0,y1),z0:Math.min(z0,z1),x1:Math.max(x0,x1),y1:Math.max(y0,y1),z1:Math.max(z0,z1),kind:o.kind||''};
  if(o.solid!==false)SOLID.push(b);
  if(mat){ const m=new THREE.Mesh(BOXG,mat); m.scale.set(b.x1-b.x0,b.y1-b.y0,b.z1-b.z0); m.position.set((b.x0+b.x1)/2,(b.y0+b.y1)/2,(b.z0+b.z1)/2);
    m.castShadow=o.cast!==false; m.receiveShadow=true; scene.add(m); b.mesh=m; }
  return b; }
const crate=(x0,z0,x1,z1,h,mat)=>{ const b=box(x0,0,z0,x1,h,z1,mat||M.crate,{kind:'crate'}); const s=box(x0+0.04,h-0.12,z0-0.01,x1-0.04,h-0.06,z1+0.01,M.dark,{solid:false,cast:false}); return b; };

// suelo: barro de marisma fuera, asfalto dentro de la base
box(-60,-1,-62,60,0,50,M.mud,{cast:false});
box(-36,0,-30,36,0.02,22,M.asphalt,{solid:false,cast:false});
{ const w=new THREE.Mesh(new THREE.PlaneGeometry(120,8),M.water); w.rotation.x=-Math.PI/2; w.position.set(0,0.03,46); scene.add(w);
  const w2=new THREE.Mesh(new THREE.PlaneGeometry(120,10),M.water); w2.rotation.x=-Math.PI/2; w2.position.set(0,0.03,-56); scene.add(w2); }
// límites invisibles del mapa
box(-61,-1,-62,-60,20,50,null); box(60,-1,-62,61,20,50,null); box(-61,-1,-63,61,20,-62,null); box(-61,-1,48,61,20,49,null);

// muralla perimetral (3,2 m) con portón al sur y valla rota al sureste
const WH=3.2;
box(-36.6,0,21.7,-3,WH,22.3,M.wall); box(3,0,21.7,24,WH,22.3,M.wall);
box(-3.6,0,21.6,-3,4.2,22.4,M.concreteD); box(3,0,21.6,3.6,4.2,22.4,M.concreteD);
box(-3,3.9,21.9,3,4.2,22.1,M.stripe,{solid:false});
box(-36.6,0,-30.6,-36,WH,22.3,M.wall); box(36,0,-30.6,36.6,WH,22.3,M.wall);
box(-36.6,0,-30.6,36.6,WH,-30,M.wall);
// valla metálica con agujero entre x 29 y 31
box(24,0,21.92,29,2.6,22.08,M.fence); box(31,0,21.92,36,2.6,22.08,M.fence);
for(let x=24;x<=36;x+=2.5){ if(x>28.6&&x<31.4)continue; box(x-0.06,0,21.9,x+0.06,2.7,22.1,M.metal,{solid:false}); }
box(28.8,1.9,21.95,29.2,2.6,22.05,M.fence,{solid:false}); box(30.8,1.6,21.95,31.2,2.6,22.05,M.fence,{solid:false});

// embarcadero y bote
box(-1.5,0,26,1.5,0.3,43,M.wood);
for(let z=27;z<43;z+=3){ box(-1.7,-0.5,z,-1.4,0.6,z+0.3,M.wood,{solid:false}); box(1.4,-0.5,z,1.7,0.6,z+0.3,M.wood,{solid:false}); }
const boat=new THREE.Group(); { const hull=new THREE.Mesh(BOXG,M.dark); hull.scale.set(2.2,0.6,5.5); hull.position.y=0.2; boat.add(hull);
  const bow=new THREE.Mesh(new THREE.ConeGeometry(1.1,1.6,4),M.dark); bow.rotation.x=-Math.PI/2; bow.rotation.y=Math.PI/4; bow.scale.set(1,1,0.35); bow.position.set(0,0.2,-3.4); boat.add(bow);
  boat.position.set(3.3,0,39.5); scene.add(boat); }

// torre de vigilancia (plataforma a 7 m) con escalera al norte
const TW={x0:-22,x1:-18,z0:6,z1:10,top:7};
[[TW.x0,TW.z0],[TW.x1-0.3,TW.z0],[TW.x0,TW.z1-0.3],[TW.x1-0.3,TW.z1-0.3]].forEach(([x,z])=>box(x,0,z,x+0.3,TW.top,z+0.3,M.metal));
box(TW.x0,6.7,TW.z0,TW.x1,TW.top,TW.z1,M.wood);
box(TW.x0,7,TW.z1-0.1,TW.x1,8.1,TW.z1,M.metal); box(TW.x1-0.1,7,TW.z0,TW.x1,8.1,TW.z1,M.metal); box(TW.x0,7,TW.z0,TW.x0+0.1,8.1,TW.z1,M.metal);
box(TW.x0,7,TW.z0,-20.6,8.1,TW.z0+0.1,M.metal); box(-19.4,7,TW.z0,TW.x1,8.1,TW.z0+0.1,M.metal);
[[TW.x0,TW.z0],[TW.x1-0.12,TW.z0],[TW.x0,TW.z1-0.12],[TW.x1-0.12,TW.z1-0.12]].forEach(([x,z])=>box(x,8.1,z,x+0.12,9.6,z+0.12,M.metal,{solid:false}));
box(TW.x0-0.3,9.6,TW.z0-0.3,TW.x1+0.3,9.8,TW.z1+0.3,M.rust,{solid:false});
box(-21.7,7,6.6,-20.9,7.75,7.3,M.wood,{solid:false}); box(-21.6,7.75,6.75,-21.15,7.8,7.1,M.bible,{solid:false});
box(-21.9,7,8.6,-21.1,7.5,9.4,M.crate,{solid:false}); // caja de dardos

// centro de comunicaciones: planta baja maciza, archivo en la 1ª planta (suelo 4 m), azotea a 8,3 m
const B={x0:-12,x1:12,z0:-22,z1:-10};
box(B.x0,0,B.z0,B.x1,4,B.z1,M.concrete);
box(5,0,-10.05,7,2.4,-9.98,M.dark,{solid:false}); box(-8,1.2,-10.05,-4,2.4,-9.98,M.glass,{solid:false}); box(8.5,1.2,-10.05,11,2.4,-9.98,M.glass,{solid:false});
// muros de la 1ª planta (puerta del archivo al sur, x -1..1)
box(B.x0,4,-10.3,-1,8,B.z1,M.wall); box(1,4,-10.3,B.x1,8,B.z1,M.wall); box(-1,6.2,-10.3,1,8,B.z1,M.wall);
box(B.x0,4,B.z0,B.x1,8,-21.7,M.wall); box(B.x0,4,B.z0,-11.7,8,B.z1,M.wall); box(11.7,4,B.z0,B.x1,8,B.z1,M.wall);
box(-8,5.2,-10.06,-4,6.6,-9.99,M.glass,{solid:false}); box(4,5.2,-10.06,8,6.6,-9.99,M.glass,{solid:false});
// azotea con escotilla en (-9,-19)
const HATCH={x0:-9.6,x1:-8.4,z0:-19.6,z1:-18.4};
box(B.x0,8,B.z0,B.x1,8.3,HATCH.z0,M.concreteD); box(B.x0,8,HATCH.z1,B.x1,8.3,B.z1,M.concreteD);
box(B.x0,8,HATCH.z0,HATCH.x0,8.3,HATCH.z1,M.concreteD); box(HATCH.x1,8,HATCH.z0,B.x1,8.3,HATCH.z1,M.concreteD);
box(-4,8.3,-14,-2,9.3,-12,M.metal); box(3,8.3,-20,5,9.5,-18.6,M.metal); // máquinas del aire: cobertura
box(6,8.3,-17.2,6.3,14,-16.9,M.metal); { const dish=new THREE.Mesh(new THREE.SphereGeometry(1.1,12,6,0,Math.PI*2,0,Math.PI/3),M.metal); dish.material.side=THREE.DoubleSide; dish.position.set(6.15,12.8,-16.6); dish.rotation.x=Math.PI/2.4; scene.add(dish); }
box(-0.3,8.3,-21.9,0.3,10.2,-21.3,M.metal); // poste de la tirolina
// interior del archivo
box(-11.7,4,-21,-11.1,6.2,-12,M.wood); box(11.1,4,-21,11.7,6.2,-12,M.wood);
box(-7,4,-20,-6.4,6.2,-14,M.wood); box(6.4,4,-20,7,6.2,-14,M.wood);
for(const sx of [-11.4,-6.7,6.7,11.4]) for(let y=4.6;y<6.2;y+=0.55) box(sx-0.32,y,-20.6,sx+0.32,y+0.3,-12.4,M.paper,{solid:false,cast:false});
box(2,4,-15.5,4,4.8,-14.5,M.wood); box(2.8,4.8,-15.2,3.3,4.82,-14.8,M.paper,{solid:false});
const SAFE=box(-0.7,4,-21.7,0.7,5.3,-21,M.metal);
const safeDoor=new THREE.Mesh(BOXG,M.concreteD); safeDoor.scale.set(1.2,1.1,0.08); safeDoor.geometry=BOXG;
const safePivot=new THREE.Group(); safePivot.position.set(-0.6,4.65,-20.96); safeDoor.position.set(0.6,0,0); safePivot.add(safeDoor); scene.add(safePivot);
box(0.25,4.8,-20.95,0.45,5.05,-20.9,M.stripe,{solid:false});
box(8.2,4,-20.3,8.9,4.4,-19.6,M.crate,{solid:false}); // munición
// balcón (4 m) delante del archivo y escalera exterior al este
box(B.x0,3.7,-10,15,4,-8,M.concreteD);
for(const x of [-11.8,-4,4,11.8]) box(x-0.15,0,-8.3,x+0.15,3.7,-8,M.concreteD);
box(B.x0,4,-8.1,12.5,5,-8,M.metal); box(B.x0,4,-10,B.x0+0.1,5,-8,M.metal); box(14.9,4,-10,15,5,-8,M.metal,{solid:true});
for(let i=1;i<=20;i++){ const z1=2-0.5*(i-1), z0=2-0.5*i; box(12.5,0,z0,15,0.2*i,z1,i%2?M.concreteD:M.concrete); }
box(15,0.2,-8,15.08,5,2,M.metal,{solid:false});
// anexo oeste (2,4 m) y cajas para subir
box(-20,0,-22,B.x0,2.4,-12,M.concreteD);
crate(-18,-11.95,-16.8,-10.75,0.9); crate(-16.8,-11.95,-15.6,-10.75,1.7,M.crateB);
// cajas y camión del patio
crate(-6,10,-4.8,11.2,1.0); crate(-4.8,10,-3.6,11.2,1.0,M.crateB); crate(-6,11.2,-4.8,12.4,2.0);
crate(8,12,10.4,13.2,1.2,M.crateB); crate(8,13.2,9.2,14.4,2.2);
crate(-14,0,-12,2,1.1); crate(-14,2,-13,3.2,2.0,M.crateB);
crate(20,6,22.4,7.2,1.0); crate(21.2,7.2,22.4,8.4,2.0,M.crateB);
crate(28,16,29.2,17.2,1.1); crate(29.2,16,31.6,17.2,2.0,M.crateB);
crate(-26,14,-24,16,1.2); crate(0,-6,2.4,-4.8,1.0,M.crateB); crate(-4,-7,-2.8,-5.8,2.0);
crate(-30,-6,-28,-4,1.1); crate(26,-14,28.4,-12.8,1.2);
box(17,0.4,-4,19.6,3.0,2,M.truck); box(17.2,0.4,2,19.4,2.6,4,M.truck); box(17.25,1.6,3.95,19.35,2.4,4.02,M.glass,{solid:false});
for(const [x,z] of [[16.9,-2.6],[19.7,-2.6],[16.9,0.8],[19.7,0.8],[16.9,3],[19.7,3]]){ const w=new THREE.Mesh(new THREE.CylinderGeometry(0.45,0.45,0.35,10),M.dark); w.rotation.z=Math.PI/2; w.position.set(x,0.45,z); scene.add(w); }
// barracones (decorado sólido) al oeste y al este del centro
box(-34,0,-26,-22,3.2,-16,M.concreteD); box(22,0,-26,34,3.2,-18,M.concreteD);
box(-34,3.2,-26.2,-22,3.5,-15.8,M.rust,{solid:false}); box(22,3.2,-26.2,34,3.5,-17.8,M.rust,{solid:false});

// farolas de sodio: zonas iluminadas (te ven desde más lejos)
const LAMPS=[], BEACON=[];
function lamp(x,z,y,r,wall){ if(!wall){ box(x-0.1,0,z-0.1,x+0.1,y,z+0.1,M.metal); }
  const bulb=new THREE.Mesh(new THREE.SphereGeometry(0.18,8,6),M.lampOn); bulb.position.set(x,y,z); scene.add(bulb);
  const L=new THREE.PointLight(0xffa24a,1.25,r*2.2,1.6); L.position.set(x,y-0.2,z); scene.add(L);
  LAMPS.push({x,z,y:wall?y-2.4:0,r}); }
lamp(2.6,20.6,4.6,7.5); lamp(2,5,5,7); lamp(11,-3,5,6.5); lamp(0,-9.6,6.6,4.5,true);
box(-0.3,6.5,-9.99,0.3,6.7,-9.7,M.metal,{solid:false});
lamp(0,-15.5,7.5,5,true); box(-0.02,7.5,-15.52,0.02,8,-15.48,M.dark,{solid:false}); // bombilla del archivo
{ const b=new THREE.PointLight(0xff2a1a,0.9,9,2); b.position.set(6.15,14.2,-17.05); scene.add(b); const m=new THREE.Mesh(new THREE.SphereGeometry(0.12,6,4),new THREE.MeshBasicMaterial({color:0xff3020})); m.position.copy(b.position); scene.add(m); BEACON.push(b,m); }

// juncos: esconderse agachado
const REEDS=[[29.5,25.5,3.4],[25,27,3],[33,27,3],[20,25,2.4],[-14,26,3.5],[-24,25,3],[-6,28,2.5],[8,29,2.6],[33,14,3],[33,6,2.6],[-33,10,2.6],[-6,-36,4],[6,-38,4],[0,-42,4]];
{ const g=new THREE.ConeGeometry(0.06,1.6,4); g.translate(0,0.8,0); const n=REEDS.reduce((s,r)=>s+Math.round(r[2]*r[2]*9),0);
  const im=new THREE.InstancedMesh(g,M.reed,n); const o=new THREE.Object3D(); let k=0; let seed=7; const rnd=()=>{ seed=(seed*16807)%2147483647; return seed/2147483647; };
  for(const [cx,cz,r] of REEDS){ const m=Math.round(r*r*9); for(let i=0;i<m;i++){ const a=rnd()*6.283, d=Math.sqrt(rnd())*r; o.position.set(cx+Math.cos(a)*d,0,cz+Math.sin(a)*d); o.rotation.set((rnd()-0.5)*0.4,rnd()*3,(rnd()-0.5)*0.4); const s=0.7+rnd()*0.7; o.scale.set(1,s,1); o.updateMatrix(); im.setMatrixAt(k++,o.matrix); } }
  im.count=k; scene.add(im); }
const inReeds=(x,z)=>REEDS.some(([cx,cz,r])=>dist2(x,z,cx,cz)<r);
const isLit=(x,y,z)=>LAMPS.some(l=>Math.abs(y-l.y)<2.5&&dist2(x,z,l.x,l.z)<l.r)||spotOn(x,y,z);

// escaleras de mano: punto de agarre (x,z), alturas y salida arriba
const LADDERS=[
  {name:'torre',x:-20,z:5.55,y0:0,y1:7,top:[-20,7,7.0],a:0},
  {name:'anexo',x:-12.45,z:-17,y0:2.4,y1:8.3,top:[-11.0,8.3,-17],a:Math.PI/2},
  {name:'balcon',x:10,z:-9.55,y0:4,y1:8.3,top:[10,8.3,-11],a:Math.PI},
  {name:'escotilla',x:-9,z:-19,y0:4,y1:8.3,top:[-9,8.3,-17.5],a:Math.PI,hatch:true}];
for(const L of LADDERS){ const g=new THREE.Group(); const h=L.y1-L.y0+(L.hatch?0:0.9);
  for(const s of [-0.28,0.28]){ const r=new THREE.Mesh(BOXG,M.metal); r.scale.set(0.05,h,0.05); r.position.set(s,h/2,0); g.add(r); }
  for(let y=0.3;y<h;y+=0.35){ const r=new THREE.Mesh(BOXG,M.metal); r.scale.set(0.56,0.04,0.04); r.position.set(0,y,0); g.add(r); }
  g.position.set(L.x+Math.sin(L.a)*0.3,L.y0,L.z+Math.cos(L.a)*0.3); g.rotation.y=L.a; scene.add(g); }
// tirolina: de la azotea a la marisma norte, por encima de la muralla
const ZIP={a:new THREE.Vector3(0,10.0,-21.6),b:new THREE.Vector3(0,2.3,-46)};
{ const g=new THREE.BufferGeometry().setFromPoints([ZIP.a,ZIP.b]); scene.add(new THREE.Line(g,new THREE.LineBasicMaterial({color:0x111111})));
  box(-0.15,0,-46.15,0.15,2.6,-45.85,M.wood,{solid:false}); }

// reflector de la torre
const spot=new THREE.SpotLight(0xf4f7ff,3.2,70,0.13,0.35,1.2); spot.position.set(-18.5,8.1,9.5); scene.add(spot,spot.target);
const spotHead=new THREE.Mesh(new THREE.CylinderGeometry(0.28,0.36,0.5,10),M.metal); spotHead.position.copy(spot.position); scene.add(spotHead);
const beamMat=new THREE.MeshBasicMaterial({color:0xdde6ff,transparent:true,opacity:0.07,depthWrite:false,blending:THREE.AdditiveBlending,side:THREE.DoubleSide});
const beam=new THREE.Mesh((()=>{ const g=new THREE.ConeGeometry(1,1,18,1,true); g.translate(0,-0.5,0); g.rotateX(-Math.PI/2); return g; })(),beamMat); scene.add(beam);
const SPOT_R=3.1;

// ================================================================ FÍSICA
const STEP=0.45, GRAV=13;
function hitBox(x,y,z,r,h){ for(const b of SOLID){ if(b.x0<x+r&&b.x1>x-r&&b.z0<z+r&&b.z1>z-r&&b.y0<y+h&&b.y1>y+0.001)return b; } return null; }
function hitTop(x,y,z,r,h){ let t=-1; for(const b of SOLID){ if(b.x0<x+r&&b.x1>x-r&&b.z0<z+r&&b.z1>z-r&&b.y0<y+h&&b.y1>y+0.001&&b.y1>t)t=b.y1; } return t; }
function floorAt(x,z,r,y){ let f=-50; for(const b of SOLID){ if(b.x0<x+r&&b.x1>x-r&&b.z0<z+r&&b.z1>z-r&&b.y1<=y+0.02&&b.y1>f)f=b.y1; } return f; }
function tryMove(e,nx,nz){ if(!hitBox(nx,e.y,nz,e.r,e.h)){ e.x=nx; e.z=nz; return true; }
  const t=hitTop(nx,e.y,nz,e.r,e.h); if(e.vy<=0.5&&t-e.y<=STEP&&!hitBox(nx,t+0.002,nz,e.r,e.h)){ e.x=nx; e.z=nz; e.y=t; e.vy=0; return true; } return false; }
function moveH(e,dx,dz){ const n=Math.max(1,Math.ceil(Math.hypot(dx,dz)/0.2)); let ok=true; for(let i=0;i<n;i++){ if(!tryMove(e,e.x+dx/n,e.z))ok=false; if(!tryMove(e,e.x,e.z+dz/n))ok=false; } return ok; }
function moveV(e,dt){ e.vy-=GRAV*dt; const ny=e.y+e.vy*dt; let fell=0;
  if(e.vy<=0){ const f=floorAt(e.x,e.z,e.r,e.y); if(ny<=f){ if(!e.onGround)fell=(e.peak!=null?e.peak:e.y)-f; e.y=f; e.vy=0; e.onGround=true; e.peak=null; } else { e.y=ny; e.onGround=false; if(e.peak==null||e.y>e.peak)e.peak=Math.max(e.peak==null?-99:e.peak,e.y); } }
  else { if(hitBox(e.x,ny,e.z,e.r,e.h)){ e.vy=0; } else e.y=ny; e.onGround=false; e.peak=Math.max(e.peak==null?-99:e.peak,e.y); }
  return fell; }
// rayo contra cajas sólidas (método de las losas); devuelve t o Infinity
function rayBox(o,d,b,tmax){ let t0=0,t1=tmax; for(const [oa,da,a0,a1] of [[o.x,d.x,b.x0,b.x1],[o.y,d.y,b.y0,b.y1],[o.z,d.z,b.z0,b.z1]]){ if(Math.abs(da)<1e-9){ if(oa<a0||oa>a1)return Infinity; continue; } let ta=(a0-oa)/da, tb=(a1-oa)/da; if(ta>tb){ const k=ta; ta=tb; tb=k; } if(ta>t0)t0=ta; if(tb<t1)t1=tb; if(t0>t1)return Infinity; } return t0; }
function rayWorld(o,d,tmax){ let best=tmax; for(const b of SOLID){ const t=rayBox(o,d,b,best); if(t<best)best=t; } return best; }
const _o=new THREE.Vector3(), _d=new THREE.Vector3();
function los(ax,ay,az,bx,by,bz){ _o.set(ax,ay,az); _d.set(bx-ax,by-ay,bz-az); const L=_d.length(); if(L<0.01)return true; _d.divideScalar(L); return rayWorld(_o,_d,L-0.05)>=L-0.05; }

// ================================================================ NAVEGACIÓN (rejilla de 1 m con varias alturas, para los guardias)
const NAV={nodes:[],cell:new Map()};
(function buildNav(){ const R=0.32;
  for(let gx=-49;gx<49;gx++) for(let gz=-60;gz<47;gz++){ const x=gx+0.5, z=gz+0.5; const hs=[0];
    for(const b of SOLID){ if(b.x0<=x&&b.x1>=x&&b.z0<=z&&b.z1>=z&&b.y1>0.01&&b.y1<12)hs.push(b.y1); }
    const list=[]; for(const h of hs){ if(list.some(n=>Math.abs(n.y-h)<0.05))continue; if(h===0&&hs.length>1&&floorAt(x,z,0.01,0.01)>0.01&&false)continue;
      if(hitBox(x,h+0.05,z,R,1.65))continue; if(floorAt(x,z,0.05,h)<h-0.05)continue;
      const n={i:NAV.nodes.length,x,y:h,z,gx,gz,nb:[]}; NAV.nodes.push(n); list.push(n); }
    if(list.length)NAV.cell.set(gx+','+gz,list); }
  const get=(gx,gz)=>NAV.cell.get(gx+','+gz)||[];
  for(const n of NAV.nodes){ for(const [dx,dz] of [[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]]){ for(const m of get(n.gx+dx,n.gz+dz)){ if(Math.abs(m.y-n.y)>0.45)continue;
      if(dx&&dz){ const a=get(n.gx+dx,n.gz).some(k=>Math.abs(k.y-n.y)<=0.45), c=get(n.gx,n.gz+dz).some(k=>Math.abs(k.y-n.y)<=0.45); if(!a||!c)continue; }
      const mx=(n.x+m.x)/2, mz=(n.z+m.z)/2, my=Math.max(n.y,m.y); if(hitBox(mx,my+0.05,mz,0.22,1.6))continue;
      n.nb.push(m.i); } } }
})();
function navNear(x,y,z){ let best=null,bd=1e9; const gx=Math.floor(x),gz=Math.floor(z);
  for(let r=0;r<=3&&!best;r++) for(let dx=-r;dx<=r;dx++) for(let dz=-r;dz<=r;dz++){ const l=NAV.cell.get((gx+dx)+','+(gz+dz)); if(!l)continue;
    for(const n of l){ if(n.y>y+0.6)continue; const d=Math.hypot(n.x-x,n.z-z)+Math.abs(n.y-y)*3; if(d<bd){ bd=d; best=n; } } }
  return best; }
function navPath(ax,ay,az,bx,by,bz){ const s=navNear(ax,ay,az), g=navNear(bx,by,bz); if(!s||!g)return null; if(s===g)return [[g.x,g.y,g.z]];
  const N=NAV.nodes, gs=new Float32Array(N.length).fill(1e9), from=new Int32Array(N.length).fill(-1), closed=new Uint8Array(N.length); const heap=[];
  const push=(i,f)=>{ heap.push([f,i]); let k=heap.length-1; while(k>0){ const p=(k-1)>>1; if(heap[p][0]<=heap[k][0])break; [heap[p],heap[k]]=[heap[k],heap[p]]; k=p; } };
  const pop=()=>{ const top=heap[0], last=heap.pop(); if(heap.length){ heap[0]=last; let k=0; for(;;){ const l=2*k+1,r=l+1; let m=k; if(l<heap.length&&heap[l][0]<heap[m][0])m=l; if(r<heap.length&&heap[r][0]<heap[m][0])m=r; if(m===k)break; [heap[m],heap[k]]=[heap[k],heap[m]]; k=m; } } return top; };
  const h=n=>Math.hypot(n.x-g.x,n.z-g.z)+Math.abs(n.y-g.y);
  gs[s.i]=0; push(s.i,h(s)); let it=0;
  while(heap.length&&it++<20000){ const [,i]=pop(); if(closed[i])continue; closed[i]=1; if(i===g.i)break; const n=N[i];
    for(const j of n.nb){ if(closed[j])continue; const m=N[j]; const c=gs[i]+Math.hypot(m.x-n.x,m.z-n.z)+Math.abs(m.y-n.y); if(c<gs[j]){ gs[j]=c; from[j]=i; push(j,c+h(m)); } } }
  if(from[g.i]<0)return null; const out=[]; for(let i=g.i;i!==s.i;i=from[i])out.push([N[i].x,N[i].y,N[i].z]); out.reverse();
  // suavizado: saltar nodos con línea directa al mismo nivel
  const sm=[]; let cur=[ax,ay,az]; let k=0; while(k<out.length){ let far=k; for(let j=out.length-1;j>k;j--){ if(Math.abs(out[j][1]-cur[1])<0.05&&out.slice(k,j+1).every(p=>Math.abs(p[1]-cur[1])<0.05)&&clearLine(cur,out[j])){ far=j; break; } } sm.push(out[far]); cur=out[far]; k=far+1; }
  return sm; }
function clearLine(a,b){ const L=Math.hypot(b[0]-a[0],b[2]-a[2]); const n=Math.ceil(L/0.4); for(let i=1;i<=n;i++){ const t=i/n; const x=lerp(a[0],b[0],t), z=lerp(a[2],b[2],t); if(hitBox(x,a[1]+0.05,z,0.34,1.6))return false; if(floorAt(x,z,0.05,a[1])<a[1]-0.05)return false; } return true; }

// ================================================================ PERSONAJES
const BODYG={};
function cyl(r0,r1,len,mat){ const k=r0+'_'+r1+'_'+len; if(!BODYG[k]){ const g=new THREE.CylinderGeometry(r1,r0,len,10); g.translate(0,-len/2,0); BODYG[k]=g; } const m=new THREE.Mesh(BODYG[k],mat); m.castShadow=true; return m; }
function makeFig(o){ const g=new THREE.Group(), root=new THREE.Group(); g.add(root);
  const mB=toon(o.body), mP=toon(o.pants), mS=toon(o.skin||0xc99472), mK=toon(0x18191b), mH=toon(o.hat);
  const hip=new THREE.Group(); hip.position.y=0.9; root.add(hip);
  const torso=cyl(0.17,0.23,0.62,mB); torso.position.y=0.62; hip.add(torso);
  const belt=new THREE.Mesh(BOXG,mK); belt.scale.set(0.38,0.07,0.28); belt.position.y=0.04; hip.add(belt);
  const head=new THREE.Group(); head.position.y=0.78; hip.add(head);
  const skull=new THREE.Mesh(new THREE.SphereGeometry(0.13,12,10),mS); skull.castShadow=true; head.add(skull);
  const eyes=new THREE.Mesh(BOXG,mK); eyes.scale.set(0.15,0.025,0.02); eyes.position.set(0,0.02,0.125); head.add(eyes);
  if(o.cap){ const c=new THREE.Mesh(new THREE.CylinderGeometry(0.14,0.145,0.09,12),mH); c.position.y=0.09; head.add(c); const br=new THREE.Mesh(BOXG,mH); br.scale.set(0.2,0.02,0.1); br.position.set(0,0.06,0.15); head.add(br); }
  if(o.band){ const c=new THREE.Mesh(new THREE.CylinderGeometry(0.135,0.135,0.05,12),mH); c.position.y=0.05; head.add(c); for(const s of [-1,1]){ const t=new THREE.Mesh(BOXG,mH); t.scale.set(0.03,0.025,0.26); t.position.set(s*0.035,-0.02,-0.2); t.rotation.x=-0.7; head.add(t); }
    const hair=new THREE.Mesh(new THREE.SphereGeometry(0.135,10,8,0,Math.PI*2,0,Math.PI/2.2),toon(0x2b2018)); hair.position.y=0.015; head.add(hair); }
  const arm=s=>{ const p=new THREE.Group(); p.position.set(s*0.27,0.58,0); hip.add(p); const u=cyl(0.06,0.055,0.58,mB); p.add(u); const hnd=new THREE.Mesh(new THREE.SphereGeometry(0.055,8,6),mS); hnd.position.y=-0.6; p.add(hnd); return p; };
  const leg=s=>{ const p=new THREE.Group(); p.position.set(s*0.11,0,0); hip.add(p); const u=cyl(0.09,0.08,0.43,mP); p.add(u); const k=new THREE.Group(); k.position.y=-0.42; p.add(k); const l=cyl(0.075,0.07,0.42,mP); k.add(l); const bt=new THREE.Mesh(BOXG,mK); bt.scale.set(0.13,0.1,0.24); bt.position.set(0,-0.43,0.04); k.add(bt); p.knee=k; return p; };
  const armL=arm(1), armR=arm(-1), legL=leg(1), legR=leg(-1);
  const gun=new THREE.Mesh(BOXG,mK); gun.scale.set(0.05,0.1,o.rifle?0.6:0.24); gun.position.set(0,-0.62,0.12); armR.add(gun);
  scene.add(g); return {g,root,hip,head,armL,armR,legL,legR,gun,ph:0}; }
function animFig(f,speed,dt,o){ o=o||{}; f.ph+=speed*dt*3.1; const amp=Math.min(1,speed/2.2)*0.75; const s=Math.sin(f.ph)*amp;
  const cr=o.crouch?1:0; f.hip.position.y=lerp(0.9,0.6,cr); f.hip.rotation.x=cr*0.3; f.root.rotation.set(0,0,0); f.root.position.set(0,0,0);
  f.legL.rotation.x=s-cr*1.15; f.legR.rotation.x=-s-cr*1.15; f.legL.knee.rotation.x=cr*1.6+Math.max(0,-Math.sin(f.ph))*amp*0.9; f.legR.knee.rotation.x=cr*1.6+Math.max(0,Math.sin(f.ph))*amp*0.9; f.armL.rotation.x=-s*0.8; f.armR.rotation.x=o.aim?-Math.PI/2+f.hip.rotation.x*-1:s*0.8;
  f.armL.rotation.z=0; f.armR.rotation.z=0; if(o.aim){ f.armL.rotation.x=-1.3; f.armL.rotation.z=-0.5; }
  f.head.rotation.y=o.look||0; }
function poseDown(f,dead){ f.root.rotation.set(-Math.PI/2,0,dead?0.3:0); f.root.position.set(0,0.2,-0.9); f.hip.position.y=0.9; f.hip.rotation.x=0; f.legL.rotation.x=0.1; f.legR.rotation.x=-0.1; f.legL.knee.rotation.x=0.2; f.legR.knee.rotation.x=0.4; f.armL.rotation.x=dead?-2.6:-0.2; f.armR.rotation.x=0.3; f.armL.rotation.z=0.3; f.armR.rotation.z=-0.3; f.head.rotation.y=dead?0.9:0.3; }
// iconos sobre la cabeza
function iconTex(txt,col){ const c=document.createElement('canvas'); c.width=64; c.height=64; const x=c.getContext('2d'); x.font='bold 50px monospace'; x.textAlign='center'; x.textBaseline='middle'; x.lineWidth=7; x.strokeStyle='#000'; x.strokeText(txt,32,34); x.fillStyle=col; x.fillText(txt,32,34); const t=new THREE.CanvasTexture(c); return t; }
const ICON={'!':new THREE.SpriteMaterial({map:iconTex('!','#ff3b2a'),depthTest:false}),'?':new THREE.SpriteMaterial({map:iconTex('?','#ffc23a'),depthTest:false}),'z':new THREE.SpriteMaterial({map:iconTex('z','#9fd0ff'),depthTest:false})};

// ================================================================ ESTADO
const S={mode:'menu',time:0,yaw:0,pitch:-0.12,aim:false,lethal:false,alarm:false,alarmT:0,alarms:0,base:'calma',baseT:0,
  kills:0,sleeps:0,hasFile:false,noteRead:false,bibleRead:false,codeTries:0,notes:[],flags:{},checkpoint:null,objective:0,mags:3,
  noise:null,searchT:0,lastSeen:null,seenT:99,spotT:0,spotOn:true,cut:null,exit:null,t0:0};
const P={x:0,y:0.3,z:38,vy:0,r:0.34,h:1.75,a:Math.PI,crouch:false,onGround:true,hp:100,hurtT:9,ammoL:10,ammoN:6,ladder:null,carry:null,lock:0,peak:null,speed:0,fig:null};
P.fig=makeFig({body:0x2a2f36,pants:0x23272d,hat:0x2c3a5a,band:true,skin:0xc08a68});
const GDEF=[
  {id:'centinela',post:[0,0,20.2],a:0,sweep:1.0},
  {id:'patio O',route:[[-10,0,14],[-10,0,-3],[4,0,-3],[4,0,14]]},
  {id:'patio E',route:[[26,0,15],[26,0,-6],[16,0,-6],[16,0,15]]},
  {id:'vigía',post:[-19.3,7,8.7],a:1.2,tower:true},
  {id:'balcón',route:[[-10,4,-9],[11,4,-9],[0,4,-9],[0,4,-14]]},
  {id:'azotea',route:[[-6,8.3,-11.5],[9,8.3,-11.5],[9,8.3,-20.5],[-6,8.3,-20.5]],reserve:true}];
const G=[];
function makeGuard(d,i){ const g={i,d,id:d.id,x:0,y:0,z:0,vy:0,r:0.3,h:1.75,a:d.a||0,onGround:true,peak:null,state:d.post?'post':'patrol',meter:0,path:null,pi:0,ri:0,wait:0,stuck:0,
  alive:true,sleep:0,sleepT:0,tranq:0,found:false,active:!d.reserve,shotT:1.5,target:null,lookT:0,speed:0,repath:0,fig:makeFig({body:0x4b5a35,pants:0x3e4a2c,hat:0x3b4a2a,cap:true,rifle:true}),icon:new THREE.Sprite(ICON['?'])};
  g.icon.scale.set(0.6,0.6,0.6); g.icon.visible=false; scene.add(g.icon); resetGuard(g); return g; }
function resetGuard(g){ const d=g.d, p=d.post||d.route[0]; g.x=p[0]; g.y=p[1]; g.z=p[2]; g.vy=0; g.a=d.a||0; g.state=d.post?'post':'patrol'; g.meter=0; g.path=null; g.ri=0; g.wait=0; g.alive=true; g.sleep=0; g.found=false; g.tranq=0; g.carried=false; g.active=!d.reserve; g.fig.g.visible=g.active; }
GDEF.forEach((d,i)=>G.push(makeGuard(d,i)));

// ================================================================ ENTRADA
const IN={f:0,s:0,run:false,aim:false,keys:new Set(),press:new Set()};
const pressed=k=>{ if(IN.press.has(k)){ IN.press.delete(k); return true; } return false; };
const KEYMAP={KeyE:'use',KeyF:'takedown',KeyQ:'mode',KeyR:'carry',KeyG:'throw',Space:'jump',KeyC:'crouch',ControlLeft:'crouch'};
addEventListener('keydown',e=>{ if(e.code==='Tab'){ e.preventDefault(); toggleNotes(); return; }
  if(S.mode==='keypad'){ keypadKey(e); return; }
  if(S.mode==='dialog'){ if(['KeyE','Space','Enter'].includes(e.code)){ e.preventDefault(); dlgNext(); } return; }
  if(e.code==='Space')e.preventDefault(); IN.keys.add(e.code); if(KEYMAP[e.code]&&!e.repeat)IN.press.add(KEYMAP[e.code]); });
addEventListener('keyup',e=>IN.keys.delete(e.code));
addEventListener('blur',()=>IN.keys.clear());
function readKeys(){ if(TEST&&IN.bot)return; const k=IN.keys; IN.f=(k.has('KeyW')||k.has('ArrowUp')?1:0)-(k.has('KeyS')||k.has('ArrowDown')?1:0); IN.s=(k.has('KeyD')||k.has('ArrowRight')?1:0)-(k.has('KeyA')||k.has('ArrowLeft')?1:0); IN.run=k.has('ShiftLeft')||k.has('ShiftRight'); }
let locked=false, NOLOCK=false;
cv.addEventListener('mousedown',e=>{ if(S.mode!=='play')return; if(!locked&&!TEST&&!NOLOCK){ cv.requestPointerLock(); return; } if(e.button===0)IN.press.add('shoot'); if(e.button===2)IN.aim=true; });
addEventListener('mouseup',e=>{ if(e.button===2)IN.aim=false; });
addEventListener('contextmenu',e=>e.preventDefault());
addEventListener('mousemove',e=>{ if(!locked||S.mode!=='play')return; S.yaw-=e.movementX*0.0022; S.pitch=clamp(S.pitch-e.movementY*0.0022,-0.95,0.7); });
document.addEventListener('pointerlockerror',()=>{ NOLOCK=true; toast('Sin captura de ratón: arrastra con el botón pulsado para mirar.',4); });
addEventListener('mousemove',e=>{ if(!NOLOCK||locked||S.mode!=='play'||!e.buttons)return; S.yaw-=e.movementX*0.004; S.pitch=clamp(S.pitch-e.movementY*0.004,-0.95,0.7); });
document.addEventListener('pointerlockchange',()=>{ locked=document.pointerLockElement===cv; if(!locked&&S.mode==='play'&&!TEST&&!NOLOCK){ S.mode='pause'; $('pause').hidden=false; IN.aim=false; } });

// ================================================================ AUDIO (sintetizador + banda sonora de Andres)
let AC=null; const music={};
function audioInit(){ if(AC)return; try{ AC=new (window.AudioContext||window.webkitAudioContext)(); }catch(e){}
  for(const k of ['sigilo','accion']){ const a=new Audio(MUSIC_SRC[k]); a.loop=true; a.volume=0; music[k]=a; a.play().catch(()=>{}); } }
function tone(f,d,type,vol,slide){ if(!AC)return; const o=AC.createOscillator(), g=AC.createGain(); o.type=type||'square'; o.frequency.value=f; if(slide)o.frequency.exponentialRampToValueAtTime(slide,AC.currentTime+d); g.gain.value=vol||0.08; g.gain.exponentialRampToValueAtTime(0.0001,AC.currentTime+d); o.connect(g).connect(AC.destination); o.start(); o.stop(AC.currentTime+d); }
function noise(d,vol,hp){ if(!AC)return; const n=AC.sampleRate*d, buf=AC.createBuffer(1,n,AC.sampleRate), ch=buf.getChannelData(0); for(let i=0;i<n;i++)ch[i]=(Math.random()*2-1)*(1-i/n); const s=AC.createBufferSource(); s.buffer=buf; const f=AC.createBiquadFilter(); f.type='highpass'; f.frequency.value=hp||400; const g=AC.createGain(); g.gain.value=vol; s.connect(f).connect(g).connect(AC.destination); s.start(); }
const SFX={shot:()=>{ noise(0.35,0.5,200); tone(90,0.25,'sawtooth',0.15,40); },dart:()=>{ noise(0.08,0.12,2500); },alert:()=>{ tone(880,0.12,'square',0.1); setTimeout(()=>tone(1320,0.25,'square',0.1),90); },
  hmm:()=>tone(520,0.25,'triangle',0.08,700),beep:()=>tone(1200,0.06,'square',0.05),err:()=>tone(160,0.3,'square',0.1),ok:()=>{ tone(880,0.1,'square',0.06); setTimeout(()=>tone(1320,0.2,'square',0.06),100); },
  hit:()=>noise(0.12,0.35,800),hurt:()=>tone(140,0.15,'sawtooth',0.12,70),choke:()=>noise(0.4,0.1,300),zip:()=>noise(2.5,0.15,1500),gshot:()=>{ noise(0.25,0.3,300); },clink:()=>{ tone(2400,0.05,'square',0.04); setTimeout(()=>tone(1900,0.06,'square',0.04),80); }};
function musicUpdate(dt){ if(!AC)return; const act=S.alarm||S.mode==='dead'?1:0; const silent=S.mode==='menu'||S.mode==='end'?0:1; const tgtS=silent*(1-act)*0.45, tgtA=silent*act*0.5;
  for(const [k,t] of [['sigilo',tgtS],['accion',tgtA]]){ const a=music[k]; if(!a)continue; a.volume=clamp(a.volume+clamp(t-a.volume,-dt*0.6,dt*0.6),0,1); } }

// ================================================================ INTERFAZ
let toastT=0;
function toast(t,s){ $('toast').textContent=t; $('toast').hidden=false; toastT=s||3; }
function addNote(t){ if(!S.notes.includes(t))S.notes.push(t); }
const OBJ=['Entra en la base: el portón tiene centinela; la valla del este, un agujero entre los juncos.',
  'Sube al archivo: primera planta del centro de comunicaciones (escalera exterior, balcón o la escotilla de la azotea).',
  'Abre la caja fuerte del archivo y coge el expediente ALEPH-07.',
  'Sal con el expediente: tirolina de la azotea (escotilla del archivo) o vuelve al bote del embarcadero.'];
function objText(){ let t=OBJ[S.objective]; if(S.objective===2){ if(S.noteRead&&!S.bibleRead)t+=' Pista: «pregúntale al profeta de qué huía» (la torre de vigilancia).'; if(S.bibleRead)t+=' Pista: Jonás 1,3.'; } return t; }
function setObjective(n){ if(n<=S.objective)return; S.objective=n; $('objT').textContent=objText(); }
function objTarget(){ if(S.objective===0)return [0,0,22]; if(S.objective===1)return [0,4,-10]; if(S.objective===2)return (S.noteRead&&!S.bibleRead)?[-20,7,8]:[0,4,-21]; return [0,8.3,-21.4]; }
function toggleNotes(){ const n=$('notes'); if(S.mode==='play'){ n.hidden=false; S.mode='notes'; $('nObj').textContent=objText(); $('nList').innerHTML=S.notes.length?S.notes.map(t=>'<li>'+t+'</li>').join(''):'<li>Nada todavía.</li>'; } else if(S.mode==='notes'){ n.hidden=true; S.mode='play'; } }
// diálogo tipo códec
let DLG=null;
const WHO={control:['CONTROL','140.85'],cuttlas:['CUTTLAS','pensamiento'],doc:['DOCUMENTO',''],fuente:['000.00','frecuencia sin asignar'],guard:['GUARDIA','']};
function say(lines,done){ DLG={lines:lines.slice(),done,i:0,shown:0}; S.mode='dialog'; $('codec').hidden=false; IN.aim=false; showLine(); }
function showLine(){ const [who,txt]=DLG.lines[DLG.i]; const w=WHO[who]||[who,'']; $('cWho').innerHTML=w[0]+(w[1]?'<small>'+w[1]+'</small>':''); $('codec').className=who==='doc'?'doc':who==='cuttlas'?'mind':who==='fuente'?'fuente':''; DLG.txt=txt; DLG.shown=0; $('cTxt').textContent=''; }
function dlgNext(){ if(!DLG)return; if(DLG.shown<DLG.txt.length){ DLG.shown=DLG.txt.length; $('cTxt').textContent=DLG.txt; return; } DLG.i++; if(DLG.i>=DLG.lines.length){ const d=DLG.done; DLG=null; $('codec').hidden=true; S.mode='play'; if(d)d(); return; } showLine(); }
$('codec').addEventListener('click',()=>dlgNext());
function dlgUpdate(dt){ if(!DLG||DLG.shown>=DLG.txt.length)return; DLG.shown=Math.min(DLG.txt.length,DLG.shown+dt*55); $('cTxt').textContent=DLG.txt.slice(0,Math.floor(DLG.shown)); }
// teclado de la caja fuerte
let kp='';
(function(){ const gr=$('kpGrid'); ['1','2','3','4','5','6','7','8','9','C','0','OK'].forEach(k=>{ const b=document.createElement('button'); b.textContent=k; b.onclick=()=>keypadPress(k); gr.appendChild(b); }); $('kpClose').onclick=()=>keypadClose(); })();
function keypadOpen(){ S.mode='keypad'; kp=''; $('keypad').hidden=false; $('kpScreen').textContent='____'; $('kpMsg').textContent=S.codeTries>=2?'Capítulo y versículo: dos cifras cada uno.':'Combinación de 4 cifras.'; IN.aim=false; }
function keypadClose(){ $('keypad').hidden=true; S.mode='play'; relock(); }
function keypadKey(e){ e.preventDefault(); if(/^Digit\d$|^Numpad\d$/.test(e.code))keypadPress(e.code.slice(-1)); else if(e.code==='Backspace')keypadPress('C'); else if(e.code==='Enter'||e.code==='NumpadEnter')keypadPress('OK'); else if(e.code==='KeyE'||e.code==='Escape')keypadClose(); }
function keypadPress(k){ if(k==='C'){ kp=''; } else if(k==='OK'){ checkCode(); return; } else if(kp.length<4){ kp+=k; SFX.beep(); } $('kpScreen').textContent=(kp+'____').slice(0,4); }
function checkCode(){ if(kp==='0103'){ SFX.ok(); $('keypad').hidden=true; S.mode='play'; openSafe(); return; }
  S.codeTries++; SFX.err(); kp=''; $('kpScreen').textContent='ERR!';
  if(S.codeTries>=2)$('kpMsg').textContent='Capítulo y versículo: dos cifras cada uno.'; else $('kpMsg').textContent='Combinación incorrecta.';
  if(S.codeTries%3===0){ $('kpMsg').textContent='¡Zumbador! Alguien lo habrá oído.'; makeNoise(0,4,-20,14,true); } }
function relock(){ if(!TEST&&!NOLOCK&&!locked&&S.mode==='play'){ try{ cv.requestPointerLock(); }catch(e){} } }

// ================================================================ INTERACCIONES
function interactions(){ const L=[];
  for(const l of LADDERS){ if(P.ladder)break; const dx=dist2(P.x,P.z,l.x,l.z), dt=dist2(P.x,P.z,l.top[0],l.top[2]);
    if(dx<0.85&&P.y>=l.y0-0.3&&P.y<l.y1-1.0)L.push({d:dx,label:'TREPAR',act:()=>grabLadder(l,false)});
    else if(dt<0.9&&Math.abs(P.y-l.y1)<0.35)L.push({d:dt,label:l.hatch?'BAJAR POR LA ESCOTILLA':'BAJAR POR LA ESCALERA',act:()=>grabLadder(l,true)}); }
  const near=(x,y,z,r)=>{ const d=dist2(P.x,P.z,x,z); return d<r&&Math.abs(P.y-y)<1.3?d:null; };
  let d;
  if((d=near(3,4,-15,1.6))!=null)L.push({d,label:'LEER LA NOTA',act:readNote});
  if((d=near(-21.3,7,7,1.5))!=null)L.push({d,label:'LEER LA BIBLIA',act:readBible});
  if(!S.flags.darts&&(d=near(-21.5,7,9,1.3))!=null)L.push({d,label:'COGER DARDOS',act:()=>{ S.flags.darts=1; P.ammoN+=4; toast('+4 dardos tranquilizantes'); SFX.clink(); }});
  if(!S.flags.ammo&&(d=near(8.55,4,-19.95,1.3))!=null)L.push({d,label:'COGER MUNICIÓN',act:()=>{ S.flags.ammo=1; P.ammoL+=6; P.ammoN+=2; toast('+6 balas, +2 dardos'); SFX.clink(); }});
  if(!S.hasFile&&(d=near(0,4,-20.5,1.4))!=null)L.push({d,label:'TECLADO DE LA CAJA FUERTE',act:keypadOpen});
  if((d=near(0,8.3,-21.3,1.6))!=null)L.push({d,label:'TIROLINA',act:useZip});
  if((d=near(2.2,0.3,39.5,1.8))!=null)L.push({d,label:'SUBIR AL BOTE',act:useBoat});
  // cuerpos
  if(!P.carry){ for(const g of G){ if(!g.active||g.alive&&!g.sleep||g.carried)continue; const dd=dist2(P.x,P.z,g.x,g.z); if(dd<1.6&&Math.abs(P.y-g.y)<0.8){ L.push({d:dd+0.5,label:'R · CARGAR CUERPO',key:'R'}); break; } } }
  // derribo
  const tg=takedownTarget(); if(tg)L.push({d:0,label:'F · '+(S.lethal?'CUCHILLO':'ESTRANGULAR'),key:'F'});
  L.sort((a,b)=>a.d-b.d); const top=L.find(x=>!x.key)||null; const show=L[0];
  $('prompt').hidden=!show||S.mode!=='play'; if(show)$('prompt').textContent=show.key?show.label:'E · '+show.label;
  if(pressed('use')&&top)top.act(); }
function grabLadder(l,fromTop){ P.ladder=l; P.vy=0; P.x=l.x; P.z=l.z; P.a=l.a+Math.PI; P.y=fromTop?l.y1-0.6:Math.max(P.y,l.y0); if(P.carry)dropBody(); P.crouch=false; P.h=1.75; }
function readNote(){ S.noteRead=true; addNote('Nota de M. Halloran: «He vuelto a cambiar la combinación. Si la olvidas, sube a la torre y pregúntale al profeta de qué huía.»');
  say([['doc','Nota a mano sobre la mesa: «Moya: he vuelto a cambiar la combinación de la caja. Si la olvidas, sube a la torre y pregúntale al profeta de qué huía. — M. H.»'],
       ['cuttlas',S.bibleRead?'El profeta que huía… Jonás. Y la Biblia de la torre estaba abierta por el capítulo 1, versículo 3.':'¿El profeta? En la torre de vigilancia tiene que haber algo.']],()=>{ $('objT').textContent=objText(); }); }
function readBible(){ S.bibleRead=true; addNote('Biblia del vigía, abierta por Jonás. Subrayado: «Pero Jonás se levantó para huir a Tarsis» (Jonás 1,3).');
  say([['doc','Una Biblia gastada, abierta por el libro de Jonás. Subrayado a lápiz: «Pero Jonás se levantó para huir a Tarsis, lejos de la presencia del Señor.» (Jonás 1,3)'],
       ['cuttlas',S.noteRead?'De qué huía el profeta: capítulo uno, versículo tres. Cero, uno, cero, tres.':'Alguien ha leído esto muchas veces. Tarsis… aquí.']],()=>{ $('objT').textContent=objText(); }); }
function openSafe(){ S.hasFile=true; S.flags.safeOpen=1; addNote('Expediente ALEPH-07: relación de sujetos del programa Lost Horizon. LH-07: Cuttlas, Andrew. Estado: en misión.');
  const extra=S.kills>0;
  say([['doc','PROGRAMA LOST HORIZON · FUENTE ALEPH-07 · Relación de sujetos.'],['doc','LH-01 a LH-06: BAJA.'],['doc','LH-07: CUTTLAS, ANDREW. Estado: EN MISIÓN. Recuperación programada: Tarsis, 14-XI-1983.'],
       ['cuttlas','…Esa fecha es hoy.'],['control','Cuttlas, no lo leas. Mete el expediente en la bolsa y sal de ahí. Ahora.'],
       ['fuente','No eres el primero que huye a Tarsis.'],
       ...(extra?[['control','Han encontrado lo que dejaste en el patio: hay un tirador nuevo en la azotea. Ojo al subir.']]:[['control','La base sigue tranquila. Azotea o bote, tú eliges.']])],
    ()=>{ setObjective(3); if(extra)spawnReserve(); saveCheckpoint(); });
  S.flags.safeT=0; }
function spawnReserve(){ for(const g of G){ if(g.d.reserve&&!g.active){ resetGuard(g); g.active=true; g.fig.g.visible=true; } } if(S.base==='calma')S.base='sospecha'; }
function useZip(){ if(!S.hasFile){ toast('Control: «Sin el expediente no te vas.»'); return; } if(P.carry)dropBody(); S.mode='cut'; S.cut={type:'zip',t:0}; SFX.zip(); $('bars').classList.add('on'); }
function useBoat(){ if(!S.hasFile){ toast('Control: «Sin el expediente no hay extracción.»'); return; } finish('bote'); }

// ================================================================ COMBATE Y SIGILO
function takedownTarget(){ if(P.ladder||P.carry)return null; let best=null,bd=1.5;
  for(const g of G){ if(!g.active||!g.alive||g.sleep||g.state==='alert')continue; const d=dist2(P.x,P.z,g.x,g.z); if(d>bd||Math.abs(P.y-g.y)>0.7)continue;
    const toP=Math.atan2(P.x-g.x,P.z-g.z); const behind=Math.abs(angDiff(g.a,toP))>1.75; if(!behind&&g.meter>0.5)continue; best=g; bd=d; }
  return best; }
function neutralize(g,lethal,how){ if(!g.alive||g.sleep)return; g.icon.visible=false; g.meter=0; g.path=null; g.tranq=0;
  if(lethal){ g.alive=false; g.state='dead'; S.kills++; } else { g.sleep=1; g.sleepT=how==='dart'?90:120; g.state='sleep'; S.sleeps++; }
  poseDown(g.fig,lethal); }
function wake(g){ g.sleep=0; g.state='search'; g.meter=0.4; g.target=[g.x,g.y,g.z]; g.searchT=12; g.path=null; g.found=false; if(S.base==='calma'){ S.base='sospecha'; } }
function doTakedown(){ const g=takedownTarget(); if(!g)return; P.lock=S.lethal?0.5:1.1; g.fig.g.position.set(g.x,g.y,g.z); P.a=g.a; if(S.lethal){ SFX.hit(); } else SFX.choke(); neutralize(g,S.lethal,'cqc'); }
function dropTakedownCheck(){ for(const g of G){ if(!g.active||!g.alive||g.sleep)continue; if(dist2(P.x,P.z,g.x,g.z)<1.25&&Math.abs(P.y-g.y)<0.6){ neutralize(g,S.lethal,'drop'); SFX.hit(); toast(S.lethal?'Derribo aéreo (letal)':'Derribo aéreo: dormido'); return true; } } return false; }
function shoot(){ if(P.ladder||P.carry||P.lock>0)return; const lethal=S.lethal; if(lethal?P.ammoL<=0:P.ammoN<=0){ SFX.err(); toast('Sin munición '+(lethal?'letal':'tranquilizante')+'. Q cambia de tipo.',2); return; }
  if(lethal)P.ammoL--; else P.ammoN--; lethal?SFX.shot():SFX.dart();
  const o=camera.position.clone(), d=new THREE.Vector3(); camera.getWorldDirection(d);
  const tMin=Math.max(0,camDist-0.6); let tw=rayWorld(o,d,80); let hit=null,ht=tw,head=false;
  for(const g of G){ if(!g.active||!g.alive||g.sleep)continue; const r=rayGuard(o,d,g); if(r&&r.t>tMin&&r.t<ht){ ht=r.t; hit=g; head=r.head; } }
  tracer(o,d,Math.min(ht,80),lethal);
  if(lethal){ makeNoise(P.x,P.y,P.z,38,true); }
  if(hit){ if(lethal){ neutralize(hit,true,'shot'); } else { if(head)neutralize(hit,false,'dart'); else { hit.tranq=1.2; if(hit.state!=='alert'){ hit.state='suspect'; hit.target=[P.x,P.y,P.z]; hit.wait=1.2; hit.meter=Math.max(hit.meter,0.5); } } }
    $('cross').classList.add('hit'); setTimeout(()=>$('cross').classList.remove('hit'),150); } }
function rayGuard(o,d,g){ // cabeza (esfera) y cuerpo (cilindro vertical)
  const hx=g.x, hy=g.y+1.66, hz=g.z; const ox=o.x-hx, oy=o.y-hy, oz=o.z-hz; const b=ox*d.x+oy*d.y+oz*d.z, c=ox*ox+oy*oy+oz*oz-0.17*0.17, disc=b*b-c;
  let best=null; if(disc>=0){ const t=-b-Math.sqrt(disc); if(t>0)best={t,head:true}; }
  const ax=o.x-g.x, az=o.z-g.z; const A=d.x*d.x+d.z*d.z, Bq=2*(ax*d.x+az*d.z), C=ax*ax+az*az-0.3*0.3, D=Bq*Bq-4*A*C;
  if(D>=0&&A>1e-6){ const t=(-Bq-Math.sqrt(D))/(2*A); const y=o.y+d.y*t; if(t>0&&y>g.y&&y<g.y+1.5&&(!best||t<best.t))best={t,head:false}; }
  return best; }
const tracers=[];
function tracer(o,d,len,lethal){ const a=o.clone().addScaledVector(d,Math.max(0,camDist-0.3)), b=o.clone().addScaledVector(d,len); const g=new THREE.BufferGeometry().setFromPoints([a,b]); const l=new THREE.Line(g,new THREE.LineBasicMaterial({color:lethal?0xffd080:0x9fdcff})); scene.add(l); tracers.push({l,t:0.07}); }
function makeNoise(x,y,z,r,loud){ for(const g of G){ if(!g.active||!g.alive||g.sleep||g.state==='alert')continue; if(Math.hypot(g.x-x,(g.y-y)*1.5,g.z-z)<r){ if(loud){ g.state='search'; g.target=[x,y,z]; g.searchT=12; g.path=null; g.wait=0.6; g.icon.material=ICON['?']; }
      else if(g.state!=='search'){ g.state='suspect'; g.target=[x,y,z]; g.wait=1.0; g.path=null; } } }
  if(loud&&S.base==='calma')S.base='sospecha'; }
function throwMag(){ if(S.mags<=0){ toast('No te quedan cargadores vacíos.',2); return; } const o=camera.position.clone(), d=new THREE.Vector3(); camera.getWorldDirection(d);
  const t=Math.min(rayWorld(o,d,camDist+12),camDist+12); const p=o.addScaledVector(d,t-0.1); const fy=Math.max(floorAt(p.x,p.z,0.05,p.y+0.1),0); S.mags--; SFX.clink();
  setTimeout(()=>{ SFX.clink(); makeNoise(p.x,fy,p.z,13,false); },350); toast('Cargador lanzado ('+S.mags+' restantes)',1.6); }
function dropBody(){ const g=P.carry; if(!g)return; P.carry=null; g.carried=false; g.x=P.x+Math.sin(P.a)*0.8; g.z=P.z+Math.cos(P.a)*0.8; if(hitBox(g.x,P.y+0.3,g.z,0.2,0.5)){ g.x=P.x; g.z=P.z; } g.y=Math.max(0,floorAt(g.x,g.z,0.2,P.y+0.5)); g.fig.g.position.set(g.x,g.y,g.z); g.fig.g.rotation.y=P.a; }
function playerVis(){ let v=1; if(P.crouch)v*=0.55; const lit=isLit(P.x,P.y,P.z); if(!lit)v*=0.5; if(P.crouch&&inReeds(P.x,P.z)&&P.y<0.5)v*=0.35; if(P.moving)v*=1.15; if(P.carry)v*=1.2; return {v,lit}; }
function guardSees(g,tx,ty,tz,range){ const dx=tx-g.x, dz=tz-g.z, dy=ty-(g.y+1.6); const d=Math.hypot(dx,dz); if(d>range)return 0;
  const ang=Math.abs(angDiff(g.a,Math.atan2(dx,dz))); const fov=d<2?1.4:0.95; if(ang>fov)return 0;
  const va=Math.atan2(dy,Math.max(0.1,d)); if(va>0.7||va<-0.95)return 0;
  if(!los(g.x,g.y+1.6,g.z,tx,ty,tz))return 0; return 1-d/range; }
function spotOn(x,y,z){ if(!S.spotOn)return false; const t=spot.target.position; return dist2(x,z,t.x,t.z)<SPOT_R&&Math.abs(y-t.y)<1.5; }

// ================================================================ JUGADOR
function playerUpdate(dt){
  if(P.lock>0){ P.lock-=dt; animFig(P.fig,0,dt,{crouch:true}); return; }
  if(pressed('mode')){ S.lethal=!S.lethal; SFX.beep(); }
  if(P.ladder){ const l=P.ladder; P.y+=IN.f*2.3*dt; P.speed=Math.abs(IN.f)*1.5;
    if(P.y>=l.y1){ P.y=l.y1; P.x=l.top[0]; P.z=l.top[2]; P.ladder=null; P.vy=0; P.onGround=true; P.peak=null; }
    else if(P.y<=l.y0&&IN.f<0){ P.y=l.y0; P.ladder=null; P.x=l.x+Math.sin(l.a)*0.15; P.z=l.z+Math.cos(l.a)*0.15; P.peak=null; }
    else if(pressed('jump')){ P.ladder=null; P.vy=1; P.x+=Math.sin(l.a)*0.2; P.z+=Math.cos(l.a)*0.2; }
    P.fig.g.position.set(P.x,P.y,P.z); P.fig.g.rotation.y=l.a+Math.PI; animFig(P.fig,P.speed,dt,{}); P.fig.armL.rotation.x=P.fig.armR.rotation.x=-2.6+Math.sin(P.fig.ph)*0.3; return; }
  if(pressed('crouch')){ if(P.crouch){ if(!hitBox(P.x,P.y+0.05,P.z,P.r,1.75))P.crouch=false; } else P.crouch=true; }
  P.h=P.crouch?1.1:1.75;
  S.aim=IN.aim&&!P.carry;
  const fx=-Math.sin(S.yaw), fz=-Math.cos(S.yaw), rx=Math.cos(S.yaw), rz=-Math.sin(S.yaw);
  let mx=IN.f*fx+IN.s*rx, mz=IN.f*fz+IN.s*rz; const ml=Math.hypot(mx,mz); if(ml>1){ mx/=ml; mz/=ml; }
  const run=IN.run&&!P.crouch&&!P.carry&&!S.aim&&IN.f>0;
  let sp=P.crouch?1.7:run?5.4:3.1; if(P.carry)sp=Math.min(sp,2.1); if(S.aim)sp*=0.6;
  P.moving=ml>0.05; P.running=run&&P.moving; P.speed=P.moving?sp:0;
  if(S.aim)P.a=S.yaw+Math.PI; else if(P.moving){ const ta=Math.atan2(mx,mz); P.a+=angDiff(P.a,ta)*Math.min(1,dt*12); }
  moveH(P,mx*sp*dt,mz*sp*dt);
  if(pressed('jump')&&P.onGround&&!P.carry){ if(P.crouch){ if(!hitBox(P.x,P.y+0.05,P.z,P.r,1.75)){ P.crouch=false; P.h=1.75; } } P.vy=5.3; P.onGround=false; P.peak=P.y; }
  const vyBefore=P.vy; const fell=moveV(P,dt);
  if(fell>1.4&&vyBefore<-4){ if(!dropTakedownCheck()&&fell>4.6){ hurt((fell-4.6)*22,'caída'); } }
  if(P.y<-5){ P.y=0; }
  if(pressed('takedown'))doTakedown();
  if(pressed('carry')){ if(P.carry)dropBody(); else { for(const g of G){ if(!g.active||g.alive&&!g.sleep||g.carried)continue; if(dist2(P.x,P.z,g.x,g.z)<1.6&&Math.abs(P.y-g.y)<0.8){ P.carry=g; g.carried=true; P.crouch=false; break; } } } }
  if(pressed('shoot')){ if(S.aim||TEST)shoot(); else toast('Clic derecho para apuntar.',1.4); }
  if(pressed('throw'))throwMag();
  P.noise=P.running?9:(P.moving&&!P.crouch?2.2:0);
  // figura
  const f=P.fig; f.g.position.set(P.x,P.y,P.z); f.g.rotation.y=P.a; animFig(f,P.speed,dt,{crouch:P.crouch,aim:S.aim}); f.gun.visible=S.aim;
  if(P.carry){ const g=P.carry; g.x=P.x; g.y=P.y; g.z=P.z; g.fig.g.position.set(P.x,P.y+1.45,P.z); g.fig.g.rotation.y=P.a+Math.PI/2; g.fig.root.rotation.set(0,0,Math.PI/2); g.fig.root.position.set(0.9,0,0); f.armL.rotation.x=-2.8; }
  // regeneración
  P.hurtT+=dt; if(P.hurtT>5&&P.hp<100)P.hp=Math.min(100,P.hp+7*dt);
  if(!S.flags.inside&&P.z<21.4&&Math.abs(P.x)<36&&P.z>-30){ S.flags.inside=1; setObjective(1); saveCheckpoint(); say([['cuttlas','Este patio… juraría que ya lo he cruzado. De noche. Descalzo.']]); }
  if(S.objective===1&&P.y>3.5&&P.y<6&&P.x>-11.7&&P.x<11.7&&P.z<-10.3&&P.z>-21.7){ setObjective(2); }
}
function hurt(n,why){ P.hp-=n; P.hurtT=0; SFX.hurt(); $('hurt').style.opacity=1; setTimeout(()=>$('hurt').style.opacity=0,180); post.uniforms.hurt.value=1; if(P.hp<=0&&S.mode==='play'){ P.hp=0; die(why); } }
function die(why){ S.mode='dead'; $('over').hidden=false; $('overTxt').textContent=why==='caída'?'Cuttlas no sobrevivió a la caída.':'Abatido en el patio de Tarsis. Control pierde la señal a las '+clock()+'.'; if(document.pointerLockElement)document.exitPointerLock(); }
function clock(){ const m=40+Math.floor(S.time/60); return '0'+(2+Math.floor(m/60))+':'+String(m%60).padStart(2,'0'); }

// ================================================================ GUARDIAS
function guardsUpdate(dt){
  const vis=playerVis(); let anySee=false;
  for(const g of G){ if(!g.active)continue;
    if(!g.alive){ if(!g.carried)g.fig.g.position.set(g.x,g.y,g.z); g.icon.visible=false; continue; }
    if(g.sleep){ g.sleepT-=dt; if(!g.carried)g.fig.g.position.set(g.x,g.y,g.z); g.icon.visible=true; g.icon.material=ICON.z; g.icon.position.set(g.x,g.y+0.7+Math.sin(S.time*2)*0.1,g.z); if(g.sleepT<=0&&!g.carried){ wake(g); g.fig.g.position.set(g.x,g.y,g.z); } continue; }
    if(g.tranq>0){ g.tranq-=dt; if(g.tranq<=0){ neutralize(g,false,'dart'); continue; } }
    // percepción
    const range=(vis.lit?20:12)*(S.base==='calma'?1:1.2)*(g.d.tower?1.25:1);
    const ty=P.y+(P.crouch?0.8:1.4); let see=guardSees(g,P.x,ty,P.z,range*Math.min(1.2,vis.v*1.6));
    if(g.d.tower&&S.spotOn&&spotOn(P.x,P.y,P.z)&&los(spot.position.x,spot.position.y,spot.position.z,P.x,ty,P.z)&&!(P.crouch&&inReeds(P.x,P.z)))see=Math.max(see,0.9);
    if(see>0){ const rate=(0.9+3.2*see)*(g.state==='suspect'||g.state==='search'?1.6:1)*(S.base==='calma'?1:1.3); g.meter=Math.min(1.2,g.meter+rate*dt); anySee=true; g.lastSeeT=0; g.target=[P.x,P.y,P.z]; }
    else { g.meter=Math.max(0,g.meter-(g.state==='alert'?0:0.22)*dt); g.lastSeeT=(g.lastSeeT||0)+dt; }
    if(g.meter>=1&&g.state!=='alert')raiseAlarm(g);
    else if(see>0&&g.meter>0.3&&(g.state==='patrol'||g.state==='post'||g.state==='return')){ g.state='suspect'; g.wait=1.4; g.path=null; SFX.hmm(); }
    // oído
    if(P.noise>0&&g.state!=='alert'&&g.state!=='suspect'&&Math.hypot(g.x-P.x,(g.y-P.y)*2,g.z-P.z)<P.noise){ g.state='suspect'; g.target=[P.x,P.y,P.z]; g.wait=0.8; g.path=null; SFX.hmm(); }
    // cuerpos a la vista
    if(g.state!=='alert'&&g.state!=='inspect'){ for(const o of G){ if(o===g||!o.active||o.found||o.carried||(o.alive&&!o.sleep))continue; const lit=isLit(o.x,o.y,o.z); if(guardSees(g,o.x,o.y+0.3,o.z,lit?15:8)>0){ g.state='inspect'; g.body=o; g.path=null; SFX.hmm(); break; } } }
    guardAct(g,dt,see>0);
    // figura e icono
    g.fig.g.position.set(g.x,g.y,g.z); g.fig.g.rotation.y=g.a;
    animFig(g.fig,g.speed,dt,{aim:g.state==='alert'&&see>0,look:g.state==='search'||g.state==='suspect'?Math.sin(S.time*1.6)*0.6:0});
    const ic=g.state==='alert'?'!':(g.state==='suspect'||g.state==='search'||g.state==='inspect'||g.meter>0.15)?'?':null;
    g.icon.visible=!!ic; if(ic){ g.icon.material=ICON[ic]; g.icon.position.set(g.x,g.y+2.25,g.z); }
  }
  // alarma global
  if(S.alarm){ if(anySee)S.alarmT=0; else S.alarmT+=dt; S.lastSeen=anySee?[P.x,P.y,P.z]:S.lastSeen;
    if(S.alarmT>14){ S.alarm=false; S.base='sospecha'; for(const g of G){ if(g.active&&g.alive&&!g.sleep&&g.state==='alert'){ g.state='search'; g.target=S.lastSeen||[g.x,g.y,g.z]; g.searchT=14; g.path=null; g.meter=0.2; } } toast('La alarma se apaga. Siguen buscando.',2.5); } }
}
function raiseAlarm(g){ g.state='alert'; g.meter=1.2; g.path=null; g.shotT=0.9; if(!S.alarm){ S.alarms++; SFX.alert(); S.lastAlarm={by:g.id,t:+S.time.toFixed(1),p:[+P.x.toFixed(1),+P.y.toFixed(1),+P.z.toFixed(1)],g:[+g.x.toFixed(1),+g.y.toFixed(1),+g.z.toFixed(1)],crouch:P.crouch,lit:isLit(P.x,P.y,P.z)}; } S.alarm=true; S.alarmT=0; S.base='sospecha'; S.lastSeen=[P.x,P.y,P.z];
  for(const o of G){ if(o===g||!o.active||!o.alive||o.sleep)continue; if(Math.hypot(o.x-P.x,o.z-P.z)<32){ o.state='alert'; o.meter=Math.max(o.meter,1); o.path=null; o.shotT=1.4+Math.random(); } } }
function goTo(g,tx,ty,tz,sp,dt){ // A* + seguimiento
  g.repath-=dt; if(!g.path||g.repath<=0){ g.path=navPath(g.x,g.y,g.z,tx,ty,tz)||[]; g.pi=0; g.repath=g.state==='alert'?1.2:6; }
  if(g.pi>=g.path.length){ g.speed=0; return true; }
  const p=g.path[g.pi]; const dx=p[0]-g.x, dz=p[2]-g.z, d=Math.hypot(dx,dz);
  if(d<0.35&&Math.abs(p[1]-g.y)<0.6){ g.pi++; return g.pi>=g.path.length; }
  const ta=Math.atan2(dx,dz); g.a+=angDiff(g.a,ta)*Math.min(1,dt*8); const ox=g.x, oz=g.z;
  moveH(g,dx/d*sp*dt,dz/d*sp*dt); g.speed=sp;
  if(Math.hypot(g.x-ox,g.z-oz)<sp*dt*0.3){ g.stuck+=dt; if(g.stuck>1.2){ g.stuck=0; g.path=null; g.repath=0; } } else g.stuck=0;
  return false; }
function guardAct(g,dt,seeing){ const d=g.d; moveV(g,dt); if(g.y<-2)g.y=0;
  const walk=S.base==='calma'?1.5:1.9;
  switch(g.state){
  case 'post': { g.speed=0; const pa=d.tower?Math.atan2(spot.target.position.x-g.x,spot.target.position.z-g.z):d.a+Math.sin(S.time*0.55+g.i)*(d.sweep||0.6); g.a+=angDiff(g.a,pa)*Math.min(1,dt*3);
    const p=d.post; if(dist2(g.x,g.z,p[0],p[2])>0.6){ g.state='return'; } break; }
  case 'patrol': { if(g.wait>0){ g.wait-=dt; g.speed=0; g.a+=Math.sin(S.time*1.3)*dt*0.6; break; } const w=d.route[g.ri]; if(goTo(g,w[0],w[1],w[2],walk,dt)){ g.ri=(g.ri+1)%d.route.length; g.wait=1.6; g.path=null; } break; }
  case 'suspect': { const t=g.target||[P.x,P.y,P.z]; g.a+=angDiff(g.a,Math.atan2(t[0]-g.x,t[2]-g.z))*Math.min(1,dt*4); if(g.wait>0){ g.wait-=dt; g.speed=0; break; }
    if(d.tower||goTo(g,t[0],t[1],t[2],walk,dt)){ g.state='search'; g.searchT=4; g.path=null; } break; }
  case 'inspect': { const o=g.body; if(!o||o.carried||o.found||(o.alive&&!o.sleep)){ g.state='return'; g.path=null; break; }
    if(d.tower||goTo(g,o.x,o.y,o.z,walk*1.4,dt)||dist2(g.x,g.z,o.x,o.z)<1.3){ if(d.tower){ o.found=true; } else if(o.sleep){ o.sleepT=0; wake(o); o.fig.root.rotation.set(0,0,0); } else { o.found=true; }
      if(!o.alive){ S.base='sospecha'; makeNoise(g.x,g.y,g.z,30,true); toast('¡Hombre caído! La base está en guardia.',2.5); }
      g.state='search'; g.target=[g.x,g.y,g.z]; g.searchT=10; g.path=null; } break; }
  case 'search': { if(g.wait>0){ g.wait-=dt; g.speed=0; break; } const t=g.target||[g.x,g.y,g.z]; const arrived=d.tower||goTo(g,t[0],t[1],t[2],walk*1.5,dt);
    if(arrived){ g.speed=0; g.a+=dt*1.4; g.searchT-=dt; if(g.searchT<=0){ g.state='return'; g.path=null; } } break; }
  case 'return': { const p=d.post||d.route[g.ri]; if(d.tower||goTo(g,p[0],p[1],p[2],walk,dt)){ g.state=d.post?'post':'patrol'; g.path=null; g.wait=1; } break; }
  case 'alert': { const t=S.lastSeen||[P.x,P.y,P.z]; const dd=Math.hypot(P.x-g.x,P.z-g.z);
    if(seeing){ g.a+=angDiff(g.a,Math.atan2(P.x-g.x,P.z-g.z))*Math.min(1,dt*6); g.speed=0;
      if(dd>9&&!d.tower)goTo(g,P.x,P.y,P.z,3.6,dt); g.shotT-=dt; if(g.shotT<=0){ g.shotT=1.0+Math.random()*0.7; guardShoot(g,dd); } }
    else if(!d.tower){ if(goTo(g,t[0],t[1],t[2],3.8,dt)){ g.a+=dt*2; } } break; }
  }
}
function guardShoot(g,d){ SFX.gshot(); const o=new THREE.Vector3(g.x,g.y+1.45,g.z), dir=new THREE.Vector3(P.x-g.x,P.y+1.1-g.y-1.45,P.z-g.z).normalize(); const l=new THREE.Line(new THREE.BufferGeometry().setFromPoints([o,o.clone().addScaledVector(dir,d)]),new THREE.LineBasicMaterial({color:0xffe0a0})); scene.add(l); tracers.push({l,t:0.06});
  let p=0.7-d/40-(P.moving?0.15:0)-(P.crouch?0.1:0); if(Math.random()<clamp(p,0.1,0.75))hurt(11,'disparo'); }

// ================================================================ REFLECTOR
function spotUpdate(dt){ const op=G[3]; S.spotOn=op.active&&op.alive&&!op.sleep; spot.visible=beam.visible=S.spotOn; spotHead.material=S.spotOn?M.lampOn:M.metal;
  const t=spot.target.position;
  if(S.spotOn){ if(op.state==='alert'||op.state==='suspect'){ t.x+=(P.x-t.x)*Math.min(1,dt*2.5); t.z+=(P.z-t.z)*Math.min(1,dt*2.5); t.y=Math.max(0,floorAt(t.x,t.z,0.1,P.y+0.5)); }
    else { S.spotT+=dt; const tx=5+19*Math.sin(S.spotT*0.33), tz=9+6*Math.sin(S.spotT*0.51+1); t.x+=(tx-t.x)*Math.min(1,dt*3); t.z+=(tz-t.z)*Math.min(1,dt*3); t.y=0; } }
  spot.target.updateMatrixWorld(); const L=spot.position.distanceTo(t); beam.position.copy(spot.position); beam.lookAt(t); beam.scale.set(SPOT_R*0.9,SPOT_R*0.9,L); spotHead.lookAt(t); }

// ================================================================ CÁMARA
let camDist=3.4;
function updateCamera(dt){ const aim=S.aim; const tx=P.x, ty=P.y+(P.crouch?1.05:1.55)-(P.carry?0:0), tz=P.z;
  const D=aim?1.9:3.4, sh=aim?0.8:0.5;
  const cy=Math.cos(S.pitch); const bx=Math.sin(S.yaw)*cy, by=-Math.sin(S.pitch), bz=Math.cos(S.yaw)*cy;
  const rx=Math.cos(S.yaw), rz=-Math.sin(S.yaw);
  const ox=tx+rx*sh, oz=tz+rz*sh; let base=[ox,ty,oz]; if(hitBox(ox,ty-0.1,oz,0.12,0.2))base=[tx,ty,tz];
  let d=D; for(let s=0.2;s<=D;s+=0.1){ if(hitBox(base[0]+bx*s,base[1]+by*s-0.1,base[2]+bz*s,0.15,0.2)){ d=Math.max(0.3,s-0.25); break; } }
  camDist+=(d-camDist)*(d<camDist?1:Math.min(1,(dt||0.016)*6));
  camera.position.set(base[0]+bx*camDist,base[1]+by*camDist,base[2]+bz*camDist); camera.rotation.set(S.pitch,S.yaw,0);
  camera.fov+=((aim?48:62)-camera.fov)*Math.min(1,(dt||0.016)*8); camera.updateProjectionMatrix(); }
function zipUpdate(dt){ const c=S.cut; c.t+=dt; const k=Math.min(1,c.t/3.4), e=k*k*(3-2*k); const p=ZIP.a.clone().lerp(ZIP.b,e);
  P.x=p.x; P.y=p.y-2.0; P.z=p.z; P.fig.g.position.set(P.x,P.y,P.z); P.fig.g.rotation.y=Math.PI; P.fig.armL.rotation.x=P.fig.armR.rotation.x=-2.9; P.fig.legL.rotation.x=0.3; P.fig.legR.rotation.x=0.1;
  camera.position.set(P.x+4,P.y+2.5,P.z+6); camera.lookAt(P.x,P.y+1,P.z); if(k>=1&&c.t>4)finish('tirolina'); }

// ================================================================ PUNTOS DE CONTROL Y FINALES
function snapshot(){ return JSON.stringify({P:{x:P.x,y:P.y,z:P.z,a:P.a,hp:Math.max(P.hp,60),ammoL:P.ammoL,ammoN:P.ammoN},S:{yaw:S.yaw,kills:S.kills,sleeps:S.sleeps,hasFile:S.hasFile,noteRead:S.noteRead,bibleRead:S.bibleRead,codeTries:S.codeTries,notes:S.notes,flags:S.flags,objective:S.objective,mags:S.mags,time:S.time,alarms:S.alarms,base:S.base},
  G:G.map(g=>({x:g.x,y:g.y,z:g.z,a:g.a,alive:g.alive,sleep:g.sleep,sleepT:g.sleepT,active:g.active,found:g.found,ri:g.ri}))}); }
function saveCheckpoint(){ S.checkpoint=snapshot(); }
function restore(js){ const o=JSON.parse(js); Object.assign(P,o.P,{vy:0,ladder:null,carry:null,lock:0,crouch:false,h:1.75,hurtT:9,peak:null});
  Object.assign(S,o.S,{alarm:false,alarmT:0,cut:null,aim:false}); S.flags=Object.assign({},o.S.flags); S.notes=o.S.notes.slice();
  G.forEach((g,i)=>{ const q=o.G[i]; resetGuard(g); g.active=q.active; g.fig.g.visible=q.active; g.found=q.found; g.ri=q.ri;
    if(!q.alive||q.sleep){ g.x=q.x; g.y=q.y; g.z=q.z; g.a=q.a; if(!q.alive){ g.alive=false; g.state='dead'; } else { g.sleep=1; g.sleepT=Math.max(q.sleepT,20); g.state='sleep'; } poseDown(g.fig,!q.alive); }
    else if(g.d.route&&q.active){ g.x=q.x; g.y=q.y; g.z=q.z; g.a=q.a; } g.carried=false; g.icon.visible=false; });
  safePivot.rotation.y=S.flags.safeOpen?-1.9:0; $('objT').textContent=objText(); }
function newGame(){ Object.assign(S,{time:0,yaw:0,pitch:-0.12,lethal:false,alarm:false,alarmT:0,alarms:0,base:'calma',kills:0,sleeps:0,hasFile:false,noteRead:false,bibleRead:false,codeTries:0,notes:[],flags:{},objective:0,mags:3,cut:null,exit:null,spotT:0});
  Object.assign(P,{x:0,y:0.3,z:38,vy:0,a:Math.PI,crouch:false,h:1.75,hp:100,hurtT:9,ammoL:10,ammoN:6,ladder:null,carry:null,lock:0,peak:null});
  G.forEach(resetGuard); safePivot.rotation.y=0; $('objT').textContent=objText(); saveCheckpoint(); }
function finish(exit){ S.exit=exit; S.mode='end'; $('bars').classList.remove('on'); if(document.pointerLockElement)document.exitPointerLock();
  const t=Math.floor(S.time); $('endExit').textContent=exit==='tirolina'?'Saliste por la tirolina de la azotea, por encima de la muralla norte.':'Volviste al bote del embarcadero y te perdiste en la marisma.';
  const rows=[['Tiempo',Math.floor(t/60)+' min '+String(t%60).padStart(2,'0')+' s'],['Alarmas',S.alarms],['Muertos',S.kills],['Dormidos',S.sleeps],['Vía',S.kills?'letal':'no letal']];
  $('endStats').innerHTML=rows.map(r=>'<span>'+r[0]+'</span><span>'+r[1]+'</span>').join('');
  $('endMem').innerHTML=S.kills?'<b>RECUERDO · EL PROGRAMA</b><br>«Sujeto LH-07, cuarta sesión. Respuesta al estímulo: óptima. Remordimiento: no se observa.» Una sala blanca. Una voz de mujer que cuenta hacia atrás desde diez.'
    :'<b>RECUERDO · UNA VIDA</b><br>Una casa con persianas verdes. Alguien te llama desde la cocina por un nombre que no es Cuttlas. Elena. No recuerdas el resto, pero sabes que es tuyo.';
  const sor=S.alarms===0?'«Según los partes de la base, aquella noche no pasó nada. El expediente que me llegó en 2026 dice lo contrario.»':'«El parte de guardia del 14 de noviembre habla de un intruso, '+S.alarms+' alarma'+(S.alarms>1?'s':'')+' y ningún detenido. Nadie firmó el informe.»';
  $('endSor').innerHTML='<b>LAURA SOROLLA · 2026</b><br>'+(exit==='tirolina'?'«Un guardia juró que vio a un hombre bajar del cielo sobre la marisma. Lo apartaron del servicio al día siguiente.» ':'«Los registros de Rota anotan una lancha sin luces saliendo de las marismas a las '+clock()+'. Volvió al mar, como Jonás.» ')+sor;
  $('end').hidden=false; }

// ================================================================ BUCLE
function sim(dt){ S.time+=dt; readKeys(); playerUpdate(dt); guardsUpdate(dt); spotUpdate(dt); interactions();
  if(S.flags.safeOpen&&safePivot.rotation.y>-1.9)safePivot.rotation.y-=dt*2; }
function hud(dt){ $('hp').style.width=Math.max(0,P.hp)+'%'; $('hp').style.background=P.hp<35?'#ff4a3a':'';
  const m=$('mode'); m.className=S.lethal?'letal':'noletal'; m.textContent=S.lethal?'LETAL · '+P.ammoL:'DARDOS · '+P.ammoN;
  $('inv').textContent=(S.hasFile?'▣ Expediente  ':'')+'Cargadores vacíos: '+S.mags+(P.carry?'  · cargando cuerpo':'');
  const st=$('state'); const s=S.alarm?'alarma':G.some(g=>g.active&&g.alive&&!g.sleep&&(g.state==='search'||g.state==='inspect'))?'busqueda':S.base;
  st.className='hud '+s; st.textContent=s==='alarma'?'¡ALARMA! '+Math.max(0,Math.ceil(14-S.alarmT)):s==='busqueda'?'BÚSQUEDA':s==='sospecha'?'SOSPECHA':'CALMA';
  $('cross').hidden=!(S.aim&&S.mode==='play'); if(toastT>0){ toastT-=dt; if(toastT<=0)$('toast').hidden=true; }
  post.uniforms.hurt.value=Math.max(0,post.uniforms.hurt.value-dt*3); drawRadar(); }
// radar: plano cenital prerenderizado y girado con la cámara
const RAD=$('radar'), rctx=RAD.getContext('2d'), MAPC=document.createElement('canvas'); const MS=3, MX0=-40, MZ0=-50; MAPC.width=80*MS; MAPC.height=100*MS;
(function(){ const x=MAPC.getContext('2d'); x.fillStyle='#04120a'; x.fillRect(0,0,MAPC.width,MAPC.height); const bs=SOLID.filter(b=>b.y1>0.25&&b.y1<20&&b.x1-b.x0<60).sort((a,b)=>a.y1-b.y1);
  for(const b of bs){ const k=clamp(b.y1/9,0,1); x.fillStyle='rgb('+Math.round(30+60*k)+','+Math.round(80+110*k)+','+Math.round(50+60*k)+')'; x.fillRect((b.x0-MX0)*MS,(b.z0-MZ0)*MS,Math.max(1,(b.x1-b.x0)*MS),Math.max(1,(b.z1-b.z0)*MS)); }
  x.fillStyle='rgba(120,200,140,.25)'; for(const [cx,cz,r] of REEDS){ x.beginPath(); x.arc((cx-MX0)*MS,(cz-MZ0)*MS,r*MS,0,7); x.fill(); } })();
function drawRadar(){ const W=RAD.width, c=rctx, sc=W/44; c.save(); c.clearRect(0,0,W,W); c.beginPath(); c.rect(0,0,W,W); c.clip(); c.translate(W/2,W/2); c.rotate(S.yaw); c.scale(sc/MS,sc/MS); c.translate(-(P.x-MX0)*MS,-(P.z-MZ0)*MS); c.drawImage(MAPC,0,0); c.restore();
  c.save(); c.translate(W/2,W/2); c.rotate(S.yaw); c.scale(sc,sc); c.translate(-P.x,-P.z);
  for(const g of G){ if(!g.active)continue; const col=!g.alive?'#555':g.sleep?'#5aa0ff':g.state==='alert'?'#ff3b2a':(g.state==='suspect'||g.state==='search'||g.state==='inspect')?'#ffc23a':'#e6e6e6';
    if(g.alive&&!g.sleep){ c.fillStyle=g.state==='alert'?'rgba(255,60,40,.25)':'rgba(255,255,255,.12)'; c.beginPath(); c.moveTo(g.x,g.z); c.arc(g.x,g.z,10,Math.PI/2-g.a-0.95,Math.PI/2-g.a+0.95); c.closePath(); c.fill(); }
    c.fillStyle=col; c.beginPath(); c.arc(g.x,g.z,0.7,0,7); c.fill(); if(Math.abs(g.y-P.y)>2){ c.fillStyle='#fff'; c.font='2px monospace'; c.fillText(g.y>P.y?'▲':'▼',g.x+0.8,g.z-0.6); } }
  if(S.spotOn){ const t=spot.target.position; c.strokeStyle='rgba(220,230,255,.6)'; c.lineWidth=0.3; c.beginPath(); c.arc(t.x,t.z,SPOT_R,0,7); c.stroke(); }
  const o=objTarget(); c.fillStyle='#ffb347'; c.save(); c.translate(o[0],o[2]); c.rotate(Math.PI/4); c.fillRect(-0.8,-0.8,1.6,1.6); c.restore(); c.restore();
  // objetivo fuera del radar: flecha en el borde
  const dx=o[0]-P.x, dz=o[2]-P.z; const ry=S.yaw; const lx=dx*Math.cos(ry)-dz*Math.sin(ry), lz=dx*Math.sin(ry)+dz*Math.cos(ry); if(Math.max(Math.abs(lx),Math.abs(lz))>21){ const a=Math.atan2(lz,lx); c.fillStyle='#ffb347'; c.beginPath(); const R=W/2-8; c.arc(W/2+Math.cos(a)*R,W/2+Math.sin(a)*R,4,0,7); c.fill(); }
  c.fillStyle='#7dff9a'; c.beginPath(); c.moveTo(W/2,W/2-6); c.lineTo(W/2-4,W/2+4); c.lineTo(W/2+4,W/2+4); c.closePath(); c.fill();
  if(Math.abs(o[1]-P.y)>2){ c.fillStyle='#ffb347'; c.font='12px monospace'; c.fillText(o[1]>P.y?'objetivo ▲ arriba':'objetivo ▼ abajo',6,W-6); } }
// rendimiento: si va lento baja la resolución y quita sombras
let perfAcc=0,perfN=0;
function perf(dt){ perfAcc+=dt; perfN++; if(perfAcc>2.5){ const fps=perfN/perfAcc; perfAcc=0; perfN=0; if(fps<26&&S.mode==='play'){ if(renderer.shadowMap.enabled){ renderer.shadowMap.enabled=false; moon.castShadow=false; scene.traverse(o=>{ if(o.material)o.material.needsUpdate=true; }); } else if(SCALE>0.5){ SCALE=Math.max(0.5,SCALE-0.15); resize(); } } } }
let last=performance.now();
function frame(t){ requestAnimationFrame(frame); const dt=Math.min(0.05,(t-last)/1000); last=t; if(TEST&&IN.manual)return; step(dt); render(); }
function step(dt){ if(S.mode==='play'){ sim(dt); updateCamera(dt); } else if(S.mode==='cut'){ zipUpdate(dt); } else if(S.mode==='dialog'){ dlgUpdate(dt); updateCamera(dt); } else updateCamera(dt);
  for(let i=tracers.length-1;i>=0;i--){ tracers[i].t-=dt; if(tracers[i].t<=0){ scene.remove(tracers[i].l); tracers[i].l.geometry.dispose(); tracers.splice(i,1); } }
  const bl=Math.sin(performance.now()/300)>0.3; BEACON.forEach(o=>o.visible=bl);
  musicUpdate(dt); hud(dt); if(S.mode==='play')perf(dt); }
function render(){ renderer.setRenderTarget(rt); renderer.render(scene,camera); renderer.setRenderTarget(null); renderer.render(postScene,postCam); }

// ================================================================ MENÚS
function start(){ audioInit(); $('start').hidden=true; newGame(); if(!TEST)cv.requestPointerLock();
  say([['control','Cuttlas, aquí Control. Estás en el embarcadero sur de Tarsis. El expediente ALEPH-07 está en el archivo del centro de comunicaciones, en la primera planta.'],
       ['control','Un reflector barre el patio desde la torre de vigilancia. En el portón hay un centinela; la valla del este tiene un agujero entre los juncos.'],
       ['control','Entra, coge el expediente y sal: por la tirolina de la azotea o de vuelta a este bote. Cómo lo hagas es cosa tuya. Q cambia entre balas y dardos.'],
       ['cuttlas','Entendido. Tarsis… el nombre me suena a algo que no recuerdo.']]); }
$('btnGo').onclick=start;
$('btnResume').onclick=()=>{ $('pause').hidden=true; S.mode='play'; relock(); };
const retry=()=>{ $('over').hidden=true; $('pause').hidden=true; restore(S.checkpoint); S.mode='play'; relock(); };
const restart=()=>{ $('over').hidden=true; $('pause').hidden=true; $('end').hidden=true; start(); };
$('btnRetry').onclick=retry; $('btnRetryP').onclick=retry; $('btnRestart').onclick=restart; $('btnRestartP').onclick=restart; $('btnAgain').onclick=restart;
$('objT').textContent=objText(); updateCamera(0.016); requestAnimationFrame(frame);

// ganchos para las pruebas automáticas (?test)
window.__T={hurt,los,S,P,G,IN,LADDERS,SOLID,NAV,navPath,step,render,start,dlgNext,keypadPress,shoot,updateCamera,isLit,inReeds,hitBox,floorAt,saveCheckpoint,restore,get camDist(){ return camDist; },camera,spot,WEAK,GPU};
})();
