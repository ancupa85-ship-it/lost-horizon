'use strict';
// ---------- MISIÓN 2 «DESCENSO»: la excavación (laboratorio del programa y tres grupos electrógenos) y el templo fenicio con la Fuente
// Plano de la excavación: la puerta blindada ALEPH-07 queda al norte, ya cerrada a la espalda. Al este, el laboratorio (W/_), al sur la compuerta
// de extracción 'X' (la sujeta un electroimán: sin los tres grupos, cae) y, por el oeste, un canal de desagüe que baja al templo por su cuenta.
const MAPSRC_EXC=[
"##############BB##############",
"#.....c......l.....c.........#",
"#.............P..............#",
"#.c.........................c#",
"####..######.....######..#####",
"#............................#",
"#..l.......ss.......g........#",
"#......##..ss.....l..........#",
"#.g....##..sss.............l.#",
"#.........sss.......WWWWWWWWWW",
"#l.........ss.......W________W",
"#..........ss..c....W__z_____W",
"#....c.....sss......D________W",
"#...........ss......W________W",
"#......##...ss...l..W___z____W",
"#......##...sss.....WWWWWWWWWW",
"#.g........ssss...........c..#",
"#ss.......sssss.l............#",
"#sss......ssss.........l.....#",
"#sWWWWWWWWWWWWWXWWWWWWWWWWWWW#",
"#ss..........................#",
"#.s.....l..............l.....#",
"#........c.........c.........#",
"##############################"];
// grupos electrógenos: [casilla del grupo, casilla desde la que se repara]
const GENS_EXC=[[2,8,3,9],[20,6,21,7],[2,16,3,17]];
const LOOK_PROG={uniform:0x3a4a5a,helmet:0x2a3440,rifle:true,hair:'#2a1a10',hairStyle:'corto'};
const GDEF_EXC=[
 {name:'Soldado del programa',role:'excavación oeste',nerve:2,loyal:1,wps:[[4,5],[4,12],[12,12],[12,6]],look:Object.assign({},LOOK_PROG,{hair:'#5a3a1e',hairStyle:'rizado'}),
  q:{templo:[{f:0,t:'Ahí abajo reza el coronel. Nosotros no bajamos.'},{f:2,t:'Cuando paran los grupos, lo de abajo deja de llorar y el coronel sube blanco. Por eso nadie los toca.',clue:'alarcon'}],
     clave:[{f:0,t:'La compuerta no tiene clave. Tiene corriente. Pregunta al técnico.'}],llave:[{f:0,t:'Aquí no hay llaves. Hay interruptores.'}]}},
 {name:'Soldado del programa',role:'excavación este',nerve:3,loyal:2,wps:[[18,5],[27,5],[27,8],[18,8],[18,17],[26,17]],look:Object.assign({},LOOK_PROG,{scar:true,rank:1,hair:'#141010',hairStyle:'rapado'}),
  q:{templo:[{f:0,t:'Material clasificado.'},{f:3,t:'La carga es una persona. O lo fue. Lo dicen los partes cuando nadie los lee.',clue:'luz'}],
     clave:[{f:0,t:'No hay clave que valga. Baja por el canal si tienes prisa; no vuelves seco.',clue:'protocolo'}],llave:[{f:0,t:'Ninguna.'}]}},
 {name:'Vigilante del canal',role:'desagüe',nerve:2,loyal:0,wps:[[3,21],[12,21],[12,22],[20,22],[26,21],[12,21]],look:Object.assign({},LOOK_PROG,{hair:'#b08a40',hairStyle:'flequillo',stubble:true}),
  q:{templo:[{f:0,t:'Yo vigilo el agua. Lo que haya debajo del agua no es mi turno.'},{f:1,t:'El coronel baja a rezar a las tres. Solo. Con la escolta a diez pasos para no oírle.',clue:'alarcon'}],
     clave:[{f:0,t:'El montacargas del templo sube a la torre. Es la única salida que conozco.'}],llave:[{f:0,t:'No hay.'}]}},
 {name:'Técnico Serra',role:'laboratorio',nerve:1,loyal:0,wps:[[23,12],[27,10],[27,14],[22,10]],look:{uniform:0xe8e8e0,pants:0x9a9a90,hair:'#8a8a80',glasses:true,plain:true,suit:true},
  q:{templo:[{f:0,t:'No me hagas daño. Yo solo mido. Mido el rendimiento.'},{f:1,t:'La compuerta de extracción la sujeta un electroimán con los tres grupos. Sin los tres, cae y se queda abierta. Nadie quiere que caiga.',clue:'protocolo'}],
     clave:[{f:0,t:'La lista está en el archivador del fondo. Siete nombres. El séptimo... Dios mío. Eres tú.',clue:'lista'}],llave:[{f:0,t:'Los interruptores están junto a cada grupo. Sin llave.'}]}},
];
function excInter(){ return [
 {x:14,y:1,label:'PUERTA BLINDADA · ALEPH-07 · CERRADA',f:()=>openDialog('PUERTA BLINDADA','<p>Se ha cerrado a vuestra espalda con un golpe sordo. Por fuera no se abre; por dentro, tampoco: el pasador es de la Compañía.</p><p>Roig: «Pues hacia abajo, entonces.»</p>',[{t:'Cerrar',f:closeDialog}])},
 {x:3,y:9,label:()=>genLabel(0),f:()=>toggleGen(0)},
 {x:21,y:7,label:()=>genLabel(1),f:()=>toggleGen(1)},
 {x:3,y:17,label:()=>genLabel(2),f:()=>toggleGen(2)},
 {x:22,y:10,label:'E · LEER EL PROTOCOLO DE EXTRACCIÓN',f:()=>{ addClue('protocolo'); openDialog('PROTOCOLO DE EXTRACCIÓN · ALEPH-07','<p>1. Los tres grupos electrógenos alimentan la bomba, el electroimán de la compuerta y la iluminación por sectores. 2. La compuerta de extracción permanece sellada mientras haya corriente en los tres; <b>sin los tres grupos cae por su peso y no vuelve a sellarse</b>. 3. El canal de desagüe del oeste drena al templo: <b>prohibido el paso</b>.</p><p>Al margen: "Si para la bomba, para el ruido. Si para el ruido, Alarcón no duerme. — S."</p>',[{t:'Cerrar',f:closeDialog}]); }},
 {x:26,y:10,label:'E · ABRIR EL ARCHIVADOR · LISTA DE SUJETOS',f:()=>{ const had=S.clues.includes('lista'); addClue('lista'); openDialog('LISTA DE SUJETOS · PROGRAMA LOST HORIZON','<p>LH-01 SERRA, M. — baja (1980). LH-02 OSUNA, R. — baja. LH-03 KELLER, D. — baja. LH-04 VIDAL, J. — baja (1982). LH-05 BAENA, T. — baja. LH-06 — retirado (sordera, afasia).</p><p><b>LH-07 CUTTLAS, A. — ACTIVO. 4ª sesión: pendiente.</b></p><p>LH-08 — sin asignar. Candidata propuesta: ROIG, E.</p>',[{t:'Cerrar',f:()=>{ closeDialog(); if(!had){ saveGame('Con la lista'); updObj(); setTimeout(()=>{ if(!uiOpen&&!S.over&&!cut)codec(CODEC.lista); },600); } }}]); }},
 {x:24,y:13,label:'E · LA SILLA',f:()=>{ addClue('silla'); openDialog('LA SILLA','<p>Correas de cuero, electrodos, un altavoz de rejilla que da a un tubo. El tubo baja al pozo.</p><p>No borran la memoria con drogas. La tapan con lo que canta abajo. Conoces el olor del cuero. Conoces el tubo.</p><p class="m">RECUERDO: una voz que dice "otra vez", y debajo de la voz, otra voz que no es humana y que pide perdón.</p>',[{t:'Cerrar',f:closeDialog}]); }},
 {x:14,y:21,label:'E · BAJAR AL TEMPLO',f:()=>travel('templo',[2,16],0)},
]; }
function genLabel(i){ return W.gens[i]?'E · PARAR EL GRUPO '+(i+1):'E · ARRANCAR EL GRUPO '+(i+1); }
function gensOff(){ return W.gens.filter(v=>!v).length; }
// apaga/enciende un grupo: su sector queda a oscuras, el zumbido baja y los guardias vendrán a arrancarlo; sin los tres, la compuerta cae
function toggleGen(i){ W.gens[i]=!W.gens[i]; applyGens(); beep(W.gens[i]?300:80,0.4,'sawtooth',0.06); S.fixTimer=30;
  if(!W.gens[i]){ const n=gensOff(); if(!S.flashSeen.gen2){ S.flashSeen.gen2=true; flash('ALIVIO','El sector se apaga y, abajo, algo deja de gritar a medias. Un guardia vendrá a arrancarlo: no tienes todo el tiempo.',7); } else if(n<3)flash('GRUPO '+(i+1)+' PARADO','Grupos parados: '+n+'/3. '+(n===2?'Uno más y la compuerta cae.':''),4);
    if(n===3&&!W.gateOpen){ W.gateOpen=true; if(dynamicDoors.gate)dynamicDoors.gate.visible=false; beep(50,1.2,'sawtooth',0.1,30); flash('LA COMPUERTA CAE','Sin los tres grupos, el electroimán suelta y la compuerta de extracción cae abierta. Abajo, por primera vez, silencio.',7); saveGame('Compuerta abierta'); } }
  updObj(); }
// luces por sectores: cada lámpara depende del grupo más cercano
function applyGens(){ if(!ZONE||!ZONE.gens)return; const sec=(x,z)=>{ let b=0,bd=1e9; ZONE.gens.forEach((g,i)=>{ const d=Math.hypot(wx(g[0])-x,wx(g[1])-z); if(d<bd){bd=d;b=i;} }); return b; };
  lamps.forEach(L=>{ const on=W.gens[sec(L.position.x,L.position.z)]; L.intensity=on?(L.userData.i||(L.userData.i=L.intensity)):0; }); lampPosts.forEach(b=>b.material.color.set(W.gens[sec(b.position.x,b.position.z)]?0xffd080:0x332218));
  const n=gensOff(); if(emergency)emergency.intensity=n===3?0.7:0; if(hum)hum.gain.gain.setTargetAtTime(0.012+0.016*(3-n),AC.currentTime,0.6); el('hPow').textContent=n?'GRUPOS '+(3-n)+'/3':'GRUPOS 3/3'; el('hPow').style.color=n===3?'#e0483a':''; }
function excProps(add){
  // andamios de la excavación
  const scaf=(x,y)=>{ for(const [dx,dz] of [[-0.8,-0.8],[0.8,-0.8],[-0.8,0.8],[0.8,0.8]]){ const p=new THREE.Mesh(new THREE.CylinderGeometry(0.05,0.05,2.9,5),M.dark); p.position.set(wx(x)+dx,1.45,wx(y)+dz); add(p); } const pl=new THREE.Mesh(new THREE.BoxGeometry(1.9,0.08,1.9),M.wood); pl.position.set(wx(x),2.2,wx(y)); add(pl); };
  scaf(9,6); scaf(16,9); scaf(5,14); scaf(23,17);
  // tubería de la bomba a lo largo del canal y bomba junto al grupo 2
  const pipe=new THREE.Mesh(new THREE.CylinderGeometry(0.14,0.14,T*12,6),M.metal); pipe.rotation.x=Math.PI/2; pipe.position.set(wx(13)+0.4,2.6,wx(11)); add(pipe);
  prop(19,6,1.2,0.9,1.0,M.metal); prop(19,6,0.6,0.5,0.6,M.dark,0.9);
  // laboratorio: mesas, archivador, la silla
  prop(22,10,1.6,0.8,0.8,M.metal); prop(22,10,0.5,0.05,0.35,toon({color:0xe8e0c0}),0.8);
  prop(26,10,0.9,1.8,0.6,M.metal); prop(27,10,0.9,1.8,0.6,M.metal);
  prop(24,13,0.7,0.5,0.7,M.dark); prop(24,13,0.7,0.9,0.12,M.dark,0.5); prop(24,13,0.12,0.6,0.12,M.metal,0.9);
  const tube=new THREE.Mesh(new THREE.CylinderGeometry(0.1,0.1,2.4,6),M.dark); tube.position.set(wx(24)-0.8,1.2,wx(13)); add(tube);
  prop(27,14,1.4,0.9,0.8,M.metal); prop(27,14,1.2,0.3,0.6,toon({color:0x3fd080}),0.9);
  // rótulo de la compuerta y escalera al templo
  const sign=new THREE.Mesh(new THREE.PlaneGeometry(1.6,0.45),toon({color:0xd8c860})); sign.position.set(wx(14),2.5,wx(19)-1.05); add(sign);
  for(let k=0;k<4;k++){ const st=new THREE.Mesh(new THREE.BoxGeometry(1.6,0.25,0.5),M.stone); st.position.set(wx(14),-0.12-k*0.25,wx(21)+0.3+k*0.45); add(st); }
  const hole=new THREE.Mesh(new THREE.PlaneGeometry(1.7,1.4),new THREE.MeshBasicMaterial({color:0x050608})); hole.rotation.x=-Math.PI/2; hole.position.set(wx(14),0.05,wx(21)+1.2); add(hole);
  // puerta blindada vista desde dentro: rótulo
  const s2=new THREE.Mesh(new THREE.PlaneGeometry(1.6,0.45),toon({color:0xc8b850})); s2.position.set(wx(14.5),2.4,wx(0)+1.05); s2.rotation.y=Math.PI; add(s2); }
function excSync(){ if(dynamicDoors.gate)dynamicDoors.gate.visible=!W.gateOpen; applyGens(); }
ZONES.excavacion={id:'excavacion',title:'LA EXCAVACIÓN',sub:'BAJO LA GALERÍA · LABORATORIO DEL PROGRAMA',desc:'Tres grupos electrógenos, un laboratorio y una compuerta que solo cae cuando todo se apaga. El zumbido ya no es un zumbido.',
  src:MAPSRC_EXC,start:[14,2],indoor:true,sky:0x06080a,fog:0.038,fogOff:0.07,ambient:0x32424c,ambientI:1.0,guards:GDEF_EXC,gens:GENS_EXC,exitTo:{templo:[14,21]},
  lights:[[25,12.5,0xe0f0ff,1.0,9,2.6],[22.5,10.5,0xe0f0ff,0.7,8,2.6],[14.5,19.6,0xffa040,0.8,7,2.4],[12,10,0x3a6a90,0.5,10,0.8],[11,16,0x3a6a90,0.5,10,0.8]],
  props:excProps,sync:excSync,dark(x,y){ let b=0,bd=1e9; GENS_EXC.forEach((g,i)=>{ const d=Math.hypot(g[0]-x,g[1]-y); if(d<bd){bd=d;b=i;} }); return !W.gens[b]; },
  inter:excInter()};

// ---- el templo: columnas, la alberca con la luz de la Fuente, Alarcón rezando y el montacargas que sube a la torre
const MAPSRC_TEM=[
"######################",
"#....................#",
"#.#....#....#.....G..#",
"#....................#",
"#.......ssssss.......#",
"#.#.....ssssss..#....#",
"#.......ssssss.......#",
"#.......ssssss.......#",
"#.#.....ssssss..#....#",
"#....................#",
"#.#....#....#....#...#",
"#....................#",
"#....................#",
"#.#....#....#....#...#",
"#....................#",
"#....................#",
"#.#..................#",
"#.U..................#",
"#....................#",
"######################"];
const GDEF_TEM=[
 {name:'Coronel Alarcón',role:'mando',nerve:5,loyal:3,wps:[[11,9]],face:[0,-1],look:{uniform:0x3a4030,cap:0x2a3024,rank:3,old:true,hair:'#c0c0b8',rosary:true,holster:true,skin:'#d8b090'},
  q:{templo:[{f:0,t:'No se habla en la iglesia. Ni en la mía ni en la suya.'},{f:2,t:'Le rezo para que no me oiga a mí. Cuando paran los grupos deja de llorar, y entonces sí que no duermo.'},{f:4,t:'Lo hice yo. Los siete. Rezaba el De profundis para no oír lo que decían al despertarse. Dios no perdonó a Tarsis; yo tampoco espero que me perdone.',clue:'alarcon'}],
     clave:[{f:0,t:'Ya ha abierto usted lo que había que abrir. La clave era un salmo, y ni eso me dejan.'}],llave:[{f:0,t:'El montacargas sube a la torre. Suba, Cuttlas. Arriba está lo que queda de la noche.'}]}},
 {name:'Escolta del coronel',role:'templo',nerve:3,loyal:2,wps:[[5,3],[16,3],[16,10],[5,10]],look:Object.assign({},LOOK_PROG,{helmet:0x1e2a30,rank:1,hair:'#2a1a10'}),
  q:{templo:[{f:0,t:'Diez pasos. Esa es la orden: a diez pasos de él y de espaldas al agua.'},{f:2,t:'El coronel habla con el agua y el agua le contesta. Yo no miro. Si miras, sueñas con ella.',clue:'luz'}],clave:[{f:0,t:'Ninguna.'}],llave:[{f:0,t:'El montacargas no tiene llave. Tiene al coronel delante.'}]}},
 {name:'Soldado del programa',role:'templo sur',nerve:2,loyal:1,wps:[[4,15],[18,15],[18,12],[4,12]],look:Object.assign({},LOOK_PROG,{hair:'#8a3a1a',hairStyle:'tupe'}),q:{}},
];
const temF={};
function temProps(add){
  for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++)if(MAPSRC_TEM[y][x]==='#'&&x>0&&y>0&&x<COLS-1&&y<ROWS-1){ const cap=new THREE.Mesh(new THREE.BoxGeometry(T+0.3,0.3,T+0.3),M.stone); cap.position.set(wx(x),3.4,wx(y)); add(cap); const base=new THREE.Mesh(new THREE.BoxGeometry(T+0.3,0.3,T+0.3),M.stone); base.position.set(wx(x),0.15,wx(y)); add(base); }
  // luz de la Fuente bajo el agua
  const glow=new THREE.Mesh(new THREE.PlaneGeometry(T*6,T*4),new THREE.MeshBasicMaterial({color:0x2fa070,transparent:true,opacity:0.35})); glow.rotation.x=-Math.PI/2; glow.position.set(wx(10.5),0.03,wx(5.5)); add(glow);
  const L=new THREE.PointLight(0x7fd4a0,1.8,20,1.2); L.position.set(wx(10.5),0.6,wx(5.5)); add(L); temF.light=L; temF.glow=glow;
  // montacargas: jaula y cables
  for(const [dx,dz] of [[-0.9,-0.9],[0.9,-0.9],[-0.9,0.9],[0.9,0.9]]){ const p=new THREE.Mesh(new THREE.BoxGeometry(0.08,3.4,0.08),M.metal); p.position.set(wx(18)+dx,1.7,wx(2)+dz); add(p); const c=new THREE.Mesh(new THREE.CylinderGeometry(0.02,0.02,3,4),M.dark); c.position.set(wx(18)+dx*0.5,3.3,wx(2)+dz*0.5); add(c); }
  const roof=new THREE.Mesh(new THREE.BoxGeometry(2,0.1,2),M.metal); roof.position.set(wx(18),3.35,wx(2)); add(roof); const lamp=new THREE.Mesh(new THREE.BoxGeometry(0.4,0.15,0.3),toon({color:0xffd080})); lamp.position.set(wx(18),3.2,wx(2)); add(lamp);
  const hole=new THREE.Mesh(new THREE.PlaneGeometry(1.8,1.8),new THREE.MeshBasicMaterial({color:0x050608})); hole.rotation.x=Math.PI/2; hole.position.set(wx(18),2.99,wx(2)); add(hole);
  // altar junto al agua, donde reza Alarcón
  prop(11,8,1.2,0.5,0.6,M.stone); const cand=new THREE.PointLight(0xffa040,0.9,6,1.5); cand.position.set(wx(11),1.0,wx(8)); add(cand);
  prop(2,16,0.2,0.2,0.2,M.stone); }
function temTick(dt){ if(!temF.light)return; const n=W.gens?gensOff():0; const calm=n/3; const a=S.t*(2.2-calm*1.4); temF.light.intensity=1.2+Math.sin(a)*(0.7-calm*0.5)+calm*0.6; temF.glow.material.opacity=0.28+Math.sin(a*0.5)*0.08; }
const INTER_TEM=[
 {x:2,y:16,label:'E · VOLVER A LA EXCAVACIÓN',f:()=>travel('excavacion',[14,21],Math.PI)},
 {x:11,y:3,label:'E · MIRAR EL AGUA',f:()=>{ const had=S.clues.includes('luz'); addClue('luz'); openDialog('EL AGUA','<p>Tibia. Debajo, una luz que no viene de ninguna lámpara y que late despacio'+(gensOff()===3?', tranquila: con los grupos parados respira como quien duerme':', a destiempo, como alguien que aguanta')+'.</p><p>No la ves entera. Nadie la ha visto entera. Ves tu cara en el agua y, por un momento, no es la tuya.</p>'+(had?'':'<p class="m">RECUERDO: una cocina con la luz de la tarde. No es tuyo. Es de ella, o de los seis anteriores.</p>'),[{t:'Apartar la mirada',f:closeDialog}]); }},
 {x:18,y:2,label:'E · SUBIR EN EL MONTACARGAS',f:()=>{ if(S.over)return; S.over=true; outro2(); }},
];
ZONES.templo={id:'templo',title:'EL TEMPLO',sub:'BAJO LA EXCAVACIÓN · LA FUENTE',desc:'Columnas de hace tres mil años y un agua que late con luz propia. El coronel reza en la orilla. El montacargas del fondo sube a la torre.',
  src:MAPSRC_TEM,start:[2,16],indoor:true,sky:0x030806,fog:0.05,fogOff:0.07,ambient:0x203a30,ambientI:0.9,guards:GDEF_TEM,inter:INTER_TEM,exitTo:{excavacion:[2,16]},
  lights:[[4.5,2.5,0xffc070,0.8,9,2.6],[17.5,16.5,0xffc070,0.7,9,2.6],[18.5,2.5,0xffd080,1.0,6,3.0]],props:temProps,tick:temTick,
  onEnter(){ saveGame('En el templo'); if(!S.codecSeen.templo){ S.codecSeen.templo=true; setTimeout(()=>{ if(!uiOpen&&!S.over&&!cut)codec(CODEC.templo); },1200); } }};
// entrada a la misión 2 desde la galería (misión 1, con el expediente en la mano) o desde el menú
function startMission(m,withIntro){ reset(m); try{localStorage.removeItem('lh-save');}catch(e){} startGame(withIntro); }
