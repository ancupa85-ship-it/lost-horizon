'use strict';
// ---------- ZONAS: planos, guardias, props y puntos de interacción de cada zona; carga y descarga con pantalla de carga
const MAPSRC_BASE=[
"####################################",
"#..........l......#..............l.#",
"#.P...c...cc......#..TT....cc......#",
"#.ss..c....c......#..TT.....c......#",
"#.ss...........cc.D................#",
"#.........l.......#......WWWWWWWWWW#",
"#......cc.........#......W________W#",
"#....TT...........#......W_zz_____W#",
"#....TT........ss.#..g...D____WWDWW#",
"#...............s.#......W____W__zW#",
"#WWWWWWDWWWW......#......WWWWWW___W#",
"#_____z____W......#......W________W#",
"#__cc__z___W....l.#..........WWbWWW#",
"#______z___D......#..........W___W.#",
"#______z___W..cc..#.......l..W___W.#",
"#WWWLWWWWWWW..........ss.....WWWWW.#",
"#_____W____W...............s.......#",
"#_____W____V.............s.........#",
"#_z___W_zz_W...cc..................#",
"#_____W____W.......l...............#",
"#WWWWWWWWWWW.......................#",
"#.....cc......l.........ss....TT...#",
"#......c...............ss...ccTT...#",
"#..cc.............cc...............#",
"#..cc.................l............#",
"#.........cc............ss.........#",
"#.ss..........l...................G#",
"####################################"];
const baseHatch={};
function baseProps(add){
  prop(1,12,1.2,0.9,1.0,M.metal); prop(1,12,0.9,0.3,0.7,M.dark,0.9);
  prop(3,17,1.8,0.8,1.0,M.wood); prop(3,17,0.5,0.08,0.35,toon({color:0x3a2418}),0.8);
  prop(8,17,1.0,2.2,0.6,M.metal); prop(9,18,1.0,2.2,0.6,M.metal); prop(7,18,1.0,2.2,0.6,M.metal);
  const plaque=new THREE.Mesh(new THREE.PlaneGeometry(1.2,0.5),toon({color:0x9a8a3a})); plaque.position.set(wx(1)-0.98,1.8,wx(17)); plaque.rotation.y=Math.PI/2; add(plaque);
  prop(9,11,1.4,1.0,0.8,M.metal); const ant=new THREE.Mesh(new THREE.CylinderGeometry(0.03,0.03,1.6,4),M.dark); ant.position.set(wx(9),1.8,wx(11)); add(ant);
  prop(30,14,1.6,0.4,0.9,M.olive); prop(7,8,0.5,0.3,0.35,M.olive); prop(29,21,0.5,0.3,0.35,M.olive);
  const sewer=new THREE.Mesh(new THREE.TorusGeometry(0.7,0.08,6,16),M.metal); sewer.rotation.x=-Math.PI/2; sewer.position.set(wx(2),0.06,wx(2)); add(sewer);
  // compuerta de la excavación (20,26): cerrada con candados o abierta sobre el pozo
  const hole=new THREE.Mesh(new THREE.PlaneGeometry(1.7,1.7),new THREE.MeshBasicMaterial({color:0x050608})); hole.rotation.x=-Math.PI/2; hole.position.set(wx(20),0.05,wx(26)); add(hole);
  const slab=new THREE.Mesh(new THREE.BoxGeometry(1.7,0.18,1.7),M.metal); slab.receiveShadow=true; add(slab); const bar=new THREE.Mesh(new THREE.BoxGeometry(1.8,0.08,0.12),M.dark); add(bar);
  const post=new THREE.Mesh(new THREE.BoxGeometry(0.06,1.3,0.06),M.dark); post.position.set(wx(20)+1.1,0.65,wx(26)); add(post); const sign=new THREE.Mesh(new THREE.BoxGeometry(0.7,0.4,0.04),toon({color:0xd8c860})); sign.position.set(wx(20)+1.1,1.15,wx(26)); add(sign);
  baseHatch.slab=slab; baseHatch.bar=bar; baseHatch.hole=hole;
  add(halloFig.g); add(vidalFig.g); }
function baseSync(){ if(dynamicDoors.office)dynamicDoors.office.visible=!W.officeOpen; if(dynamicDoors.vault)dynamicDoors.vault.visible=!W.vaultOpen; if(dynamicDoors.yard)dynamicDoors.yard.visible=!!W.yardDoorClosed; if(barsMesh)barsMesh.visible=!W.cellOpen; vidalFig.g.visible=!!S.inCell;
  if(baseHatch.slab){ const o=W.hatchOpen; baseHatch.hole.visible=o; if(o){ baseHatch.slab.position.set(wx(20),0.95,wx(26)-0.85); baseHatch.slab.rotation.x=-1.35; baseHatch.bar.position.set(wx(20),1.25,wx(26)-1.6); baseHatch.bar.rotation.x=-1.35; } else { baseHatch.slab.position.set(wx(20),0.09,wx(26)); baseHatch.slab.rotation.x=0; baseHatch.bar.position.set(wx(20),0.22,wx(26)); baseHatch.bar.rotation.x=0; } } }
ZONES.base={id:'base',title:'BASE DE TARSIS',sub:'PATIO SUR',desc:'Vuelves al patio. Lluvia, luz de sodio y las rondas donde las dejaste.',src:MAPSRC_BASE,start:[2,2],outdoor:true,
  guards:GDEF,inter:INTER_BASE,solids:[[1,12],[3,17],[8,17]],exitTo:{galeria:[20,26]},
  lights:[[5.5,12.5,0xfff0c0,0.9],[3,17.5,0xffe8b0,0.8],[8.5,17.5,0xd0ffd0,0.7],[29.5,6.5,0xfff0c0,0.9],[27.5,9.5,0xfff0c0,0.6],[32,10,0xfff0c0,0.7],[31,13.5,0xff5040,0.5]],
  spots:[[18,0,9,14,7,0],[35,27,25,20,8,2]],props:baseProps,sync:baseSync};

// ---- galería de acceso a la excavación (bajo la compuerta del patio sur): antesala de la misión 2
const MAPSRC_GAL=[
"################",
"#......#.......#",
"#.U.l..#..l..c.#",
"#......#.......#",
"#......#.......#",
"####.###.#######",
"####.#...#######",
"####...l.#######",
"#####....#######",
"#ssss..ss.....l#",
"#ssss...ss.....#",
"#sss.l...sss...#",
"#ss..........s.#",
"#s...#####....s#",
"#.....l........#",
"#######BB#######",
"################"];
const GDEF_GAL=[
 {name:'Soldado de la galería',role:'excavación',nerve:2,loyal:1,wps:[[4,7],[8,7],[8,2],[12,2],[8,2],[8,7]],look:{uniform:0x4a5244,helmet:0x3a4a3a,rifle:true,hair:'#3a2a1a',hairStyle:'patillas'},
  q:{templo:[{f:0,t:'Ahí abajo no se baja sin orden. Ni con orden, si puedo.'},{f:2,t:'La blindada solo la abre Alarcón, y solo cuando "la carga" pide. Dicen que la semana que viene bajan al siguiente. Me da igual quién sea mientras no sea yo.',clue:'aleph'}],
     clave:[{f:0,t:'Yo no subo al despacho. Pregunta arriba.'}],llave:[{f:0,t:'Arriba. Ibarra. Aquí abajo no hay puertas que abrir.',clue:'llave'}]}},
];
const INTER_GAL=[
 {x:2,y:2,label:'E · SUBIR A LA BASE',f:()=>travel('base',[20,25],0)},
 {x:12,y:3,label:()=>S.ammoTaken.g?'':'E · COGER MUNICIÓN (6)',f:()=>{ S.ammoTaken.g=true; S.p.ammo+=6; updHud(); beep(1000,0.08,'square',0.04); }},
 {x:13,y:10,label:'E · LEER EL PARTE DE EXTRACCIÓN',f:()=>{ addClue('aleph'); openDialog('PARTE DE EXTRACCIÓN · ALEPH-07 · NOV 83','<p>CARGA: ESTABLE. RENDIMIENTO: 104 %. RUIDO: PERSISTENTE (NO MECÁNICO).</p><p>SUJETO LH-06: RETIRADO (SORDERA, AFASIA). PRÓXIMO SUJETO: LH-07, A LA ESPERA DE LA 4ª SESIÓN.</p><p>Firma: Alarcón. Al margen, a lápiz: "Vidal, J. — baja."</p>',[{t:'Cerrar',f:closeDialog}]); }},
 {x:7,y:15,label:'E · PUERTA BLINDADA · ALEPH-07',f:()=>{ addClue('aleph'); openDialog('PUERTA BLINDADA','<p>Acero de un palmo, sin cerradura por fuera. Rotulado a plantilla: <b>ALEPH-07 — SÓLO PERSONAL DEL PROGRAMA</b>. Se abre desde dentro.</p><p>Al apoyar la mano, el metal está tibio. Detrás, el zumbido sube y baja despacio, como alguien que respira dormido.</p><p>Control: «Ahí no, Cuttlas. Todavía no. Eso es la siguiente misión.»</p>',[{t:'Cerrar',f:closeDialog}]); }},
];
function galProps(add){
  const sign=new THREE.Mesh(new THREE.PlaneGeometry(1.6,0.5),toon({color:0xc8b850})); sign.position.set(wx(7.5),2.3,wx(15)-0.3); add(sign);
  const lamp=new THREE.Mesh(new THREE.BoxGeometry(0.5,0.2,0.3),toon({color:0x3fd080})); lamp.position.set(wx(7.5),2.8,wx(15)-0.3); add(lamp);
  prop(13,12,1.4,1.0,0.9,M.metal); const pipe=new THREE.Mesh(new THREE.CylinderGeometry(0.1,0.1,8,6),M.dark); pipe.rotation.z=Math.PI/2; pipe.position.set(wx(10),2.7,wx(12)); add(pipe);
  prop(2,12,0.9,0.5,0.9,M.rock); prop(12,6,1.1,0.6,0.8,M.rock); prop(1,14,0.7,0.4,0.6,M.rock);
  for(let k=0;k<4;k++){ const c=new THREE.Mesh(new THREE.BoxGeometry(0.06,0.06,T*9),M.dark); c.position.set(wx(4)-0.9+k*0.08,2.9,wx(9)); add(c); } }
ZONES.galeria={id:'galeria',title:'GALERÍA DE ACCESO',sub:'BAJO EL PATIO SUR · EXCAVACIÓN DE TARSIS',desc:'Roca de hace tres mil años, agua tibia y un zumbido que sube del fondo. La puerta blindada es la siguiente misión.',
  src:MAPSRC_GAL,start:[3,2],indoor:true,sky:0x050709,fog:0.042,fogOff:0.075,ambient:0x28343e,ambientI:0.9,guards:GDEF_GAL,inter:INTER_GAL,exitTo:{base:[2,2]},
  lights:[[7.5,14.6,0x60e0a0,1.0,9,1.4],[2.5,10,0x3a6a90,0.6,10,0.8],[12,11.5,0x3a6a90,0.5,9,0.8]],props:galProps,
  onEnter(){ if(!S.codecSeen.down){ S.codecSeen.down=true; setTimeout(()=>{ if(!uiOpen&&!S.over&&!cut)codec(CODEC.down); },1200); } }};

// ---- estado de los guardias por zona (se conserva al salir y al guardar)
function guardState(g){ return {x:g.x,z:g.z,fx:g.fx,fz:g.fz,wi:g.wi,dead:g.dead,down:g.down,fear:g.fear,hasKey:g.hasKey,stripped:!!g.stripped,ref:!!g.red}; }
function applyGuardState(list){ (list||[]).forEach((sg,i)=>{ let g=S.guards[i]; if(!g){ if(!sg.ref)return; g=mkGuard(REFDEF,true); S.guards.push(g); }
  Object.assign(g,{x:sg.x,z:sg.z,fx:sg.fx,fz:sg.fz,wi:sg.wi,dead:sg.dead,down:sg.down,fear:sg.fear,hasKey:sg.hasKey,stripped:!!sg.stripped}); g.state='patrol'; g.susp=0; g.held=false;
  if(g.dead||g.down>0){ S.bodies.push({x:g.x,z:g.z,dead:g.dead,g,carried:false,hidden:false,stripped:!!g.stripped}); g.fall=1; g.fig.g.rotation.z=Math.PI/2; g.fig.g.position.y=0.26; g.mark.visible=false; } g.fig.g.position.x=g.x; g.fig.g.position.z=g.z; }); }
function zoneSnapshot(){ return {guards:S.guards.map(guardState),dogs:S.dogs.filter(d=>!d.dead).length}; }
function leaveZone(keep){ if(!ZONE)return; if(keep)S.zoneState[ZONE.id]=zoneSnapshot(); S.guards.forEach(g=>{scene.remove(g.fig.g);scene.remove(g.mark);}); S.dogs.forEach(d=>scene.remove(d.fig.g)); S.guards=[]; S.dogs=[]; S.bodies=[]; if(S.p&&S.p.carry){S.p.carry.carried=false;S.p.carry=null;} unloadWorld(); }
// carga una zona: at = casilla de llegada [x,y] (por defecto el inicio de la zona), face = yaw de llegada
function enterZone(id,at,face,o){ o=o||{}; const z=ZONES[id]; if(!z)throw new Error('zona desconocida: '+id);
  leaveZone(!(o.fresh||o.noSave)); S.zone=id; setMap(z); buildWorld(z); INTER=z.inter||[]; flow=null;
  S.guards=(z.guards||[]).map(d=>mkGuard(d)); S.bodies=[]; S.dogs=[]; const st=S.zoneState[id]; if(st){ applyGuardState(st.guards); if(st.dogs&&id==='base')releaseDogs(st.dogs,true); }
  if(S.refPending&&id==='base'){ S.refPending=false; S.guards.push(mkGuard(REFDEF,true)); }
  const t=at||[start.x,start.y]; const P=S.p, C=S.c; P.x=wx(t[0]); P.z=wx(t[1]); P.moving=false;
  if(C){ let placed=false; for(const d of [[0,1],[1,0],[0,-1],[-1,0],[1,1],[-1,1],[1,-1],[-1,-1]]){ if(!solidT(t[0]+d[0],t[1]+d[1])){ C.x=wx(t[0]+d[0]); C.z=wx(t[1]+d[1]); placed=true; break; } } if(!placed){ C.x=P.x; C.z=P.z; } C.fig.g.position.set(C.x,0,C.z); C.carry=null; }
  if(face!==undefined&&face!==null)yaw=face; S.camH=undefined; if(z.sync)z.sync(); setPower(W.power); updObj(); }
// viaje entre zonas con fundido y pantalla de carga
function travel(to,at,face){ if(S.traveling||S.over)return; const z=ZONES[to]; if(!z)return; S.traveling=true; uiOpen=true; promptEl.hidden=true; const L=el('load'); el('loadTitle').textContent=z.title; el('loadSub').textContent=z.sub||''; fadeEl.style.opacity=1; beep(140,0.4,'sine',0.04,70);
  setTimeout(()=>{ L.hidden=false; enterZone(to,at,face); saveGame(z.title.charAt(0)+z.title.slice(1).toLowerCase());
    setTimeout(()=>{ L.hidden=true; fadeEl.style.opacity=0; uiOpen=false; S.traveling=false; flash(z.title,z.desc||'',6); if(z.onEnter)z.onEnter(); },900); },1000); }
