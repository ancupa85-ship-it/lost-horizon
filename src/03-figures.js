'use strict';
// ---------- PERSONAJES 3D (figuras de bloques, cara pixelada)
function faceTex(o){ const c=document.createElement('canvas'); c.width=8;c.height=8; const x=c.getContext('2d'); x.fillStyle=o.skin||'#e8b890'; x.fillRect(0,0,8,8); x.fillStyle=o.hair||'#2a1a10'; x.fillRect(0,0,8,2); x.fillStyle='#111'; x.fillRect(1,3,2,1); x.fillRect(5,3,2,1); if(o.glasses){x.fillStyle='#223';x.fillRect(1,3,2,2);x.fillRect(5,3,2,2);x.fillRect(3,3,2,1);} x.fillStyle=o.stubble?'#a07858':'#c08868'; x.fillRect(2,6,4,1); if(o.scar){x.fillStyle='#902020';x.fillRect(6,2,1,3);} const t=new THREE.CanvasTexture(c); t.magFilter=t.minFilter=THREE.NearestFilter; return t; }
function figure(o){ const g=new THREE.Group(); const mU=toon({color:o.uniform}), mP=toon({color:o.pants||o.uniform}), mSk=M.skin, mH=toon({color:o.helmet||0x4a5a3a}), mHair=toon({color:o.hair||'#2a1a10'});
  const torso=new THREE.Mesh(new THREE.BoxGeometry(0.52,0.62,0.3),mU); torso.position.y=1.16; g.add(torso);
  const belt=new THREE.Mesh(new THREE.BoxGeometry(0.54,0.08,0.32),M.boots); belt.position.y=0.88; g.add(belt);
  const head=new THREE.Mesh(new THREE.BoxGeometry(0.3,0.32,0.3),[mSk,mSk,mHair,mSk,toon({map:faceTex(o)}),mHair]); head.position.y=1.64; g.add(head);
  if(o.helmet){ const h=new THREE.Mesh(new THREE.BoxGeometry(0.38,0.16,0.38),mH); h.position.y=1.78; g.add(h); const brim=new THREE.Mesh(new THREE.BoxGeometry(0.4,0.04,0.46),mH); brim.position.set(0,1.71,0.03); g.add(brim); }
  const mkLeg=x=>{ const p=new THREE.Group(); p.position.set(x,0.86,0); const m=new THREE.Mesh(new THREE.BoxGeometry(0.2,0.78,0.22),mP); m.position.y=-0.39; p.add(m); const b=new THREE.Mesh(new THREE.BoxGeometry(0.22,0.14,0.28),M.boots); b.position.set(0,-0.8,0.03); p.add(b); g.add(p); return p; };
  const mkArm=(x,hand)=>{ const p=new THREE.Group(); p.position.set(x,1.42,0); const m=new THREE.Mesh(new THREE.BoxGeometry(0.16,0.58,0.16),mU); m.position.y=-0.29; p.add(m); const h=new THREE.Mesh(new THREE.BoxGeometry(0.14,0.12,0.14),mSk); h.position.y=-0.62; p.add(h);
    if(hand==='rifle'){ const r=new THREE.Mesh(new THREE.BoxGeometry(0.06,0.09,0.8),M.boots); r.position.set(0,-0.6,0.3); p.add(r); const mag=new THREE.Mesh(new THREE.BoxGeometry(0.05,0.14,0.08),M.boots); mag.position.set(0,-0.7,0.2); p.add(mag); } g.add(p); return p; };
  const F={g,legL:mkLeg(-0.14),legR:mkLeg(0.14),armL:mkArm(-0.34),armR:mkArm(0.34,o.rifle?'rifle':(o.pistol?'pistol':null)),head,phase:Math.random()*6,rifle:!!o.rifle};
  if(o.pistol){ const pg=new THREE.Mesh(new THREE.BoxGeometry(0.05,0.07,0.26),M.boots); pg.position.set(0,-0.62,0.18); F.armR.add(pg); }
  g.traverse(m=>{ if(m.isMesh)m.castShadow=true; }); return F; }
function dogFig(){ const g=new THREE.Group(); const m=toon({color:0x4a3524}); const body=new THREE.Mesh(new THREE.BoxGeometry(0.32,0.34,0.8),m); body.position.y=0.55; g.add(body);
  const head=new THREE.Mesh(new THREE.BoxGeometry(0.26,0.26,0.3),m); head.position.set(0,0.72,0.5); g.add(head); const snout=new THREE.Mesh(new THREE.BoxGeometry(0.14,0.12,0.18),M.boots); snout.position.set(0,0.66,0.72); g.add(snout);
  [-0.09,0.09].forEach(x=>{ const e=new THREE.Mesh(new THREE.BoxGeometry(0.06,0.12,0.04),m); e.position.set(x,0.9,0.42); g.add(e); });
  const eyes=new THREE.Mesh(new THREE.BoxGeometry(0.2,0.04,0.02),toon({color:0xe0c040})); eyes.position.set(0,0.76,0.66); g.add(eyes);
  const legs=[]; [[-0.1,0.28],[0.1,0.28],[-0.1,-0.28],[0.1,-0.28]].forEach(p=>{ const l=new THREE.Group(); l.position.set(p[0],0.4,p[1]); const lm=new THREE.Mesh(new THREE.BoxGeometry(0.1,0.4,0.1),m); lm.position.y=-0.2; l.add(lm); g.add(l); legs.push(l); });
  const tail=new THREE.Mesh(new THREE.BoxGeometry(0.06,0.06,0.3),m); tail.position.set(0,0.65,-0.5); tail.rotation.x=0.6; g.add(tail); g.traverse(o=>{ if(o.isMesh)o.castShadow=true; }); return {g,legs,phase:Math.random()*6}; }
function animFig(f,moving,dt,alert){ if(moving)f.phase+=dt*8; const s=moving?Math.sin(f.phase):0; f.legL.rotation.x=s*0.7; f.legR.rotation.x=-s*0.7; f.armL.rotation.x=-s*0.5; f.armR.rotation.x=alert?-1.35:(s*0.5+(f.rifle?-0.35:0)); }
function markTex(ch,col){ const c=document.createElement('canvas'); c.width=32;c.height=32; const x=c.getContext('2d'); x.fillStyle=col; x.font='bold 28px monospace'; x.textAlign='center'; x.fillText(ch,16,27); const t=new THREE.CanvasTexture(c); t.magFilter=THREE.NearestFilter; return t; }
const MK={ex:markTex('!','#ff4a3a'),q:markTex('?','#f0b240')};
// brazos del jugador (hijos de la cámara)
const arms=new THREE.Group(); arms.scale.set(0.62,0.62,0.62); camera.add(arms);
(function(){ const uni=toon({color:0x3a4238}); const fore=new THREE.Mesh(new THREE.BoxGeometry(0.11,0.11,0.42),uni); fore.position.set(0.26,-0.27,-0.52); fore.rotation.x=-0.25; arms.add(fore);
  const hand=new THREE.Mesh(new THREE.BoxGeometry(0.1,0.12,0.12),M.skin); hand.position.set(0.26,-0.23,-0.74); arms.add(hand);
  const slide=new THREE.Mesh(new THREE.BoxGeometry(0.045,0.06,0.26),M.boots); slide.position.set(0.26,-0.15,-0.86); arms.add(slide);
  const grip=new THREE.Mesh(new THREE.BoxGeometry(0.04,0.1,0.06),toon({color:0x3a2a1a})); grip.position.set(0.26,-0.22,-0.76); arms.add(grip);
  const foreL=new THREE.Mesh(new THREE.BoxGeometry(0.11,0.11,0.36),uni); foreL.position.set(-0.22,-0.3,-0.5); foreL.rotation.set(-0.3,0.5,0); arms.add(foreL);
  const handL=new THREE.Mesh(new THREE.BoxGeometry(0.1,0.1,0.12),M.skin); handL.position.set(-0.08,-0.26,-0.7); arms.add(handL); })();
const muzzle=new THREE.PointLight(0xffc060,0,8); scene.add(muzzle);
