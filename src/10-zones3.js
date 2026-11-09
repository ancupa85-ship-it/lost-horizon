'use strict';
// ---------- MISIÓN 3 «TARSIS»: la torre de comunicaciones (archivo con la lista completa, sala de radio y depósito de gasolina) y el perímetro
// (valla, marisma, embarcadero y carretera de Rota). Aquí se decide el final: huir por el mar, destruir el programa quemando el archivo,
// entregarse por la radio o salir con la lista completa hacia Nínive. El montacargas del templo sube al rincón suroeste del patio de la torre.
const MAPSRC_TOR=[
"############################",
"#..........l.........l.....#",
"#.....WWWWWWWWWWWWWW.......#",
"#.....W______W_____W..c....#",
"#.....W__z___W___z_W.......#",
"#.....W______W_____W..g....#",
"#.....WWWDWWWWWWWDWW.......#",
"#..........................#",
"#..c.......l......cc.......#",
"#.TT.......................#",
"#.TT.....cc...........l....#",
"#..........................D",
"#..........l...............#",
"#...cc...........ss........#",
"#.........................c#",
"#.l..........cc.......l....#",
"#..........................#",
"#....ss......c.............#",
"#..........................#",
"#.ss..........l............#",
"#.U........................#",
"############################"];
const LOOK_TOR={uniform:0x4a5244,helmet:0x3a4a3a,rifle:true,hair:'#2a1a10',hairStyle:'corto'};
const GDEF_TOR=[
 {name:'Soldado de la torre',role:'puertas',nerve:3,loyal:2,wps:[[9,8],[17,8],[17,7],[9,7]],look:Object.assign({},LOOK_TOR,{rank:1,hair:'#141010',hairStyle:'rapado'}),
  q:{clave:[{f:0,t:'El archivo es del sargento Ocaña. Yo no entro.'},{f:2,t:'La lista completa está en el archivo, la puerta del oeste. No son siete nombres: son todos. Ocaña la guarda como si fuera suya.',clue:'ocana'}],
     llave:[{f:0,t:'Por la puerta del este se sale al perímetro. De ahí, el mar o la carretera. Nadie vuelve de ninguno de los dos.'}],templo:[{f:0,t:'De eso no se habla arriba.'},{f:2,t:'Cuando abajo gritan, aquí la radio chisporrotea. Hay noches que la apagamos para no oírla.',clue:'fuente'}]}},
 {name:'Patrulla del patio oeste',role:'ronda',nerve:2,loyal:1,wps:[[3,8],[3,16],[10,16],[10,12]],look:Object.assign({},LOOK_TOR,{hair:'#5a3a1e',hairStyle:'rizado'}),
  q:{clave:[{f:0,t:'Pregunta a Ocaña. Si te deja.'}],llave:[{f:0,t:'Puerta del este. Hay un hombre en la verja y otro en la torreta del perímetro.',clue:'verja'}],templo:[{f:0,t:'No bajo. Nadie de arriba baja.'}]}},
 {name:'Patrulla del patio este',role:'ronda',nerve:3,loyal:1,wps:[[21,8],[25,8],[25,18],[21,18]],look:Object.assign({},LOOK_TOR,{scar:true,hair:'#b08a40',hairStyle:'flequillo'}),
  q:{clave:[{f:0,t:'En el archivo. Con Ocaña.'}],llave:[{f:0,t:'Por el este. Y por el agujero de la valla, en la marisma, si no quieres pasar por la verja. Lo abrieron los perros hace meses y nadie lo arregla.',clue:'valla'}],templo:[{f:0,t:'Combustible. Dicen.'}]}},
 {name:'Sargento Ocaña',role:'archivero',nerve:4,loyal:3,wps:[[8,3],[11,3],[11,5],[8,5]],look:{uniform:0x3f4a34,cap:0x2f3a2a,rank:2,glasses:true,hair:'#9a9a90',hairStyle:'corto',holster:true},
  q:{clave:[{f:0,t:'El archivo es de la Compañía. Usted no es de la Compañía.'},{f:2,t:'Carpeta gris, estante del fondo. Todos los nombres desde el sesenta y nueve. El suyo, el de ella, el mío. Lo guardo porque si no lo guardo yo lo quema otro.',clue:'ocana'},{f:4,t:'...Si lo quiere quemar, el depósito está fuera, al este. Hágalo y acabe con esto. Yo ya no puedo.',clue:'gasolina'}],
     llave:[{f:0,t:'Usted no sale de Tarsis. Nadie sale de Tarsis.'},{f:3,t:'La radio de al lado llama a la Compañía directamente. Si se entrega, le dan la cuarta sesión y una cama. Hay quien lo prefiere.',clue:'radio'}],templo:[{f:0,t:'Sé lo que hay. Lo anoto. No lo miro.'}]}},
 {name:'Radiotelegrafista',role:'sala de radio',nerve:1,loyal:0,wps:[[15,3],[18,3],[18,5],[15,5]],look:{uniform:0x5a6050,cap:0x4a5040,hair:'#8a3a1a',hairStyle:'tupe',plain:true},
  q:{clave:[{f:0,t:'La lista la tiene Ocaña, pared por medio. Yo solo transmito.'}],llave:[{f:0,t:'La radio llama a la Compañía: frecuencia fija, no se cambia. Descuelga y ya saben quién eres.',clue:'radio'},{f:1,t:'Si quieres irte de verdad: el embarcadero, en la marisma. El barquero no pregunta. La carretera de Rota tiene un control; la lista pasa si pasas tú.',clue:'embarcadero'}],templo:[{f:0,t:'Lo oigo en los auriculares cuando bajan a alguien. No es estática.',clue:'fuente'}]}},
 {name:'Centinela del depósito',role:'combustible',nerve:2,loyal:1,wps:[[22,4],[25,4],[25,7],[22,7]],look:Object.assign({},LOOK_TOR,{stubble:true,hair:'#3a2a1a',hairStyle:'patillas'}),
  q:{clave:[{f:0,t:'Yo guardo gasolina, no papeles.'}],llave:[{f:0,t:'La puerta del este está ahí mismo. El del perímetro te verá antes que yo.'}],templo:[{f:0,t:'Nada.'},{f:1,t:'El depósito alimenta el grupo de la torre y el cuadro eléctrico está en el archivo. Si eso arde, se va toda la luz de arriba.',clue:'gasolina'}]}},
 {name:'Guardia de la puerta este',role:'perímetro',nerve:3,loyal:2,wps:[[25,10],[25,12],[23,12],[23,10]],look:Object.assign({},LOOK_TOR,{helmet:0x1e2a30,rank:1,hair:'#2a1a10'}),
  q:{clave:[{f:0,t:'Ocaña.'}],llave:[{f:0,t:'Por aquí al perímetro. Luego la verja, y la torreta te sigue con el foco. Suerte.',clue:'verja'}],templo:[{f:0,t:'No.'}]}},
];
const torF={};
function torInter(){ return [
 {x:2,y:20,label:'E · EL MONTACARGAS',f:()=>openDialog('EL MONTACARGAS','<p>La jaula ha subido y el cable se ha quedado flojo. Abajo no hay nada que te espere, salvo el agua.</p><p>Roig: «Esto es arriba. Arriba es la última parte.»</p>',[{t:'Cerrar',f:closeDialog}])},
 {x:8,y:4,label:()=>S.clues.includes('lista3')?'':(W.burned?'E · LAS CENIZAS DEL ARCHIVO':'E · LEER LA LISTA COMPLETA'),f:()=>{ if(W.burned){ openDialog('CENIZAS','<p>La carpeta gris ya no existe. Nombres, fechas, el tuyo: humo. Nadie podrá contarlo con papeles. Tendrá que contarlo alguien.</p>',[{t:'Cerrar',f:closeDialog}]); return; }
   const had=S.clues.includes('lista3'); addClue('lista3'); openDialog('LISTA COMPLETA · PROGRAMA LOST HORIZON · 1969-1983','<p>Cuarenta y una fichas, no siete. Las primeras son de 1969: niños de la inclusa de Rota, "sujetos de calibración". Después soldados, después presos, después nadie que fuera a faltarle a nadie.</p><p><b>LH-07 CUTTLAS, A.</b> Fecha de ingreso: 1979. Nombre anterior: tachado tres veces, legible a contraluz. <b>LH-08 ROIG, E.</b>: propuesta, pendiente de firma. La firma es la de Alarcón. La fecha, mañana.</p><p>Al final, una nota de la Compañía: "Lista de distribución: ninguna. Destruir tras la cuarta sesión."</p>',[{t:'Cerrar',f:()=>{ closeDialog(); if(!had){ saveGame('Con la lista completa'); updObj(); setTimeout(()=>{ if(!uiOpen&&!S.over&&!cut)codec(CODEC.lista3); },600); } }}]); }},
 {x:11,y:4,label:()=>W.burned?'':(S.gas?'E · ROCIAR Y PRENDER EL ARCHIVO':'ARCHIVO · PARA QUEMARLO HACE FALTA GASOLINA (DEPÓSITO DEL ESTE)'),f:()=>{ if(W.burned||!S.gas)return;
   openDialog('QUEMAR EL ARCHIVO','<p>Cuarenta y una fichas, los partes de las sesiones, el cuadro eléctrico de la torre en la pared del fondo. Una lata de gasolina y el mechero de los cigarros.</p><p>'+(S.clues.includes('lista3')?'Ya has leído la lista. Si arde, solo quedará lo que tú recuerdes, y tú no recuerdas bien.':'No has leído la lista. Si arde, nadie sabrá nunca los nombres.')+'</p><p>Roig: «Si lo haces, lo haces con alarma. Y con toda la luz de arriba apagada.»</p>',[{t:'Prenderlo',f:()=>{ closeDialog(); burnArchive(); },cls:'danger'},{t:'Todavía no',f:closeDialog}]); }},
 {x:16,y:4,label:'E · LA RADIO · LLAMAR A LA COMPAÑÍA',f:()=>{ addClue('radio'); openDialog('LA RADIO DE LA COMPAÑÍA','<p>Frecuencia fija, el dial bloqueado con un precinto. Descuelgas y, antes de que digas nada, una voz: «LH-07. Le esperábamos.»</p><p>Si te entregas se acaba la noche: cuarta sesión, una cama, no recordar la cocina. Séneca dice que obedecer, cuando ya no cabe otra cosa, puede ser la forma de acusar.</p><p>Roig: «Si lo haces, yo también entro. Estoy en la lista igual.»</p>',[{t:'«Aquí LH-07. Vengan a por mí.» · ENTREGARSE',f:()=>{ closeDialog(); if(S.over)return; S.over=true; S.ending='seneca'; outro3('radio'); },cls:'danger'},{t:'Colgar',f:closeDialog}]); }},
 {x:23,y:6,label:()=>S.gas?'':'E · COGER GASOLINA DEL DEPÓSITO',f:()=>{ if(S.gas)return; S.gas=true; addClue('gasolina'); beep(600,0.1,'square',0.04); flash('GASOLINA','Una lata de veinte litros. El archivo de la torre tiene papel de catorce años y el cuadro eléctrico en la pared.',6); updObj(); }},
 {x:27,y:11,label:'E · PUERTA ESTE · AL PERÍMETRO',f:()=>travel('perimetro',[1,8],-Math.PI/2)},
]; }
// quemar el archivo: alarma, llamas, y a los cinco segundos el fuego llega al cuadro eléctrico y se va la luz de la torre y del perímetro
function burnArchive(){ if(W.burned)return; W.burned=true; S.burnT=5; addClue('fuego'); beep(90,1.2,'sawtooth',0.1,40); torSync(); raiseAlarm({x:S.p.x,z:S.p.z});
  flash('EL ARCHIVO ARDE','Catorce años de papel prenden a la vez. Los guardias vienen hacia el humo. Dentro de poco, el fuego llegará al cuadro eléctrico.',7); saveGame('Archivo en llamas'); updObj();
  setTimeout(()=>{ if(!S.over&&!uiOpen&&!cut)codec(CODEC.fuego); },1500); }
function torTick(dt){ if(torF.fire){ const on=!!W.burned; torF.fire.visible=on; if(on){ torF.fireL.intensity=1.6+Math.sin(S.t*17)*0.5+Math.sin(S.t*7.3)*0.4; torF.fire.children.forEach((m,i)=>{ m.scale.y=0.8+0.4*Math.sin(S.t*9+i*1.7); }); } }
  if(W.burned&&S.burnT>0){ S.burnT-=dt; if(S.burnT<=0&&W.power){ setPower(false); flash('SE VA LA LUZ','El fuego ha llegado al cuadro eléctrico. La torre y el perímetro se quedan a oscuras: nadie va a arreglarlo esta noche.',7); beep(60,1.5,'sawtooth',0.08,20); } } }
function torProps(add){
  // la torre de comunicaciones sobre el edificio: mástil, travesaños y la luz roja de cabeza
  const mast=new THREE.Mesh(new THREE.CylinderGeometry(0.12,0.3,14,6),M.metal); mast.position.set(wx(13),3+7,wx(4)); add(mast);
  for(let k=0;k<4;k++){ const bar=new THREE.Mesh(new THREE.BoxGeometry(2.4-k*0.4,0.08,0.08),M.dark); bar.position.set(wx(13),5+k*2.6,wx(4)); bar.rotation.y=k*0.6; add(bar); }
  const red=new THREE.Mesh(new THREE.SphereGeometry(0.22,8,6),new THREE.MeshBasicMaterial({color:0xff3030})); red.position.set(wx(13),17.2,wx(4)); add(red); torF.red=red;
  const rL=new THREE.PointLight(0xff3030,0.8,30,1.2); rL.position.set(wx(13),16.8,wx(4)); add(rL); torF.redL=rL;
  // rótulos de las puertas: ARCHIVO (oeste) y RADIO (este)
  const sA=new THREE.Mesh(new THREE.PlaneGeometry(1.4,0.45),toon({color:0xd8c860})); sA.position.set(wx(9),2.9,wx(6)+1.05); add(sA);
  const sR=new THREE.Mesh(new THREE.PlaneGeometry(1.4,0.45),toon({color:0x80c0e0})); sR.position.set(wx(17),2.9,wx(6)+1.05); add(sR);
  // archivo: estanterías, la carpeta gris, el cuadro eléctrico
  prop(7,3,0.8,2.2,0.6,M.metal); prop(8,3,0.8,2.2,0.6,M.metal); prop(11,3,0.8,2.2,0.6,M.metal); prop(12,3,0.8,2.2,0.6,M.metal);
  prop(8,5,1.4,0.8,0.7,M.wood); prop(8,5,0.5,0.06,0.35,toon({color:0x9a9a9a}),0.8);
  const cuadro=new THREE.Mesh(new THREE.BoxGeometry(0.9,1.1,0.25),M.dark); cuadro.position.set(wx(12)+0.6,1.6,wx(4)); add(cuadro); const led=new THREE.Mesh(new THREE.BoxGeometry(0.1,0.1,0.05),new THREE.MeshBasicMaterial({color:0x40ff60})); led.position.set(wx(12)+0.6,1.9,wx(4)-0.15); add(led);
  // llamas (ocultas hasta que arde)
  const fire=new THREE.Group(); const fm=new THREE.MeshBasicMaterial({color:0xff7a20,transparent:true,opacity:0.85}); const fm2=new THREE.MeshBasicMaterial({color:0xffd060,transparent:true,opacity:0.7});
  for(let i=0;i<9;i++){ const f=new THREE.Mesh(new THREE.ConeGeometry(0.35+Math.random()*0.3,1.4+Math.random()*1.2,5),i%3?fm:fm2); f.position.set(wx(8+(i%4)*1.2)-0.6,0.9,wx(3+(i%2)*2)+(i%3-1)*0.4); fire.add(f); }
  fire.visible=false; add(fire); torF.fire=fire; const fL=new THREE.PointLight(0xff7a20,0,16,1.2); fL.position.set(wx(10),1.8,wx(4)); add(fL); torF.fireL=fL;
  // sala de radio: mesa, equipos, auriculares
  prop(16,3,2.2,0.8,0.8,M.metal); prop(16,3,1.6,0.6,0.5,M.dark,0.8); for(let k=0;k<3;k++){ const d=new THREE.Mesh(new THREE.BoxGeometry(0.1,0.1,0.05),new THREE.MeshBasicMaterial({color:k?0x40ff60:0xff8040})); d.position.set(wx(16)-0.5+k*0.5,1.25,wx(3)+0.3); add(d); }
  prop(18,5,0.7,0.5,0.7,M.dark);
  // depósito de gasolina: tanque cilíndrico y latas
  const tank=new THREE.Mesh(new THREE.CylinderGeometry(0.9,0.9,2.2,10),M.olive); tank.rotation.z=Math.PI/2; tank.position.set(wx(23),1.0,wx(5)); add(tank);
  prop(23,6,0.4,0.5,0.3,toon({color:0xb03020})); prop(24,6,0.4,0.5,0.3,toon({color:0xb03020}),0); const sg=new THREE.Mesh(new THREE.PlaneGeometry(1.2,0.4),toon({color:0xd8c860})); sg.position.set(wx(23),2.1,wx(5)+1.05); add(sg);
  // montacargas en el rincón suroeste: jaula abierta
  for(const [dx,dz] of [[-0.9,-0.9],[0.9,-0.9],[-0.9,0.9],[0.9,0.9]]){ const p=new THREE.Mesh(new THREE.BoxGeometry(0.08,3.2,0.08),M.metal); p.position.set(wx(2)+dx,1.6,wx(20)+dz); add(p); }
  const roof=new THREE.Mesh(new THREE.BoxGeometry(2,0.1,2),M.metal); roof.position.set(wx(2),3.2,wx(20)); add(roof); const lamp=new THREE.Mesh(new THREE.BoxGeometry(0.4,0.15,0.3),toon({color:0xffd080})); lamp.position.set(wx(2),3.05,wx(20)); add(lamp);
  // rótulo de la puerta este
  const sE=new THREE.Mesh(new THREE.PlaneGeometry(1.4,0.45),toon({color:0xd8c860})); sE.position.set(wx(27)-1.05,2.6,wx(11)); sE.rotation.y=-Math.PI/2; add(sE);
  prop(5,13,0.9,0.5,0.9,M.olive); prop(20,15,0.9,0.5,0.9,M.olive); }
function torSync(){ if(torF.fire){ torF.fire.visible=!!W.burned; torF.fireL.intensity=W.burned?1.6:0; } }
ZONES.torre={id:'torre',title:'LA TORRE',sub:'CENTRO DE COMUNICACIONES Y ARCHIVO · SUPERFICIE',desc:'El patio de la torre: la zona más vigilada de Tarsis. En el edificio, el archivo (oeste) y la radio (este). La puerta del este da al perímetro.',
  src:MAPSRC_TOR,start:[2,20],outdoor:true,guards:GDEF_TOR,inter:torInter(),exitTo:{perimetro:[27,11]},
  lights:[[9.5,4,0xfff0c0,0.9,9,2.6],[16.5,4,0xd0e8ff,0.9,9,2.6],[23.5,5.5,0xfff0c0,0.7],[2.5,20.5,0xffd080,0.9,6,3.0],[26,11,0xfff0c0,0.8]],
  spots:[[14,0,13,11,8,0],[27,21,20,15,7,2]],props:torProps,sync:torSync,tick:torTick,
  onEnter(){ saveGame('En la torre'); }};

// ---- el perímetro: la valla con su verja y su agujero, la marisma, la torreta con el foco, el embarcadero y la carretera de Rota
const MAPSRC_PER=[
"################################",
"#....W....................l..G.#",
"#....W.........ss..............#",
"#.l..W........sss.......l......#",
"#....W....c....ss..............#",
"#....W.........................#",
"#....W....ss..........sss......#",
"#....W...sss....l.....sss......#",
"D....D..............ss.......s.#",
"#....W.......c.........ssss..Gs#",
"#....W.................sss...s.#",
"#.l..W.....ss.......l..........#",
"#....W....sss..................#",
"#.........sss.......c..........#",
"#....W.........................#",
"#....W....l....ss........l.....#",
"#....W........sss..............#",
"################################"];
const GDEF_PER=[
 {name:'Guardia de la verja',role:'valla',nerve:3,loyal:2,wps:[[6,8],[6,6],[7,10],[6,8]],look:Object.assign({},LOOK_TOR,{helmet:0x1e2a30,rank:1,hair:'#141010',hairStyle:'rapado'}),
  q:{clave:[{f:0,t:'Aquí no hay listas. Hay barro.'}],llave:[{f:0,t:'La verja la cruzo yo. Tú no.'},{f:2,t:'Hay un agujero en la valla más al sur. Lo abrieron los perros. Yo no lo he visto, ¿entiendes?',clue:'valla'}],templo:[{f:0,t:'No.'}]}},
 {name:'Patrulla de la marisma',role:'ronda',nerve:2,loyal:1,wps:[[12,3],[20,3],[20,13],[12,13]],look:Object.assign({},LOOK_TOR,{hair:'#b08a40',hairStyle:'flequillo',stubble:true}),
  q:{clave:[{f:0,t:'Lo que sea, en la torre.'}],llave:[{f:0,t:'El embarcadero, al este. El barquero sale a las cuatro llueva o no. La carretera, al noreste, con control.',clue:'embarcadero'}],templo:[{f:0,t:'Desde aquí se oye, con viento del sur. Como un coro.',clue:'fuente'}]}},
 {name:'Centinela del embarcadero',role:'bote',nerve:2,loyal:0,wps:[[27,8],[27,11],[24,11],[24,8]],look:Object.assign({},LOOK_TOR,{hair:'#5a3a1e',hairStyle:'rizado',plain:true}),
  q:{clave:[{f:0,t:'Nada de papeles aquí.'}],llave:[{f:0,t:'El bote es del barquero. Se va al mar y no pregunta nombres. Por eso lo cogen los que no lo tienen.',clue:'embarcadero'}],templo:[{f:0,t:'Mi hermano bajó. No subió. Yo no pregunto.'}]}},
 {name:'Control de la carretera',role:'Rota',nerve:4,loyal:3,wps:[[26,2],[22,2],[22,4],[26,4]],look:Object.assign({},LOOK_TOR,{scar:true,rank:2,hair:'#9a9a90',hairStyle:'corto'}),
  q:{clave:[{f:0,t:'Por aquí no pasa papel de la Compañía.'}],llave:[{f:0,t:'La carretera va a Rota. De Rota, a donde quieras. Pero por este control pasas conmigo delante o no pasas.'}],templo:[{f:0,t:'No.'}]}},
];
const perF={};
const INTER_PER=[
 {x:0,y:8,label:'E · VOLVER A LA TORRE',f:()=>travel('torre',[26,11],Math.PI/2)},
 {x:5,y:13,label:'E · LA VALLA ROTA',f:()=>{ addClue('valla'); openDialog('LA VALLA ROTA','<p>Alambre doblado hacia fuera, a la altura de un perro grande. Pelo gris en las púas. Nadie lo ha arreglado en meses.</p><p>Por aquí no hace falta pasar por la verja.</p>',[{t:'Cerrar',f:closeDialog}]); }},
 {x:26,y:10,label:'E · LA NOTA DEL BARQUERO',f:()=>{ addClue('embarcadero'); openDialog('NOTA CLAVADA EN EL POSTE','<p>"Salgo a las cuatro. No pregunto. No vuelvo. — M."</p><p>Debajo, a lápiz y con otra letra: "A Rota se va por la carretera. Al mar se va a nada."</p>',[{t:'Cerrar',f:closeDialog}]); }},
 {x:29,y:9,label:'E · SUBIR AL BOTE · HUIR POR EL MAR',f:()=>openDialog('EL EMBARCADERO','<p>Un bote con motor fueraborda y un hombre que no te mira. El mar, detrás, es del color de la radio apagada.</p><p>Si subes, Jonás vuelve al mar: nadie sabrá nunca lo que has visto, y tú tampoco por mucho tiempo.</p>'+(S.clues.includes('lista3')?'<p>Llevas la lista completa. En el mar no hay a quién dársela.</p>':''),[{t:'Subir al bote · HUIR',f:()=>{ closeDialog(); if(S.over)return; S.over=true; S.ending='mar'; outro3('bote'); },cls:'danger'},{t:'Todavía no',f:closeDialog}])},
 {x:29,y:1,label:()=>S.clues.includes('lista3')?'E · LA CARRETERA DE ROTA · IR A NÍNIVE A CONTARLO':'E · LA CARRETERA DE ROTA',f:()=>openDialog('LA CARRETERA DE ROTA','<p>Asfalto mojado y un cartel con la flecha: ROTA 14. Más allá de Rota, Cádiz; más allá, cualquiera que quiera escuchar.</p>'+(S.clues.includes('lista3')?'<p>Llevas la lista completa. Cuarenta y un nombres. Nínive es grande y no sabes si querrá oírlo; tampoco lo sabía Jonás.</p>':'<p>No llevas la lista. Puedes contarlo, pero lo que cuentes será la palabra de un hombre al que borraron tres veces.</p>'),[{t:(S.clues.includes('lista3')?'Ir a contarlo · NÍNIVE':'Echar a andar'),f:()=>{ closeDialog(); if(S.over)return; S.over=true; S.ending='ninive'; outro3('carretera'); },cls:'danger'},{t:'Todavía no',f:closeDialog}])},
];
function perProps(add){
  // marisma: láminas de agua sobre las casillas 's' (fuera no se pintan solas) y cañas
  for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++)if(MAPSRC_PER[y][x]==='s'){ const f=new THREE.Mesh(new THREE.PlaneGeometry(T,T),M.water); f.rotation.x=-Math.PI/2; f.position.set(wx(x),0.03,wx(y)); add(f);
    if((x*7+y*3)%3===0){ const r=new THREE.Mesh(new THREE.CylinderGeometry(0.03,0.05,1.4,4),toon({color:0x6a7a40})); r.position.set(wx(x)+(x%2?0.6:-0.5),0.7,wx(y)+(y%2?0.5:-0.6)); add(r); } }
  // valla: alambre entre los postes 'W' (la pared ya es sólida; esto es la cara)
  for(let y=1;y<ROWS-1;y++)if(MAPSRC_PER[y][5]==='W'){ for(let k=0;k<3;k++){ const w=new THREE.Mesh(new THREE.BoxGeometry(0.04,0.04,T),M.dark); w.position.set(wx(5)+0.95,0.8+k*0.8,wx(y)); add(w); } }
  // el agujero de la valla: alambre doblado
  const bent=new THREE.Mesh(new THREE.BoxGeometry(0.06,1.2,0.06),M.dark); bent.position.set(wx(5)+0.3,0.5,wx(13)); bent.rotation.z=1.1; add(bent);
  // torreta de vigilancia con el foco (en el extremo norte de la marisma)
  for(const [dx,dz] of [[-0.8,-0.8],[0.8,-0.8],[-0.8,0.8],[0.8,0.8]]){ const p=new THREE.Mesh(new THREE.BoxGeometry(0.12,6,0.12),M.wood); p.position.set(wx(16)+dx,3,wx(0)+1.6+dz); add(p); }
  const cab=new THREE.Mesh(new THREE.BoxGeometry(2.2,1.4,2.2),M.wood); cab.position.set(wx(16),6.5,wx(0)+1.6); add(cab);
  // embarcadero: tablas, postes, el bote
  for(let k=0;k<4;k++){ const pl=new THREE.Mesh(new THREE.BoxGeometry(T,0.15,1.6),M.wood); pl.position.set(wx(26+k),0.2,wx(9)); add(pl); }
  for(const x of [26,28]){ const p=new THREE.Mesh(new THREE.BoxGeometry(0.2,1.2,0.2),M.wood); p.position.set(wx(x),0.6,wx(9)+0.9); add(p); }
  const boat=new THREE.Mesh(new THREE.BoxGeometry(2.6,0.7,1.2),toon({color:0x3a4a6a})); boat.position.set(wx(30),0.35,wx(9)+0.6); add(boat); const motor=new THREE.Mesh(new THREE.BoxGeometry(0.4,0.6,0.4),M.dark); motor.position.set(wx(30)+1.1,0.7,wx(9)+0.6); add(motor);
  const note=new THREE.Mesh(new THREE.PlaneGeometry(0.4,0.5),toon({color:0xe8e0c0})); note.position.set(wx(26),1.0,wx(10)-0.9); add(note);
  // carretera: asfalto, cartel y barrera del control
  const road=new THREE.Mesh(new THREE.PlaneGeometry(T*2,T*8),toon({color:0x2a2c30})); road.rotation.x=-Math.PI/2; road.position.set(wx(29),0.02,wx(1)+T*3); add(road);
  const post=new THREE.Mesh(new THREE.BoxGeometry(0.08,2.6,0.08),M.metal); post.position.set(wx(28),1.3,wx(1)); add(post); const sign=new THREE.Mesh(new THREE.BoxGeometry(1.4,0.5,0.05),toon({color:0xe8e8e0})); sign.position.set(wx(28),2.3,wx(1)); add(sign);
  const bar=new THREE.Mesh(new THREE.BoxGeometry(0.1,0.1,T*1.6),toon({color:0xd04040})); bar.position.set(wx(27),1.0,wx(2)); add(bar);
  prop(24,2,1.2,0.9,0.8,M.olive); }
ZONES.perimetro={id:'perimetro',title:'EL PERÍMETRO',sub:'VALLA Y MARISMA · EMBARCADERO · CARRETERA DE ROTA',desc:'La valla, la marisma y, al fondo, las dos salidas de Tarsis: el bote del embarcadero y la carretera de Rota. El foco de la torreta barre el barro.',
  src:MAPSRC_PER,start:[1,8],outdoor:true,guards:GDEF_PER,inter:INTER_PER,exitTo:{torre:[0,8]},
  lights:[[26.5,9.5,0xffe0a0,0.9],[29,1.5,0xfff0c0,0.9],[16,1.5,0xfff4d0,0.6]],spots:[[16,1,16,8,7,1]],props:perProps,
  onEnter(){ saveGame('En el perímetro'); if(!S.codecSeen.m3per){ S.codecSeen.m3per=true; setTimeout(()=>{ if(!uiOpen&&!S.over&&!cut)codec(CODEC.m3per); },1200); } }};
// objetivo de la misión 3: la torre (lista, gasolina, radio) → puerta este → el bote o la carretera
function objective3(){ const lista=S.clues.includes('lista3');
  if(S.zone==='perimetro')return {step:3,text:lista?'ELIGE LA SALIDA: LA CARRETERA DE ROTA (NORESTE) CON LA LISTA, O EL BOTE (ESTE)':'ELIGE LA SALIDA: EL BOTE DEL EMBARCADERO (ESTE) O LA CARRETERA DE ROTA (NORESTE)',x:lista?29:29,y:lista?1:9};
  if(!lista&&!W.burned)return {step:1,text:'ENTRA EN LA TORRE: LA LISTA COMPLETA ESTÁ EN EL ARCHIVO (PUERTA OESTE)'+(S.gas?' · O QUÉMALO':''),x:9,y:6};
  return {step:2,text:(W.burned?'EL ARCHIVO ARDE: ':'')+'SAL POR LA PUERTA ESTE AL PERÍMETRO'+(W.burned||!S.gas?'':' · O VUELVE Y QUEMA EL ARCHIVO'),x:27,y:11}; }
