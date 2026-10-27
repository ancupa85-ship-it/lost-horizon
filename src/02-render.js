'use strict';
// ---------- RENDER: toon + contornos por postproceso
const gl=document.getElementById('gl'), hud=document.getElementById('hud'), hctx=hud.getContext('2d');
const renderer=new THREE.WebGLRenderer({canvas:gl,antialias:false,powerPreference:'high-performance'});
// detección de gráfica: por software (SwiftShader, llvmpipe…) o móvil/integrada → arrancar en modo ligero, salvo ?gfx=full
const GPU_INFO=(()=>{ try{ const c=renderer.getContext(); const ext=c.getExtension('WEBGL_debug_renderer_info'); return ext?String(c.getParameter(ext.UNMASKED_RENDERER_WEBGL)):''; }catch(e){ return ''; } })();
const GFX_FORCE=/gfx=full/.test(location.search);
const WEAK_GPU=!GFX_FORCE&&/swiftshader|llvmpipe|software|microsoft basic|mesa offscreen/i.test(GPU_INFO);
const MOBILE_GPU=!GFX_FORCE&&!WEAK_GPU&&(/mali|adreno|powervr|apple gpu|apple a\d|intel\(r\) (hd|uhd)|iris/i.test(GPU_INFO)||/android|iphone|ipad/i.test(navigator.userAgent));
renderer.setPixelRatio((WEAK_GPU||MOBILE_GPU)?1:Math.min(devicePixelRatio,1.25)); renderer.shadowMap.enabled=true; renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const scene=new THREE.Scene(); scene.background=new THREE.Color(0x070a12); scene.fog=new THREE.FogExp2(0x070a12,0.026);
const camera=new THREE.PerspectiveCamera(70,1,0.1,120); camera.rotation.order='YXZ'; scene.add(camera);
const grad=(()=>{const c=document.createElement('canvas');c.width=4;c.height=1;const x=c.getContext('2d');['#262626','#6a6a6a','#b4b4b4','#ffffff'].forEach((col,i)=>{x.fillStyle=col;x.fillRect(i,0,1,1);});const t=new THREE.CanvasTexture(c);t.minFilter=t.magFilter=THREE.NearestFilter;return t;})();
let rt=null, post=null, postScene=null, postCam=null, usePost=true;
function makePost(w,h){ if(rt)rt.dispose(); rt=new THREE.WebGLRenderTarget(w,h); rt.texture.minFilter=THREE.NearestFilter; rt.texture.magFilter=THREE.NearestFilter; rt.depthTexture=new THREE.DepthTexture(w,h); rt.depthTexture.type=THREE.UnsignedIntType;
  if(!post){ post=new THREE.ShaderMaterial({uniforms:{tD:{value:null},tZ:{value:null},res:{value:new THREE.Vector2(w,h)},near:{value:camera.near},far:{value:camera.far},hurt:{value:0},time:{value:0}},
    vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.0,1.0);}',
    fragmentShader:`varying vec2 vUv;uniform sampler2D tD,tZ;uniform vec2 res;uniform float near,far,hurt,time;
    float lz(vec2 uv){float z=texture2D(tZ,uv).r*2.0-1.0;return (2.0*near*far)/(far+near-z*(far-near));}
    void main(){vec2 px=1.0/res;float d=lz(vUv);
      float dx=max(abs(lz(vUv+vec2(px.x,0.0))-d),abs(lz(vUv-vec2(px.x,0.0))-d));float dy=max(abs(lz(vUv+vec2(0.0,px.y))-d),abs(lz(vUv-vec2(0.0,px.y))-d));
      float e=step(0.018*d+0.035,max(dx,dy));
      vec4 c=texture2D(tD,vUv);vec3 c1=texture2D(tD,vUv+vec2(px.x,0.0)).rgb;vec3 c2=texture2D(tD,vUv+vec2(0.0,px.y)).rgb;
      float le=step(0.34,max(length(c.rgb-c1),length(c.rgb-c2)))*step(d,60.0);
      float edge=max(e,le*0.55);vec3 col=c.rgb*(1.0-edge*0.92);
      float v=length(vUv-0.5);col*=1.0-0.5*v*v;col=mix(col,vec3(0.6,0.05,0.02),hurt*0.5);
      col*=0.96+0.04*step(0.5,fract(gl_FragCoord.y*0.5));
      gl_FragColor=vec4(col,1.0);}`});
    postScene=new THREE.Scene(); postCam=new THREE.OrthographicCamera(-1,1,1,-1,0,1); postScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2,2),post)); }
  post.uniforms.tD.value=rt.texture; post.uniforms.tZ.value=rt.depthTexture; post.uniforms.res.value.set(w,h); }
function resize(){ const w=gl.clientWidth,h=gl.clientHeight; renderer.setSize(w,h,false); camera.aspect=w/h; camera.updateProjectionMatrix(); hud.width=w; hud.height=h; const pr=renderer.getPixelRatio(); try{makePost(Math.floor(w*pr),Math.floor(h*pr));}catch(e){usePost=false;} }
addEventListener('resize',resize);

// texturas planas con pocos detalles: el cel-shading pide colores llanos y líneas
function flatTex(w,h,base,fn,rep){ const c=document.createElement('canvas');c.width=w;c.height=h;const x=c.getContext('2d'); x.fillStyle=base; x.fillRect(0,0,w,h); if(fn)fn(x,w,h); const t=new THREE.CanvasTexture(c); t.wrapS=t.wrapT=THREE.RepeatWrapping; t.magFilter=THREE.NearestFilter; if(rep)t.repeat.set(rep,rep); return t; }
const TEX={
  concrete:flatTex(64,64,'#7a7f7c',(x,w,h)=>{x.fillStyle='#6a6f6c';x.fillRect(0,0,w,h/2);x.fillStyle='#53585a';x.fillRect(0,h-5,w,5);x.fillRect(w/2-1,0,2,h);x.fillStyle='#8a8f8a';x.fillRect(6,10,12,3);x.fillRect(40,38,10,3);}),
  asphalt:flatTex(64,64,'#2d3136',(x,w,h)=>{x.fillStyle='#262a2e';x.fillRect(0,0,w/2,h/2);x.fillRect(w/2,h/2,w/2,h/2);x.fillStyle='#3a3f45';x.fillRect(10,20,8,3);x.fillRect(44,50,10,3);}),
  plaster:flatTex(64,64,'#b8ad92',(x,w,h)=>{x.fillStyle='#4a4236';x.fillRect(0,h*0.72,w,3);x.fillStyle='#8a7f68';x.fillRect(0,h*0.76,w,h*0.24);x.fillStyle='#a79c82';x.fillRect(8,12,20,8);}),
  floor:flatTex(64,64,'#5c6160',(x,w,h)=>{x.fillStyle='#3b3f3e';x.fillRect(0,0,w,2);x.fillRect(0,0,2,h);x.fillRect(w/2,0,2,h);x.fillRect(0,h/2,w,2);x.fillStyle='#676c6a';x.fillRect(6,6,10,10);}),
  wood:flatTex(64,64,'#8c5e2c',(x,w,h)=>{x.fillStyle='#4a2e12';for(let i=0;i<h;i+=16)x.fillRect(0,i,w,3);x.fillRect(0,0,3,h);x.fillRect(w-3,0,3,h);x.fillStyle='#a6753c';x.fillRect(8,6,20,4);}),
  olive:flatTex(64,64,'#4f5a3c',(x,w,h)=>{x.fillStyle='#2f3824';x.fillRect(0,h*0.62,w,h*0.38);x.fillStyle='#9fb0b8';x.fillRect(6,10,w-12,12);x.fillStyle='#1a1f14';x.fillRect(6,10,w-12,2);}),
  metal:flatTex(64,64,'#5b6468',(x,w,h)=>{x.fillStyle='#3b4347';x.fillRect(2,2,w-4,2);x.fillRect(2,2,2,h-4);x.fillRect(w-4,2,2,h-4);x.fillRect(2,h-4,w-4,2);x.fillStyle='#8a9398';x.fillRect(10,10,4,4);x.fillRect(w-14,h-14,4,4);}),
  door:flatTex(64,96,'#3e4a52',(x,w,h)=>{x.fillStyle='#232b31';x.fillRect(5,5,w-10,3);x.fillRect(5,5,3,h-10);x.fillRect(w-8,5,3,h-10);x.fillRect(5,h-8,w-10,3);x.fillStyle='#d8c060';x.fillRect(w-16,h/2-2,6,4);}),
  vault:flatTex(64,96,'#4a525a',(x,w,h)=>{x.fillStyle='#262c32';x.fillRect(3,3,w-6,4);x.fillRect(3,3,4,h-6);x.fillRect(w-7,3,4,h-6);x.fillRect(3,h-7,w-6,4);x.fillStyle='#1a1e22';x.fillRect(w/2-10,h/2-10,20,20);x.fillStyle='#2b9a4c';x.fillRect(w/2-4,h/2-4,8,8);x.fillStyle='#c33';x.fillRect(8,10,w-16,5);}),
  bars:flatTex(64,96,'rgba(0,0,0,0)',(x,w,h)=>{x.clearRect(0,0,w,h);x.fillStyle='#9aa2a8';for(let i=6;i<w;i+=12)x.fillRect(i,0,4,h);x.fillRect(0,h/2-2,w,4);}),
};
TEX.bars.wrapS=TEX.bars.wrapT=THREE.ClampToEdgeWrapping;
const toon=(o)=>new THREE.MeshToonMaterial(Object.assign({gradientMap:grad},o));
const M={ concrete:toon({map:TEX.concrete}), plaster:toon({map:TEX.plaster}), asphalt:toon({map:TEX.asphalt}), floor:toon({map:TEX.floor}), wood:toon({map:TEX.wood}), olive:toon({map:TEX.olive}), metal:toon({map:TEX.metal}),
  door:toon({map:TEX.door}), vault:toon({map:TEX.vault}), ceil:toon({color:0x5a5852}), bars:toon({map:TEX.bars,transparent:true,alphaTest:0.5}), dark:toon({color:0x202428}), skin:toon({color:0xe8b890}), boots:toon({color:0x1a1410}) };
TEX.asphalt.repeat.set(COLS,ROWS);
const box=new THREE.BoxGeometry(T,3,T), tall=new THREE.BoxGeometry(T,3.6,T);
const ground=new THREE.Mesh(new THREE.PlaneGeometry(COLS*T,ROWS*T),M.asphalt); ground.rotation.x=-Math.PI/2; ground.position.set(COLS*T/2,0,ROWS*T/2); scene.add(ground);
const dynamicDoors={};
function wallMesh(x,y,geo,mat,h){ const m=new THREE.Mesh(geo,mat); m.position.set(wx(x),h/2,wx(y)); scene.add(m); return m; }
function doorSlab(x,y,mat){ const horiz=sightT(x-1,y)&&sightT(x+1,y); const g=new THREE.BoxGeometry(horiz?T:0.3,3,horiz?0.3:T); const m=new THREE.Mesh(g,mat); m.position.set(wx(x),1.5,wx(y)); scene.add(m); return m; }
function frame(x,y){ const horiz=cell(x-1,y)==='W'||cell(x-1,y)==='#'; const g=new THREE.BoxGeometry(horiz?T:0.4,0.4,horiz?0.4:T); const m=new THREE.Mesh(g,M.dark); m.position.set(wx(x),2.8,wx(y)); scene.add(m); }
for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++){ const c=map[y][x];
  if(c==='#')wallMesh(x,y,tall,M.concrete,3.6);
  else if(c==='W'){ const inside=interior(x-1,y)||interior(x+1,y)||interior(x,y-1)||interior(x,y+1); wallMesh(x,y,box,inside?M.plaster:M.concrete,3); }
  else if(c==='T'){ const m=new THREE.Mesh(new THREE.BoxGeometry(T,1.7,T),M.olive); m.position.set(wx(x),0.85,wx(y)); scene.add(m); const cab=new THREE.Mesh(new THREE.BoxGeometry(T*0.8,0.5,T*0.8),M.dark); cab.position.set(wx(x),1.95,wx(y)); scene.add(cab); }
  else if(c==='c'){ const m=new THREE.Mesh(new THREE.BoxGeometry(1.8,1.3,1.8),M.wood); m.position.set(wx(x),0.65,wx(y)); scene.add(m); }
  else if(c==='g'){ const m=new THREE.Mesh(new THREE.BoxGeometry(1.8,1.4,1.4),M.metal); m.position.set(wx(x),0.7,wx(y)); scene.add(m); const pipe=new THREE.Mesh(new THREE.CylinderGeometry(0.12,0.12,2.2,6),M.dark); pipe.position.set(wx(x)+0.6,1.8,wx(y)); scene.add(pipe); }
  else if(c==='b'){ const m=new THREE.Mesh(new THREE.BoxGeometry(T,3,0.1),M.bars); m.position.set(wx(x),1.5,wx(y)); scene.add(m); }
  else if(c==='D'){ frame(x,y); if(x===18&&y===4){ const s=doorSlab(x,y,M.door); s.visible=false; dynamicDoors.yard=s; } }
  else if(c==='L'){ dynamicDoors.office=doorSlab(x,y,M.door); }
  else if(c==='V'){ dynamicDoors.vault=doorSlab(x,y,M.vault); }
  if(interior(x,y)){ const f=new THREE.Mesh(new THREE.PlaneGeometry(T,T),M.floor); f.rotation.x=-Math.PI/2; f.position.set(wx(x),0.02,wx(y)); scene.add(f);
    const ce=new THREE.Mesh(new THREE.PlaneGeometry(T,T),M.ceil); ce.rotation.x=Math.PI/2; ce.position.set(wx(x),3,wx(y)); scene.add(ce); }
  if(c==='G'){ const f=new THREE.Mesh(new THREE.PlaneGeometry(T,T),toon({color:0x1e4a4a})); f.rotation.x=-Math.PI/2; f.position.set(wx(x),0.03,wx(y)); scene.add(f); const r=new THREE.Mesh(new THREE.TorusGeometry(0.7,0.08,6,16),M.metal); r.rotation.x=-Math.PI/2; r.position.set(wx(x),0.08,wx(y)); scene.add(r); }
}
function prop(x,y,w,h,d,mat,yoff){ const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat); m.position.set(wx(x),(yoff||0)+h/2,wx(y)); scene.add(m); return m; }
prop(1,12,1.2,0.9,1.0,M.metal); prop(1,12,0.9,0.3,0.7,M.dark,0.9);
prop(3,17,1.8,0.8,1.0,M.wood); prop(3,17,0.5,0.08,0.35,toon({color:0x3a2418}),0.8);
prop(8,17,1.0,2.2,0.6,M.metal); prop(9,18,1.0,2.2,0.6,M.metal); prop(7,18,1.0,2.2,0.6,M.metal);
const plaque=new THREE.Mesh(new THREE.PlaneGeometry(1.2,0.5),toon({color:0x9a8a3a})); plaque.position.set(wx(1)-0.98,1.8,wx(17)); plaque.rotation.y=Math.PI/2; scene.add(plaque);
prop(9,11,1.4,1.0,0.8,M.metal); const ant=new THREE.Mesh(new THREE.CylinderGeometry(0.03,0.03,1.6,4),M.dark); ant.position.set(wx(9),1.8,wx(11)); scene.add(ant);
prop(30,14,1.6,0.4,0.9,M.olive); prop(7,8,0.5,0.3,0.35,M.olive); prop(29,21,0.5,0.3,0.35,M.olive);
const sewer=new THREE.Mesh(new THREE.TorusGeometry(0.7,0.08,6,16),M.metal); sewer.rotation.x=-Math.PI/2; sewer.position.set(wx(start.x),0.06,wx(start.y)); scene.add(sewer);

// luces
scene.add(new THREE.AmbientLight(0x2a3450,0.8));
const moon=new THREE.DirectionalLight(0x8090c0,0.55); moon.position.set(COLS*T/2-30,50,ROWS*T/2-20); moon.target.position.set(COLS*T/2,0,ROWS*T/2); scene.add(moon.target); moon.castShadow=true; moon.shadow.mapSize.set(2048,2048); moon.shadow.camera.left=-45; moon.shadow.camera.right=45; moon.shadow.camera.top=45; moon.shadow.camera.bottom=-45; moon.shadow.camera.near=1; moon.shadow.camera.far=140; moon.shadow.bias=-0.0015; scene.add(moon);
scene.traverse(o=>{ if(o.isMesh&&o.material&&o.material.isMeshToonMaterial){ o.castShadow=true; o.receiveShadow=true; } }); ground.receiveShadow=true;
const lamps=[], lampPosts=[];
for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++)if(map[y][x]==='l'){ const L=new THREE.PointLight(0xffb060,1.3,15,1.6); L.position.set(wx(x),3.2,wx(y)); scene.add(L); lamps.push(L);
  const p=new THREE.Mesh(new THREE.CylinderGeometry(0.06,0.08,3.3,6),M.dark); p.position.set(wx(x),1.65,wx(y)); scene.add(p);
  const bulb=new THREE.Mesh(new THREE.SphereGeometry(0.16,6,6),new THREE.MeshBasicMaterial({color:0xffd080})); bulb.position.set(wx(x),3.25,wx(y)); scene.add(bulb); lampPosts.push(bulb); }
[[5.5,12.5,0xfff0c0,0.9],[3,17.5,0xffe8b0,0.8],[8.5,17.5,0xd0ffd0,0.7],[29.5,6.5,0xfff0c0,0.9],[27.5,9.5,0xfff0c0,0.6],[32,10,0xfff0c0,0.7],[31,13.5,0xff5040,0.5]].forEach(r=>{ const L=new THREE.PointLight(r[2],r[3],11,1.5); L.position.set(r[0]*T,2.8,r[1]*T); scene.add(L); lamps.push(L); });
const emergency=new THREE.AmbientLight(0x401010,0); scene.add(emergency);
const spots=[];
function mkSpot(px,pz,cx,cz,rad,ph){ const s=new THREE.SpotLight(0xfff4d0,2.4,45,0.22,0.4,1); s.position.set(px,7,pz); s.castShadow=true; s.shadow.mapSize.set(1024,1024); s.shadow.bias=-0.002; const tg=new THREE.Object3D(); scene.add(tg); s.target=tg; scene.add(s);
  const beam=new THREE.Mesh(new THREE.CylinderGeometry(0.15,2.2,1,12,1,true),new THREE.MeshBasicMaterial({color:0xfff0c0,transparent:true,opacity:0.08,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide})); scene.add(beam);
  const tower=new THREE.Mesh(new THREE.BoxGeometry(1.2,7,1.2),M.concrete); tower.position.set(px,3.5,pz); scene.add(tower);
  spots.push({s,tg,beam,cx,cz,rad,ph}); }
mkSpot(wx(18),wx(0),wx(9),wx(14),7,0); mkSpot(wx(35),wx(27),wx(25),wx(20),8,2);
(function(){ const g=new THREE.BufferGeometry(); const n=400,a=new Float32Array(n*3); for(let i=0;i<n;i++){const th=Math.random()*6.283,ph=Math.random()*1.2;a[i*3]=Math.cos(th)*Math.cos(ph)*100;a[i*3+1]=Math.sin(ph)*100+5;a[i*3+2]=Math.sin(th)*Math.cos(ph)*100;} g.setAttribute('position',new THREE.BufferAttribute(a,3));
  const p=new THREE.Points(g,new THREE.PointsMaterial({color:0x9fb0d8,size:0.4,fog:false})); p.position.set(COLS,0,ROWS); scene.add(p);
  const mo=new THREE.Mesh(new THREE.SphereGeometry(2.5,10,10),new THREE.MeshBasicMaterial({color:0xe8e8ff,fog:false})); mo.position.set(-20,45,-50); scene.add(mo); })();
// lluvia
const RAIN=900; const rainPos=new Float32Array(RAIN*6); const rainGeo=new THREE.BufferGeometry(); rainGeo.setAttribute('position',new THREE.BufferAttribute(rainPos,3));
const rain=new THREE.LineSegments(rainGeo,new THREE.LineBasicMaterial({color:0x9fb8c8,transparent:true,opacity:0.45})); scene.add(rain);
function rainSpawn(i,top){ const t=OUTDOOR[(Math.random()*OUTDOOR.length)|0]; const x=wx(t[0])+(Math.random()-0.5)*T, z=wx(t[1])+(Math.random()-0.5)*T, y=top?6+Math.random()*4:Math.random()*10; rainPos[i*6]=x;rainPos[i*6+1]=y;rainPos[i*6+2]=z;rainPos[i*6+3]=x+0.05;rainPos[i*6+4]=y-0.45;rainPos[i*6+5]=z; }
for(let i=0;i<RAIN;i++)rainSpawn(i,false);
function rainUpdate(dt){ for(let i=0;i<RAIN;i++){ rainPos[i*6+1]-=16*dt; rainPos[i*6+4]-=16*dt; if(rainPos[i*6+4]<0)rainSpawn(i,true); } rainGeo.attributes.position.needsUpdate=true; }
