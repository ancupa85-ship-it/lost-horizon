'use strict';
// ---------- PERSONAJES 3D (modelos articulados con texturas pixel generadas)
// Interfaz que usan el resto de módulos:
//   figure(look) -> {g, legL, legR, armL, armR, head, phase, rifle}
//   dogFig()     -> {g, legs[4], phase}
//   animFig(f, moving, dt, alert) / animDog(f, dt, moving)
function cssHex(n){ return typeof n==='string'?n:'#'+(n>>>0).toString(16).padStart(6,'0').slice(-6); }
function shade(col,f){ const c=new THREE.Color(cssHex(col)); c.r=Math.min(1,c.r*f); c.g=Math.min(1,c.g*f); c.b=Math.min(1,c.b*f); return '#'+c.getHexString(); }
function ptex(w,h,fn){ const c=document.createElement('canvas'); c.width=w; c.height=h; const x=c.getContext('2d'); fn(x,w,h); const t=new THREE.CanvasTexture(c); t.magFilter=t.minFilter=THREE.NearestFilter; return t; }
// camuflaje: base + manchas oscuras y claras, con semilla para que cada soldado repita su patrón
function camo(x,w,h,base,seed,plain){ x.fillStyle=base; x.fillRect(0,0,w,h); if(plain)return; let s=seed||7; const rnd=()=>{ s=(s*16807)%2147483647; return s/2147483647; };
  const dark=shade(base,0.72), light=shade(base,1.18);
  for(let i=0;i<Math.max(4,(w*h/40)|0);i++){ x.fillStyle=i%3?dark:light; const bw=1+(rnd()*4)|0, bh=1+(rnd()*3)|0; x.fillRect((rnd()*w)|0,(rnd()*h)|0,bw,bh); } }
// cara para la cabeza esférica: 32×16, el frente centrado en x=8 (u=0.25 de la esfera), la nuca en x≥16
function faceTex(o){ return ptex(32,16,(x)=>{ const skin=o.skin||'#e8b890', hair=o.hair||'#2a1a10';
  x.fillStyle=skin; x.fillRect(0,0,32,16);
  x.fillStyle=shade(skin,0.9); x.fillRect(0,13,32,3); x.fillRect(16,4,16,12);                              // mandíbula y nuca en sombra
  if(!o.bald){ x.fillStyle=hair; x.fillRect(0,0,32,3); x.fillRect(15,0,17,o.female?15:12); x.fillRect(0,0,1,9); x.fillRect(0,3,2,4); x.fillRect(14,3,2,4); if(o.fringe!==false)x.fillRect(3,3,5,1); if(o.female){ x.fillRect(0,3,2,7); x.fillRect(13,3,3,7); } }
  x.fillStyle=shade(hair,0.8); x.fillRect(3,5,3,1); x.fillRect(10,5,3,1);                                   // cejas
  x.fillStyle='#f4f0ea'; x.fillRect(3,6,3,2); x.fillRect(10,6,3,2); x.fillStyle='#1a1a1a'; x.fillRect(4,6,1,2); x.fillRect(11,6,1,2); // ojos
  x.fillStyle=shade(skin,0.78); x.fillRect(7,8,2,3); x.fillStyle=shade(skin,0.9); x.fillRect(6,11,4,1);     // nariz
  x.fillStyle='#7a3a30'; x.fillRect(6,12,4,1);                                                             // boca
  if(o.moustache){ x.fillStyle=hair; x.fillRect(5,11,6,1); }
  if(o.stubble){ x.fillStyle='rgba(60,40,30,.45)'; for(let i=0;i<14;i++)x.fillRect(3+((i*5)%10),11+((i*3)%4),1,1); }
  if(o.glasses){ x.fillStyle='#2a3038'; x.fillRect(2,5,5,4); x.fillRect(9,5,5,4); x.fillRect(7,6,2,1); x.fillStyle='rgba(180,220,240,.55)'; x.fillRect(3,6,3,2); x.fillRect(10,6,3,2); }
  if(o.scar){ x.fillStyle='#a03838'; x.fillRect(12,4,1,6); x.fillRect(11,6,1,1); }
  if(o.band){ x.fillStyle=o.band; x.fillRect(0,2,32,3); x.fillStyle=shade(o.band,0.7); x.fillRect(0,4,32,1); }
  if(o.old){ x.fillStyle=shade(skin,0.8); x.fillRect(3,9,2,1); x.fillRect(11,9,2,1); x.fillRect(5,13,1,1); x.fillRect(10,13,1,1); } }); }
// guerrera envolvente: 40×24, el frente centrado en x=20 y la espalda en los bordes
function torsoTex(o){ const base=cssHex(o.uniform); return ptex(40,24,(x,w,h)=>{ camo(x,w,h,base,o.seed,o.plain); const dk=shade(base,0.6), lt=shade(base,1.25);
  x.fillStyle=dk; x.fillRect(0,0,w,2); x.fillRect(0,h-2,w,2);                                              // cuello y bajo
  if(o.suit){ x.fillStyle=shade(base,1.3); x.fillRect(19,2,2,h-4); x.fillStyle='#2a2f2a'; x.fillRect(12,4,16,8); x.fillStyle='#3a403a'; x.fillRect(13,5,14,6); x.fillStyle='#161a16'; x.fillRect(15,5,2,6); x.fillRect(23,5,2,6); x.fillStyle=shade(base,0.9); x.fillRect(0,10,8,3); x.fillRect(32,10,8,3); return; }
  x.fillStyle=lt; x.fillRect(19,2,2,h-4); x.fillStyle=dk; for(let y=4;y<h-3;y+=4)x.fillRect(20,y,1,1);     // tapeta y botones
  x.fillStyle=shade(base,0.85); x.fillRect(12,6,6,6); x.fillRect(22,6,6,6); x.fillStyle=dk; x.fillRect(12,6,6,1); x.fillRect(22,6,6,1); // bolsillos de pecho
  x.fillStyle='#2a2418'; x.fillRect(9,2,3,h-4); x.fillRect(28,2,3,h-4); x.fillRect(2,2,3,h-4); x.fillRect(35,2,3,h-4); x.fillRect(0,10,8,3); x.fillRect(32,10,8,3); // correajes delante y detrás
  x.fillStyle='#d8d0b0'; x.fillRect(22,13,6,2); x.fillStyle='#3a3a3a'; x.fillRect(23,13,1,1); x.fillRect(25,13,1,1); // cinta de nombre
  if(o.rank){ x.fillStyle='#d8b040'; for(let i=0;i<o.rank;i++)x.fillRect(13,14+i*2,4,1); } }); }
function sleeveTex(o){ const base=cssHex(o.uniform); return ptex(8,16,(x,w,h)=>{ camo(x,w,h,base,o.seed+11,o.plain); x.fillStyle=shade(base,0.6); x.fillRect(0,h-2,w,2); if(o.rank){ x.fillStyle='#d8b040'; for(let i=0;i<o.rank;i++)x.fillRect(2,3+i*2,4,1); } }); }
function pantsTex(o){ const base=cssHex(o.pants||o.uniform); return ptex(10,24,(x,w,h)=>{ camo(x,w,h,base,o.seed+23,o.plain); x.fillStyle=shade(base,0.85); x.fillRect(1,13,8,5); x.fillStyle=shade(base,0.6); x.fillRect(1,13,8,1); x.fillRect(4,0,1,h); if(o.suit){ x.fillStyle=shade(base,1.3); x.fillRect(0,20,w,1); } }); }
function bootTex(){ return ptex(8,8,(x)=>{ x.fillStyle='#1a1410'; x.fillRect(0,0,8,8); x.fillStyle='#3a2e22'; x.fillRect(2,1,4,4); x.fillStyle='#6a5a44'; x.fillRect(3,1,1,1); x.fillRect(4,2,1,1); x.fillRect(3,3,1,1); x.fillRect(4,4,1,1); x.fillStyle='#0a0806'; x.fillRect(0,6,8,2); }); }
function helmetTex(col){ const base=cssHex(col); return ptex(16,16,(x,w,h)=>{ camo(x,w,h,base,5); x.fillStyle='#4a3a28'; x.fillRect(0,6,w,2); x.fillStyle='rgba(255,255,255,.08)'; x.fillRect(0,0,w,3); }); }
function bx(w,h,d,mat){ const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat); m.castShadow=true; return m; }
function sph(r,mat,ws,hs){ const m=new THREE.Mesh(new THREE.SphereGeometry(r,ws||10,hs||8),mat); m.castShadow=true; return m; }
// miembro redondeado de una pieza (torno): empieza en y=0 y baja h, con los extremos romos
function limb(rT,rB,h,mat){ const pts=[new THREE.Vector2(0,0),new THREE.Vector2(rT*0.75,0),new THREE.Vector2(rT,-h*0.08),new THREE.Vector2(rB,-h*0.92),new THREE.Vector2(rB*0.75,-h),new THREE.Vector2(0,-h)]; const m=new THREE.Mesh(new THREE.LatheGeometry(pts,10),mat); m.castShadow=true; return m; }
function figure(o){ o=Object.assign({seed:(Math.random()*1000)|0},o); const g=new THREE.Group();
  const mSleeve=toon({map:sleeveTex(o)}), mPants=toon({map:pantsTex(o)}), mBoot=toon({map:bootTex()}), mSkin=toon({color:o.skin||'#e8b890'}), mDark=M.boots, mLeather=toon({color:0x2a2418}), mMetal=toon({color:0x3a3d40});
  const mTorso=toon({map:torsoTex(o)}), mUni=toon({color:cssHex(o.uniform)}), mHair=toon({color:o.hair||'#2a1a10'});
  // tronco torneado: caderas, cintura, pecho y hombros caídos; sección elíptica
  const prof=[[0.19,0.84],[0.21,0.9],[0.19,1.0],[0.2,1.1],[0.24,1.25],[0.26,1.38],[0.25,1.47],[0.17,1.53],[0.08,1.56],[0,1.57]].map(p=>new THREE.Vector2(p[0],p[1]));
  const torso=new THREE.Mesh(new THREE.LatheGeometry(prof,14),mTorso); torso.rotation.y=Math.PI; torso.scale.set(o.female?0.9:1,1,0.64); torso.castShadow=true; g.add(torso);
  [-0.24,0.24].forEach(x=>{ const sh=sph(0.1,mSleeve); sh.scale.set(1,0.8,0.9); sh.position.set(x,1.45,0); g.add(sh); });
  const belt=new THREE.Mesh(new THREE.CylinderGeometry(0.215,0.215,0.07,14),mLeather); belt.scale.z=0.66; belt.position.y=0.86; belt.castShadow=true; g.add(belt);
  if(!o.suit){ [-0.12,0.12].forEach(x=>{ const p=bx(0.09,0.09,0.05,mLeather); p.position.set(x,0.84,0.13); g.add(p); }); const canteen=sph(0.065,toon({color:0x3b4a3a})); canteen.scale.set(1,1.3,0.7); canteen.position.set(-0.18,0.8,-0.12); g.add(canteen); }
  if(o.pistol||o.holster){ const hol=bx(0.05,0.15,0.09,mLeather); hol.position.set(0.24,0.76,0.03); g.add(hol); }
  // cuello y cabeza esférica con la cara pintada
  const neck=new THREE.Mesh(new THREE.CylinderGeometry(0.06,0.07,0.1,10),mSkin); neck.position.y=1.58; neck.castShadow=true; g.add(neck);
  const head=sph(0.165,toon({map:faceTex(o)}),16,12); head.scale.set(1,1.12,1); head.position.y=1.77; g.add(head);
  if(o.helmet){ const mH=toon({map:helmetTex(o.helmet)}); const dome=new THREE.Mesh(new THREE.SphereGeometry(0.2,12,7,0,Math.PI*2,0,Math.PI/2),mH); dome.scale.set(1,0.8,1.08); dome.position.y=1.82; dome.castShadow=true; g.add(dome);
    const rim=new THREE.Mesh(new THREE.CylinderGeometry(0.21,0.225,0.045,12),mH); rim.scale.z=1.08; rim.position.y=1.81; rim.castShadow=true; g.add(rim); const strap=bx(0.28,0.02,0.02,mLeather); strap.position.set(0,1.62,0.1); g.add(strap); }
  if(o.cap){ const mC=toon({color:cssHex(o.cap)}); const c=new THREE.Mesh(new THREE.CylinderGeometry(0.15,0.17,0.09,12),mC); c.position.y=1.93; c.castShadow=true; g.add(c); const vis=bx(0.26,0.02,0.12,mC); vis.position.set(0,1.9,0.19); g.add(vis); }
  if(o.band){ const tail=bx(0.04,0.2,0.02,toon({color:o.band})); tail.position.set(-0.07,1.72,-0.17); tail.rotation.x=-0.3; g.add(tail); }
  if(o.female){ const bun=sph(0.1,mHair); bun.scale.set(1.3,1,1); bun.position.set(0,1.7,-0.14); g.add(bun); const tail=limb(0.05,0.035,0.3,mHair); tail.position.set(0,1.66,-0.19); tail.rotation.x=0.25; g.add(tail); }
  if(o.rosary){ const bead=toon({color:0x3a2a20}); for(let i=0;i<7;i++){ const b=sph(0.014,bead,5,4); b.position.set(-0.06+i*0.02,1.5-Math.sin(i/6*Math.PI)*0.1,0.16); g.add(b); } }
  // piernas: cadera > rodilla > bota, con muslo y pantorrilla torneados
  const mkLeg=x=>{ const hip=new THREE.Group(); hip.position.set(x,0.86,0); hip.add(limb(0.11,0.09,0.4,mPants));
    const knee=new THREE.Group(); knee.position.y=-0.4; hip.add(knee); const kn=sph(0.085,mPants); kn.scale.y=0.9; knee.add(kn); knee.add(limb(0.085,0.065,0.36,mPants));
    const boot=bx(0.16,0.12,0.25,mBoot); boot.position.set(0,-0.4,0.03); knee.add(boot); const toe=sph(0.075,mBoot); toe.scale.set(1,0.75,1); toe.position.set(0,-0.41,0.14); knee.add(toe); g.add(hip); hip.knee=knee; return hip; };
  // brazos: hombro > codo > mano
  const mkArm=(x,hand)=>{ const sh=new THREE.Group(); sh.position.set(x,1.44,0); sh.add(limb(0.08,0.07,0.3,mSleeve));
    const elbow=new THREE.Group(); elbow.position.y=-0.3; sh.add(elbow); elbow.add(sph(0.065,mSleeve)); elbow.add(limb(0.065,0.055,0.27,mSleeve));
    const hd=sph(0.062,o.gloves?mLeather:mSkin); hd.scale.set(0.9,1.15,0.75); hd.position.y=-0.32; elbow.add(hd);
    if(hand==='rifle'){ const r=new THREE.Group(); r.position.set(0,-0.3,0.05); r.rotation.x=Math.PI/2-0.55; const body=bx(0.05,0.1,0.5,mDark); body.position.z=0.15; r.add(body); const barrel=new THREE.Mesh(new THREE.CylinderGeometry(0.014,0.014,0.42,6),mMetal); barrel.rotation.x=Math.PI/2; barrel.position.set(0,0.03,0.6); r.add(barrel);
      const stock=bx(0.05,0.11,0.26,toon({color:0x4a3220})); stock.position.set(0,-0.02,-0.2); r.add(stock); const mag=bx(0.04,0.16,0.08,mDark); mag.position.set(0,-0.12,0.2); mag.rotation.x=0.25; r.add(mag); const sight=bx(0.02,0.04,0.04,mDark); sight.position.set(0,0.08,0.3); r.add(sight); elbow.add(r); }
    if(hand==='pistol'){ const pg=new THREE.Group(); pg.position.set(0,-0.36,0.08); const slide=bx(0.04,0.05,0.22,mDark); slide.position.z=0.08; pg.add(slide); const grip=bx(0.035,0.1,0.05,toon({color:0x3a2a1a})); grip.position.set(0,-0.06,-0.02); grip.rotation.x=0.2; pg.add(grip); elbow.add(pg); }
    g.add(sh); sh.elbow=elbow; return sh; };
  const F={g,legL:mkLeg(-0.12),legR:mkLeg(0.12),armL:mkArm(-0.31),armR:mkArm(0.31,o.rifle?'rifle':(o.pistol?'pistol':null)),head,phase:Math.random()*6,rifle:!!o.rifle};
  g.traverse(m=>{ if(m.isMesh)m.castShadow=true; }); animFig(F,false,0,false); return F; }
function animFig(f,moving,dt,alert){ if(moving)f.phase+=dt*8; const s=moving?Math.sin(f.phase):0;
  f.legL.rotation.x=s*0.7; f.legR.rotation.x=-s*0.7; f.legL.knee.rotation.x=moving?Math.max(0,-s)*0.9+0.1:0.05; f.legR.knee.rotation.x=moving?Math.max(0,s)*0.9+0.1:0.05;
  if(alert){ f.armR.rotation.x=-1.35; f.armL.rotation.x=-1.1; f.armL.rotation.y=0.6; f.armR.elbow.rotation.x=-0.3; f.armL.elbow.rotation.x=-0.9; }
  else { f.armL.rotation.y=0; f.armL.rotation.x=-s*0.5; f.armR.rotation.x=s*0.5+(f.rifle?-0.35:0); f.armL.elbow.rotation.x=-0.25; f.armR.elbow.rotation.x=f.rifle?-0.9:-0.25; }}
// perro: pastor con silla negra, orejas, cola y patas con rodilla
function furTex(top){ return ptex(16,16,(x,w,h)=>{ x.fillStyle='#8a6a3a'; x.fillRect(0,0,w,h); let s=3; const r=()=>{s=(s*16807)%2147483647;return s/2147483647;}; for(let i=0;i<60;i++){ x.fillStyle=i%2?'#6e5230':'#a08048'; x.fillRect((r()*w)|0,(r()*h)|0,1,1+(r()*2)|0); } if(top){ x.fillStyle='#1e1812'; x.fillRect(0,0,w,h*0.55); x.fillStyle='#2e2418'; for(let i=0;i<20;i++)x.fillRect((r()*w)|0,(r()*h*0.6)|0,1,1); } }); }
function dogFig(){ const g=new THREE.Group(); const mF=toon({map:furTex(false)}), mT=toon({map:furTex(true)}), mB=toon({color:0x1e1812}), mN=toon({color:0x0a0806});
  const fur=[mF,mF,mT,mF,mF,mF];
  const chest=bx(0.34,0.36,0.46,fur); chest.position.set(0,0.56,0.14); g.add(chest); const hind=bx(0.3,0.32,0.4,fur); hind.position.set(0,0.54,-0.26); g.add(hind);
  const neck=bx(0.2,0.22,0.22,fur); neck.position.set(0,0.72,0.42); neck.rotation.x=-0.5; g.add(neck);
  const head=bx(0.24,0.24,0.26,[mF,mF,mT,mF,mF,mT]); head.position.set(0,0.82,0.56); g.add(head);
  const snout=bx(0.13,0.11,0.2,mF); snout.position.set(0,0.76,0.76); g.add(snout); const nose=bx(0.06,0.05,0.04,mN); nose.position.set(0,0.79,0.87); g.add(nose);
  const tongue=bx(0.05,0.02,0.1,toon({color:0xc04050})); tongue.position.set(0,0.7,0.8); tongue.rotation.x=0.4; g.add(tongue);
  [-0.08,0.08].forEach(x=>{ const e=new THREE.Mesh(new THREE.ConeGeometry(0.05,0.15,4),mB); e.position.set(x,0.99,0.5); e.rotation.y=Math.PI/4; e.castShadow=true; g.add(e); });
  const mEye=toon({color:0xe0c040}); [-0.07,0.07].forEach(x=>{ const e=bx(0.04,0.03,0.02,mEye); e.position.set(x,0.86,0.69); g.add(e); });
  const legs=[]; [[-0.1,0.3],[0.1,0.3],[-0.09,-0.32],[0.09,-0.32]].forEach((p,i)=>{ const hip=new THREE.Group(); hip.position.set(p[0],0.42,p[1]); const up=bx(0.1,0.24,0.13,i<2?mF:mT); up.position.y=-0.1; hip.add(up);
    const knee=new THREE.Group(); knee.position.y=-0.22; hip.add(knee); const low=bx(0.08,0.2,0.08,mF); low.position.y=-0.1; knee.add(low); const paw=bx(0.09,0.05,0.11,mB); paw.position.set(0,-0.2,0.02); knee.add(paw); hip.knee=knee; g.add(hip); legs.push(hip); });
  const tail=new THREE.Group(); tail.position.set(0,0.64,-0.46); const tm=bx(0.06,0.06,0.34,mT); tm.position.z=-0.17; tail.add(tm); tail.rotation.x=0.8; g.add(tail);
  g.traverse(o=>{ if(o.isMesh)o.castShadow=true; }); return {g,legs,tail,phase:Math.random()*6}; }
function animDog(f,dt,moving){ const sn=Math.sin(f.phase); f.legs.forEach((l,i)=>{ const s=(i<2?sn:-sn); l.rotation.x=s*0.8; l.knee.rotation.x=Math.max(0,(i<2?-s:s))*0.9; }); if(f.tail){ f.tail.rotation.y=Math.sin(f.phase*0.7)*0.4; f.tail.rotation.x=moving?0.4:0.9; } }
function markTex(ch,col){ const c=document.createElement('canvas'); c.width=32;c.height=32; const x=c.getContext('2d'); x.fillStyle=col; x.font='bold 28px monospace'; x.textAlign='center'; x.fillText(ch,16,27); const t=new THREE.CanvasTexture(c); t.magFilter=THREE.NearestFilter; return t; }
const MK={ex:markTex('!','#ff4a3a'),q:markTex('?','#f0b240')};
const fMark=new THREE.Sprite(new THREE.SpriteMaterial({map:markTex('F','#4fb9d6'),transparent:true,depthTest:false})); fMark.scale.set(0.5,0.5,1); fMark.visible=false; scene.add(fMark);
// brazos del jugador (hijos de la cámara): manga del traje, guante y pistola con corredera, guardamonte y cañón
const arms=new THREE.Group(); arms.scale.set(0.62,0.62,0.62); camera.add(arms);
(function(){ const uni=toon({map:sleeveTex({uniform:0x2e3630,seed:9})}), glove=toon({color:0x1a1a18}), steel=toon({color:0x2a2c30}), wood=toon({color:0x3a2a1a});
  const fore=limb(0.055,0.065,0.42,uni); fore.position.set(0.26,-0.3,-0.31); fore.rotation.x=Math.PI/2-0.25; arms.add(fore);
  const cuff=new THREE.Mesh(new THREE.CylinderGeometry(0.068,0.068,0.05,10),glove); cuff.rotation.x=Math.PI/2; cuff.position.set(0.26,-0.24,-0.7); arms.add(cuff);
  const hand=sph(0.058,glove); hand.scale.set(0.85,1,1.15); hand.position.set(0.26,-0.23,-0.76); arms.add(hand);
  const slide=new THREE.Mesh(new THREE.BoxGeometry(0.045,0.055,0.28),steel); slide.position.set(0.26,-0.15,-0.88); arms.add(slide);
  const frame=new THREE.Mesh(new THREE.BoxGeometry(0.04,0.035,0.2),M.boots); frame.position.set(0.26,-0.19,-0.9); arms.add(frame);
  const barrel=new THREE.Mesh(new THREE.CylinderGeometry(0.012,0.012,0.06,6),steel); barrel.rotation.x=Math.PI/2; barrel.position.set(0.26,-0.15,-1.04); arms.add(barrel);
  const guard=new THREE.Mesh(new THREE.BoxGeometry(0.01,0.05,0.06),M.boots); guard.position.set(0.26,-0.23,-0.86); arms.add(guard);
  const grip=new THREE.Mesh(new THREE.BoxGeometry(0.04,0.1,0.06),wood); grip.position.set(0.26,-0.22,-0.76); arms.add(grip);
  const sight=new THREE.Mesh(new THREE.BoxGeometry(0.01,0.02,0.02),steel); sight.position.set(0.26,-0.115,-0.78); arms.add(sight);
  const foreL=limb(0.055,0.065,0.36,uni); foreL.position.set(-0.2,-0.31,-0.33); foreL.rotation.set(Math.PI/2-0.3,0.5,0); arms.add(foreL);
  const handL=sph(0.055,glove); handL.scale.set(0.85,1,1.15); handL.position.set(-0.08,-0.26,-0.7); arms.add(handL); })();
const muzzle=new THREE.PointLight(0xffc060,0,8); scene.add(muzzle);
