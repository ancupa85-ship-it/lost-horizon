'use strict';
// ---------- ESTADO Y DATOS
const S={}; let started=false, uiOpen=false, cut=null;
const keys={}; let yaw=-Math.PI/2, pitch=0, locked=false;
const CLUES={
  peris:'Peris (cocina): el coronel reza en el despacho y se le oye por la pared, siempre lo mismo: "desde lo profundo". Dicen que la clave es eso.',
  c130:'Ibarra: "es el salmo que reza, el De profundis, el ciento treinta". Lo sabe media base.',
  c1983:'Moya: "la clave es 1983". Lo dijo demasiado rápido.',
  roma:'Alarcón reza en latín con la Vulgata y cuenta los salmos como Roma, no como los protestantes. "Uno menos."',
  llave:'La llave del despacho la lleva el cabo Ibarra.',
  tele:'Teletipo: la clave del archivo no se transmite; "procedimiento habitual". Cuatro operarios de baja por "voces". Halloran no debe saberlo.',
  vulgata:'Biblia Vulgata en el escritorio, la cinta en PSALMUS CXXIX: "De profundis clamavi ad te". Margen: "Ella también clama. Nadie la oye. — A."',
  hallo:'Halloran: la clave es el rezo de Alarcón, pero él numera como la Vulgata. "Si cuenta usted como un protestante, se equivocará de salmo."',
  fuente:'Bajo el templo hay algo que respira y canta. Lo llaman "la carga". Los que bajan vuelven sordos, o no vuelven.',
  file:'EXPEDIENTE LH-07. Sujeto: Cuttlas, A. Memoria borrada tres veces. "El sujeto recuerda una cocina." Recomiendan una cuarta sesión.'
};
const GENERIC={clave:[{f:0,t:'Ni idea. Yo soy de la garita, la clave es cosa de Alarcón.'}],llave:[{f:0,t:'La del despacho la tiene el cabo Ibarra. Pregúntale a él, si te deja.',clue:'llave'}],templo:[{f:0,t:'De eso no se habla.'},{f:2,t:'Dicen que canta. Por la noche, cuando paran los generadores. Yo no quiero oírlo.',clue:'fuente'}]};
const GDEF=[
 {name:'Soldado Peris',role:'cocina',nerve:2,loyal:0,wps:[[26,6],[33,6],[29,7],[29,10],[26,10],[26,7]],look:{uniform:0x5a6a44,helmet:0x4a5a3a},
  q:{clave:[{f:0,t:'Yo hago el rancho. La clave la pone el coronel y no la suelta.'},{f:1,t:'No la sé, de verdad. Pero el coronel reza en el despacho y se le oye por la pared: "desde lo profundo", siempre lo mismo. Ibarra dice que la clave es eso, el rezo.',clue:'peris'}],
     llave:[{f:0,t:'La del despacho la lleva Ibarra, el cabo. Siempre encima.',clue:'llave'}],
     templo:[{f:0,t:'No bajo. Nadie de cocina baja.'},{f:2,t:'Se oye. Cuando apagan el generador se oye algo que respira abajo. Lo llaman "la carga". Los que bajan vuelven sordos, o no vuelven.',clue:'fuente'}]}},
 {name:'Cabo Ibarra',role:'llaves',nerve:3,loyal:1,hasKey:true,wps:[[13,3],[13,8],[4,8],[4,5]],look:{uniform:0x4f5a3c,helmet:0x4a5a3a,rifle:true,stubble:true,rank:1},
  q:{clave:[{f:0,t:'Pregúntaselo a Alarcón. Yo no soy el archivo.'},{f:2,t:'Es el salmo que reza, hombre. El De profundis. El ciento treinta. Lo sabe media base, no es un secreto.',clue:'c130'}],
     llave:[{f:0,t:'¿Qué llave?'},{f:1,t:'La llevo yo. Bolsillo izquierdo. Cógela y acaba de una vez.',clue:'llave',key:true}],
     templo:[{f:0,t:'Combustible. Un depósito.'},{f:3,t:'Yo bajo con los partes. Hay algo ahí que no es combustible. Alarcón le reza a eso, no a Dios.',clue:'fuente'}]}},
 {name:'Sargento Moya',role:'enlace',nerve:4,loyal:2,wps:[[20,16],[33,16],[33,19],[20,19]],look:{uniform:0x3f4a34,helmet:0x2f3a2a,rifle:true,scar:true,rank:3},
  q:{clave:[{f:0,t:'Mil novecientos ochenta y tres. El año. Métela y lárgate.',clue:'c1983'},{f:3,t:'...Vale. Vale. No es el número que crees. El coronel reza en latín, con la Vulgata. Cuenta los salmos como Roma, no como los protestantes. Uno menos.',clue:'roma'}],
     llave:[{f:0,t:'Ibarra. El cabo. Siempre la lleva él.',clue:'llave'}],
     templo:[{f:0,t:'Un almacén.'},{f:2,t:'Yo llevo los partes a la Compañía. Cuatro bajas este mes por "voces". Lo que hay abajo no es combustible. Y Halloran lo sabía antes que nadie; por eso está en la celda.',clue:'fuente'}]}},
 {name:'Soldado de garita',role:'patio sur',nerve:2,loyal:1,wps:[[13,21],[22,21],[22,25],[13,25]],look:{uniform:0x4f5a3c,helmet:0x4a5a3a,rifle:true},q:{}},
 {name:'Soldado de radio',role:'comunicaciones',nerve:2,loyal:1,wps:[[2,11],[10,11],[10,14],[2,14]],look:{uniform:0x5a6050,helmet:0x4a5a3a},q:{templo:[{f:0,t:'De eso no se habla.'},{f:1,t:'Por el teletipo llegan partes de "la carga". Bajas por voces. Yo solo los paso.',clue:'fuente'}]}},
 {name:'Soldado de puerta',role:'salida',nerve:3,loyal:1,wps:[[24,20],[33,20],[33,25],[24,25]],look:{uniform:0x4f5a3c,helmet:0x4a5a3a,rifle:true},q:{}},
];
function mkGuard(d,red){ const p=d.wps[0]; const g={name:d.name,role:d.role,nerve:d.nerve,loyal:d.loyal,hasKey:!!d.hasKey,q:d.q,wps:d.wps,wi:1,x:wx(p[0]),z:wx(p[1]),fx:1,fz:0,state:'patrol',susp:0,target:null,searchT:0,shotT:0,down:0,dead:false,fear:0,red:!!red,fixing:false,moving:false};
  const look=Object.assign({},d.look||{uniform:0x4f5a3c,helmet:0x4a5a3a,rifle:true}); if(red)look.helmet=0x8a2a2a; g.fig=figure(look); g.fig.g.position.set(g.x,0,g.z); scene.add(g.fig.g);
  g.mark=new THREE.Sprite(new THREE.SpriteMaterial({map:MK.ex,transparent:true})); g.mark.scale.set(0.6,0.6,1); g.mark.visible=false; scene.add(g.mark); return g; }
const halloFig=figure({uniform:0xe8e8e0,pants:0x9a9a90,hair:'#b0b0b0',glasses:true,skin:'#e0c0a0',old:true,suit:true,plain:true}); halloFig.g.position.set(wx(31),0,wx(13)+0.4); halloFig.g.rotation.y=Math.PI; scene.add(halloFig.g);
const playerFig=figure({uniform:0x2e3630,pants:0x262c28,hair:'#2a1a10',stubble:true,pistol:true,suit:true,plain:true,gloves:true,band:'#5a6a7a'}); playerFig.g.visible=false; scene.add(playerFig.g);
const roigFig=figure({uniform:0x2a3038,pants:0x23282c,hair:'#3a2418',female:true,pistol:true,suit:true,plain:true,gloves:true,skin:'#e6c0a0'}); roigFig.g.visible=false; scene.add(roigFig.g);
// con uniforme robado: guerrera y casco de la tropa
const playerFigU=figure({uniform:0x4f5a3c,helmet:0x4a5a3a,hair:'#2a1a10',stubble:true,pistol:true,gloves:true}); playerFigU.g.visible=false; scene.add(playerFigU.g);
const roigFigU=figure({uniform:0x4f5a3c,helmet:0x4a5a3a,hair:'#3a2418',female:true,pistol:true,gloves:true,skin:'#e6c0a0'}); roigFigU.g.visible=false; scene.add(roigFigU.g);
function setDisguise(e,on){ if(!e||!e.figBase)return; const old=e.fig; e.disguise=!!on; e.fig=on?e.figU:e.figBase; if(old!==e.fig){ e.fig.g.position.copy(old.g.position); e.fig.g.rotation.copy(old.g.rotation); e.fig.g.scale.copy(old.g.scale); e.fig.g.visible=old.g.visible; old.g.visible=false; } if(e===S.p)updHud(); }
const vidalFig=figure({uniform:0x4f5a3c,cap:0x3f4a34,moustache:true,rosary:true,rank:1,holster:true,skin:'#d8a880'}); vidalFig.g.position.set(wx(31),0,wx(11)); vidalFig.g.visible=false; scene.add(vidalFig.g);
let barsMesh=null; scene.traverse(o=>{ if(o.isMesh&&o.material===M.bars)barsMesh=o; });
const ember=new THREE.PointLight(0xff7a30,0,3.5); scene.add(ember);
const puffTex=(()=>{const c=document.createElement('canvas');c.width=32;c.height=32;const x=c.getContext('2d');const g=x.createRadialGradient(16,16,2,16,16,16);g.addColorStop(0,'rgba(200,200,210,.7)');g.addColorStop(1,'rgba(200,200,210,0)');x.fillStyle=g;x.fillRect(0,0,32,32);return new THREE.CanvasTexture(c);})();
const puffs=[]; for(let i=0;i<10;i++){ const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:puffTex,transparent:true,opacity:0,depthWrite:false})); sp.scale.set(0.3,0.3,1); scene.add(sp); puffs.push({sp,t:9}); }
let third=false;

function reset(){
  S.p={name:'CUTTLAS',fig:playerFig,x:wx(start.x),z:wx(start.y),fx:1,fz:0,hp:5,ammo:8,crouch:false,hurtT:0,carry:null,key:false,file:false,moving:false,run:false,down:0,shotT:0};
  S.c={name:'ROIG',fig:roigFig,x:wx(start.x),z:wx(start.y),fx:1,fz:0,hp:5,ammo:12,crouch:false,hurtT:0,carry:null,key:false,file:false,moving:false,run:false,down:0,shotT:0,ko:0};
  for(const o of [[0,1],[1,0],[0,-1],[-1,0]]){ if(!solidT(start.x+o[0],start.y+o[1])){ S.c.x=wx(start.x+o[0]); S.c.z=wx(start.y+o[1]); break; } } roigFig.g.visible=true; roigFig.g.rotation.z=0; roigFig.g.position.set(S.c.x,0,S.c.z); playerFig.g.rotation.z=0;
  S.swaps=0; S.cOrder='wait'; S.orders=0; S.silencer=false; S.disguises=0; S.p.figBase=playerFig; S.p.figU=playerFigU; S.c.figBase=roigFig; S.c.figU=roigFigU; S.p.disguise=false; S.c.disguise=false; playerFigU.g.visible=false; roigFigU.g.visible=false; S.teamKO=0; S.guide={};
  if(S.guards)S.guards.forEach(g=>{scene.remove(g.fig.g);scene.remove(g.mark);});
  S.guards=GDEF.map(d=>mkGuard(d)); S.bodies=[]; S.kill=0; S.ko=0; S.alarms=0; S.base='calma'; S.alertT=0; S.over=false; S.t=0; S.reinforced=false; S.wrongCode=0; S.halloTalked=false; S.interro=0;
  S.clues=[]; S.flashSeen={}; S.recoil=0; S.muzzle=0; S.fixTimer=0; S.freeze=0; S.codecSeen={}; S.cigs=3; S.smoke=0; S.stepT=0; S.inCell=false; S.dogsDone=false; S.dogKills=0; S.vidal={stage:0,fail:0,cool:0}; S.ammoTaken={}; if(S.dogs)S.dogs.forEach(d=>scene.remove(d.fig.g)); S.dogs=[]; W.cellOpen=false; if(barsMesh)barsMesh.visible=true; vidalFig.g.visible=false; flow=null;
  W.officeOpen=false; W.vaultOpen=false; W.yardDoorClosed=false; setPower(true); el('hCig').textContent=3;
  dynamicDoors.office.visible=true; dynamicDoors.vault.visible=true; dynamicDoors.yard.visible=false;
  yaw=-Math.PI/2; pitch=0; updHud(); el('hObj').textContent='OBJETIVO: ENTRA EN EL ARCHIVO'; renderNote();
}
function setPower(on){ W.power=on; lamps.forEach(L=>L.intensity=on?L.userData.i||(L.userData.i=L.intensity):0.0); lampPosts.forEach(b=>b.material.color.set(on?0xffd080:0x332218)); spots.forEach(s=>{s.s.intensity=on?2.4:0; s.beam.visible=on;}); emergency.intensity=on?0:0.9; scene.fog.density=on?0.026:0.04; el('hPow').textContent=on?'GENERADOR':'APAGADO'; el('hPow').style.color=on?'':'#e0483a'; if(hum)hum.gain.gain.setTargetAtTime(on?0.05:0.012,AC.currentTime,0.5); }
