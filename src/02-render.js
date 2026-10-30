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
  rock:flatTex(64,64,'#4a4038',(x,w,h)=>{x.fillStyle='#3a322c';x.fillRect(0,0,w,h/2);x.fillStyle='#2a241f';x.fillRect(0,h/2-3,w,3);x.fillRect(w/3,0,2,h/2);x.fillRect(2*w/3,h/2,2,h/2);x.fillStyle='#5a5048';x.fillRect(8,12,10,4);x.fillRect(38,40,14,3);}),
  stone:flatTex(64,64,'#3e3c38',(x,w,h)=>{x.fillStyle='#2e2c28';x.fillRect(0,0,w,2);x.fillRect(0,0,2,h);x.fillRect(w/2,0,2,h);x.fillRect(0,h/2,w,2);x.fillStyle='#4a4842';x.fillRect(6,6,14,8);x.fillStyle='#35332f';x.fillRect(40,38,16,10);}),
  bars:flatTex(64,96,'rgba(0,0,0,0)',(x,w,h)=>{x.clearRect(0,0,w,h);x.fillStyle='#9aa2a8';for(let i=6;i<w;i+=12)x.fillRect(i,0,4,h);x.fillRect(0,h/2-2,w,4);}),
};
TEX.bars.wrapS=TEX.bars.wrapT=THREE.ClampToEdgeWrapping;
const toon=(o)=>new THREE.MeshToonMaterial(Object.assign({gradientMap:grad},o));
const M={ concrete:toon({map:TEX.concrete}), plaster:toon({map:TEX.plaster}), asphalt:toon({map:TEX.asphalt}), floor:toon({map:TEX.floor}), wood:toon({map:TEX.wood}), olive:toon({map:TEX.olive}), metal:toon({map:TEX.metal}),
  door:toon({map:TEX.door}), vault:toon({map:TEX.vault}), rock:toon({map:TEX.rock}), stone:toon({map:TEX.stone}), water:new THREE.MeshToonMaterial({gradientMap:grad,color:0x16323e,transparent:true,opacity:0.78}), ceil:toon({color:0x5a5852}), bars:toon({map:TEX.bars,transparent:true,alphaTest:0.5}), dark:toon({color:0x202428}), skin:toon({color:0xe8b890}), boots:toon({color:0x1a1410}) };

// ---------- MUNDO POR ZONAS: buildWorld(zona) levanta la geometría y las luces en un grupo; unloadWorld() lo quita
const box=new THREE.BoxGeometry(T,3,T), tall=new THREE.BoxGeometry(T,3.6,T);
let zoneGroup=null, ground=null, dynamicDoors={}, lamps=[], lampPosts=[], spots=[], emergency=null, ambient=null;
function zadd(o){ zoneGroup.add(o); return o; }
function wallMesh(x,y,geo,mat,h){ const m=new THREE.Mesh(geo,mat); m.position.set(wx(x),h/2,wx(y)); zadd(m); return m; }
function doorSlab(x,y,mat){ const horiz=sightT(x-1,y)&&sightT(x+1,y); const g=new THREE.BoxGeometry(horiz?T:0.3,3,horiz?0.3:T); const m=new THREE.Mesh(g,mat); m.position.set(wx(x),1.5,wx(y)); zadd(m); return m; }
function frame(x,y){ const horiz=cell(x-1,y)==='W'||cell(x-1,y)==='#'; const g=new THREE.BoxGeometry(horiz?T:0.4,0.4,horiz?0.4:T); const m=new THREE.Mesh(g,M.dark); m.position.set(wx(x),2.8,wx(y)); zadd(m); }
function prop(x,y,w,h,d,mat,yoff){ const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat); m.position.set(wx(x),(yoff||0)+h/2,wx(y)); zadd(m); return m; }
function mkSpot(px,pz,cx,cz,rad,ph){ const s=new THREE.SpotLight(0xfff4d0,2.4,45,0.22,0.4,1); s.position.set(px,7,pz); s.castShadow=true; s.shadow.mapSize.set(1024,1024); s.shadow.bias=-0.002; const tg=new THREE.Object3D(); zadd(tg); s.target=tg; zadd(s);
  const beam=new THREE.Mesh(new THREE.CylinderGeometry(0.15,2.2,1,12,1,true),new THREE.MeshBasicMaterial({color:0xfff0c0,transparent:true,opacity:0.08,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide})); zadd(beam);
  const tower=new THREE.Mesh(new THREE.BoxGeometry(1.2,7,1.2),M.concrete); tower.position.set(px,3.5,pz); zadd(tower);
  spots.push({s,tg,beam,cx,cz,rad,ph}); }
function unloadWorld(){ if(!zoneGroup)return; zoneGroup.traverse(o=>{ if(o.isMesh&&o.geometry&&o.geometry!==box&&o.geometry!==tall)o.geometry.dispose(); }); scene.remove(zoneGroup); if(ground&&ground.material.map)ground.material.map.dispose(); zoneGroup=null; ground=null; dynamicDoors={}; lamps=[]; lampPosts=[]; spots=[]; emergency=null; ambient=null; }
function buildWorld(z){ unloadWorld(); zoneGroup=new THREE.Group(); scene.add(zoneGroup);
  scene.background.set(z.sky||0x070a12); scene.fog.color.set(z.sky||0x070a12); scene.fog.density=W.power?(z.fog||0.026):(z.fogOff||0.04);
  ambient=zadd(new THREE.AmbientLight(z.ambient||0x2a3450,z.ambientI||0.8));
  const wallMat=z.indoor?M.rock:M.concrete, floorMat=z.indoor?M.stone:M.floor;
  if(!z.indoor){ const t=TEX.asphalt.clone(); t.needsUpdate=true; t.repeat.set(COLS,ROWS); ground=new THREE.Mesh(new THREE.PlaneGeometry(COLS*T,ROWS*T),toon({map:t})); ground.rotation.x=-Math.PI/2; ground.position.set(COLS*T/2,0,ROWS*T/2); zadd(ground); }
  for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++){ const c=map[y][x];
    if(c==='#')wallMesh(x,y,tall,wallMat,3.6);
    else if(c==='W'){ const inside=interior(x-1,y)||interior(x+1,y)||interior(x,y-1)||interior(x,y+1); wallMesh(x,y,box,inside?M.plaster:M.concrete,3); }
    else if(c==='T'){ const m=new THREE.Mesh(new THREE.BoxGeometry(T,1.7,T),M.olive); m.position.set(wx(x),0.85,wx(y)); zadd(m); const cab=new THREE.Mesh(new THREE.BoxGeometry(T*0.8,0.5,T*0.8),M.dark); cab.position.set(wx(x),1.95,wx(y)); zadd(cab); }
    else if(c==='c'){ const m=new THREE.Mesh(new THREE.BoxGeometry(1.8,1.3,1.8),M.wood); m.position.set(wx(x),0.65,wx(y)); zadd(m); }
    else if(c==='g'){ const m=new THREE.Mesh(new THREE.BoxGeometry(1.8,1.4,1.4),M.metal); m.position.set(wx(x),0.7,wx(y)); zadd(m); const pipe=new THREE.Mesh(new THREE.CylinderGeometry(0.12,0.12,2.2,6),M.dark); pipe.position.set(wx(x)+0.6,1.8,wx(y)); zadd(pipe); }
    else if(c==='b'){ const m=new THREE.Mesh(new THREE.BoxGeometry(T,3,0.1),M.bars); m.position.set(wx(x),1.5,wx(y)); zadd(m); barsMesh=m; }
    else if(c==='B'){ const horiz=cell(x-1,y)==='#'||cell(x-1,y)==='B'; const m=new THREE.Mesh(new THREE.BoxGeometry(horiz?T:0.5,3.6,horiz?0.5:T),M.vault); m.position.set(wx(x),1.8,wx(y)); zadd(m); }
    else if(c==='D'){ frame(x,y); if(z.id==='base'&&x===18&&y===4){ const s=doorSlab(x,y,M.door); s.visible=false; dynamicDoors.yard=s; } }
    else if(c==='L'){ dynamicDoors.office=doorSlab(x,y,M.door); }
    else if(c==='V'){ dynamicDoors.vault=doorSlab(x,y,M.vault); }
    else if(c==='U'){ const lad=new THREE.Mesh(new THREE.BoxGeometry(0.9,3.4,0.12),M.dark); lad.position.set(wx(x),1.7,wx(y)-0.8); zadd(lad); for(let k=0;k<7;k++){ const r=new THREE.Mesh(new THREE.BoxGeometry(0.9,0.06,0.12),M.metal); r.position.set(wx(x),0.35+k*0.46,wx(y)-0.74); zadd(r); } const hole=new THREE.Mesh(new THREE.PlaneGeometry(1.6,1.6),new THREE.MeshBasicMaterial({color:0x101418})); hole.rotation.x=Math.PI/2; hole.position.set(wx(x),2.99,wx(y)); zadd(hole); }
    if(interior(x,y)){ if(c==='s'&&z.indoor){ const f=new THREE.Mesh(new THREE.PlaneGeometry(T,T),M.water); f.rotation.x=-Math.PI/2; f.position.set(wx(x),0.04,wx(y)); zadd(f); const b=new THREE.Mesh(new THREE.PlaneGeometry(T,T),M.stone); b.rotation.x=-Math.PI/2; b.position.set(wx(x),-0.3,wx(y)); zadd(b); }
      else { const f=new THREE.Mesh(new THREE.PlaneGeometry(T,T),floorMat); f.rotation.x=-Math.PI/2; f.position.set(wx(x),0.02,wx(y)); zadd(f); }
      const ce=new THREE.Mesh(new THREE.PlaneGeometry(T,T),z.indoor?M.rock:M.ceil); ce.rotation.x=Math.PI/2; ce.position.set(wx(x),3,wx(y)); zadd(ce); }
    if(c==='G'){ const f=new THREE.Mesh(new THREE.PlaneGeometry(T,T),toon({color:0x1e4a4a})); f.rotation.x=-Math.PI/2; f.position.set(wx(x),0.03,wx(y)); zadd(f); const r=new THREE.Mesh(new THREE.TorusGeometry(0.7,0.08,6,16),M.metal); r.rotation.x=-Math.PI/2; r.position.set(wx(x),0.08,wx(y)); zadd(r); }
  }
  if(z.props)z.props(zadd);
  // luces: farolas 'l' del plano, puntos extra y focos de la zona
  for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++)if(map[y][x]==='l'){ const L=new THREE.PointLight(z.indoor?0xffc070:0xffb060,z.indoor?1.15:1.3,z.indoor?10:15,1.6); L.position.set(wx(x),z.indoor?2.6:3.2,wx(y)); zadd(L); lamps.push(L);
    const p=new THREE.Mesh(new THREE.CylinderGeometry(0.06,0.08,z.indoor?2.7:3.3,6),M.dark); p.position.set(wx(x),z.indoor?1.35:1.65,wx(y)); zadd(p);
    const bulb=new THREE.Mesh(new THREE.SphereGeometry(0.16,6,6),new THREE.MeshBasicMaterial({color:0xffd080})); bulb.position.set(wx(x),z.indoor?2.65:3.25,wx(y)); zadd(bulb); lampPosts.push(bulb); }
  (z.lights||[]).forEach(r=>{ const L=new THREE.PointLight(r[2],r[3],r[4]||11,1.5); L.position.set(r[0]*T,r[5]!=null?r[5]:2.8,r[1]*T); zadd(L); lamps.push(L); });
  emergency=zadd(new THREE.AmbientLight(0x401010,0));
  (z.spots||[]).forEach(a=>mkSpot(wx(a[0]),wx(a[1]),wx(a[2]),wx(a[3]),a[4],a[5]));
  zoneGroup.traverse(o=>{ if(o.isMesh&&o.material&&o.material.isMeshToonMaterial){ o.castShadow=true; o.receiveShadow=true; } }); if(ground)ground.receiveShadow=true;
  moon.visible=!!z.outdoor; moon.castShadow=!!z.outdoor; sky.visible=!!z.outdoor; rain.visible=!!z.outdoor&&OUTDOOR.length>0;
  if(z.outdoor){ moon.position.set(COLS*T/2-30,50,ROWS*T/2-20); moon.target.position.set(COLS*T/2,0,ROWS*T/2); sky.position.set(COLS,0,ROWS); if(OUTDOOR.length)for(let i=0;i<RAIN;i++)rainSpawn(i,false); } }

// cielo, luna y lluvia: se crean una vez y se muestran solo en zonas exteriores
const moon=new THREE.DirectionalLight(0x8090c0,0.55); moon.castShadow=true; moon.shadow.mapSize.set(2048,2048); moon.shadow.camera.left=-45; moon.shadow.camera.right=45; moon.shadow.camera.top=45; moon.shadow.camera.bottom=-45; moon.shadow.camera.near=1; moon.shadow.camera.far=140; moon.shadow.bias=-0.0015; scene.add(moon); scene.add(moon.target);
const sky=new THREE.Group(); scene.add(sky);
(function(){ const g=new THREE.BufferGeometry(); const n=400,a=new Float32Array(n*3); for(let i=0;i<n;i++){const th=Math.random()*6.283,ph=Math.random()*1.2;a[i*3]=Math.cos(th)*Math.cos(ph)*100;a[i*3+1]=Math.sin(ph)*100+5;a[i*3+2]=Math.sin(th)*Math.cos(ph)*100;} g.setAttribute('position',new THREE.BufferAttribute(a,3));
  const p=new THREE.Points(g,new THREE.PointsMaterial({color:0x9fb0d8,size:0.4,fog:false})); sky.add(p);
  const mo=new THREE.Mesh(new THREE.SphereGeometry(2.5,10,10),new THREE.MeshBasicMaterial({color:0xe8e8ff,fog:false})); mo.position.set(-56,45,-78); sky.add(mo); })();
// lluvia
const RAIN=900; const rainPos=new Float32Array(RAIN*6); const rainGeo=new THREE.BufferGeometry(); rainGeo.setAttribute('position',new THREE.BufferAttribute(rainPos,3));
const rain=new THREE.LineSegments(rainGeo,new THREE.LineBasicMaterial({color:0x9fb8c8,transparent:true,opacity:0.45})); scene.add(rain);
function rainSpawn(i,top){ const t=OUTDOOR[(Math.random()*OUTDOOR.length)|0]; const x=wx(t[0])+(Math.random()-0.5)*T, z=wx(t[1])+(Math.random()-0.5)*T, y=top?6+Math.random()*4:Math.random()*10; rainPos[i*6]=x;rainPos[i*6+1]=y;rainPos[i*6+2]=z;rainPos[i*6+3]=x+0.05;rainPos[i*6+4]=y-0.45;rainPos[i*6+5]=z; }
function rainUpdate(dt){ if(!rain.visible||!OUTDOOR.length)return; for(let i=0;i<RAIN;i++){ rainPos[i*6+1]-=16*dt; rainPos[i*6+4]-=16*dt; if(rainPos[i*6+4]<0)rainSpawn(i,true); } rainGeo.attributes.position.needsUpdate=true; }
