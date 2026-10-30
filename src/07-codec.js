'use strict';
// ---------- CÓDEC (retratos pixelados, texto mecanografiado)
const PORT={
 cuttlas:["................","....xxxxxxxx....","...xxxxxxxxxx...","...xxhhhhhhxx...","...xhhhhhhhhx...","...xhhkhhkhhx...","...xhhhhhhhhx...","....hhhnnhhh....","....hhhhhhhh....","....hhsssshh....",".....hhhhhh.....","......uuuu......","....uuuuuuuu....","...uuuuuuuuuu...","..uuuuuuuuuuuu..",".uuuuuuuuuuuuuu."],
 roig:   ["................","....xxxxxxxx....","...xxxxxxxxxx...","..xxxhhhhhhxxx..","..xxhhhhhhhhxx..","..xxhhkhhkhhxx..","..xxhhhhhhhhxx..","..xxhhhnnhhhxx..","..xxhhhhhhhhxx..","..xxhhsshhhhxx..","..xx.hhhhhh.xx..","..x...uuuu...x..","....uuuuuuuu....","...uuuuuuuuuu...","..uuuuuuuuuuuu..",".uuuuuuuuuuuuuu."],
 control:["................","................","......####......",".....######.....","....########....","....########....","....########....",".....######.....","......####......","....########....","..############..",".##############.","################","################","################","################"],
 fuente: ["................","................","................",".......ff.......","......ffff......",".....ffffff.....","....ffffffff....","...ffffffffff...","..ffffffffffff..","...ffffffffff...","....ffffffff....",".....ffffff.....","......ffff......",".......ff.......","................","................"],
};
const PPAL={x:'#2a1a10',h:'#e8b890',k:'#111',n:'#c08868',s:'#a07858',u:'#3a4238','#':'#143a28',f:'#7fd4a0'};
function drawPort(cv,key,t){ const x=cv.getContext('2d'); x.fillStyle='#031a10'; x.fillRect(0,0,32,32); const rows=PORT[key]; const ox=8,oy=4; rows.forEach((r,j)=>{for(let i=0;i<16;i++){const ch=r[i]; if(ch==='.')continue; x.fillStyle=PPAL[ch]||'#fff'; if(key==='control'&&Math.random()<0.25)x.fillStyle='#0f2a1c'; if(key==='fuente')x.fillStyle=(i+j+((t*6)|0))%3?'#3a8a60':'#9ff0c0'; x.fillRect(ox+i,oy+j,1,1);}}); x.fillStyle='rgba(0,0,0,.35)'; for(let y=0;y<32;y+=2)x.fillRect(0,y,32,1); }
const codecEl=el('codec'); let codecQ=null, codecIdx=0, typeT=0, typed=0, codecDone=null;
function codec(lines,done){ codecQ=lines; codecIdx=0; typed=0; codecDone=done||null; uiOpen=true; codecEl.hidden=false; el('top').style.opacity=0.25; beep(1800,0.06,'sine',0.04); setTimeout(()=>beep(1800,0.06,'sine',0.04),120); setTimeout(()=>beep(1800,0.06,'sine',0.04),240); showCodecLine(); }
function showCodecLine(){ const L=codecQ[codecIdx]; el('cWho').textContent=L.who; el('cFreq').textContent=L.freq||'141.12'; drawPort(el('pL'),(S.p&&S.p.name==='ROIG')?'roig':'cuttlas',0); drawPort(el('pR'),L.port||'control',0); typed=0; typeT=0; el('cTxt').innerHTML=''; }
function codecTick(dt){ if(!codecQ)return; const L=codecQ[codecIdx]; drawPort(el('pR'),L.port||'control',S.t||0); if(typed<L.text.length){ typeT+=dt; while(typeT>0.022&&typed<L.text.length){typeT-=0.022;typed++; if(typed%3===0)beep(L.port==='fuente'?220:900,0.02,'square',0.012);} el('cTxt').innerHTML='<span class="cur">'+L.text.slice(0,typed)+'</span>'; } }
function codecNext(){ if(!codecQ)return; const L=codecQ[codecIdx]; if(typed<L.text.length){typed=L.text.length; el('cTxt').innerHTML='<span class="cur">'+L.text+'</span>'; return;} codecIdx++; if(codecIdx>=codecQ.length){ codecQ=null; codecEl.hidden=true; uiOpen=false; el('top').style.opacity=1; const d=codecDone; codecDone=null; if(d)d(); return; } showCodecLine(); }
const CODEC={
 start:[{who:'CONTROL',text:'Cuttlas. Estás en el patio norte. El edificio bajo, con la antena, es comunicaciones. El archivo está detrás, puerta blindada.'},{who:'CONTROL',text:'Quiero el expediente LH-07. Está en el archivo, dentro del despacho de Alarcón: el edificio del oeste. La llave del despacho la lleva el cabo Ibarra, que ronda el patio norte.'},{who:'CONTROL',text:'El archivo tiene un teclado. La clave no te la voy a dar porque no la tengo: sácasela a la base. No hables con nadie que no haga falta. No leas lo que no es tuyo.'},{who:'CUTTLAS',text:'...¿Y qué es mío?'},{who:'CONTROL',text:'Esta noche, el expediente. Corto.'}],
 alarm:[{who:'CONTROL',text:'Te han visto. Ahora eres ruido. Si te cogen, no te conocemos; si sales, tampoco.'}],
 warn:[{who:'CONTROL',text:'Llevas demasiado dentro. A las 02:19 sueltan la perrera: siete perros. No les ganas corriendo; o los paras o te paran.'}],
 dogs:[{who:'CONTROL',text:'Perrera abierta. Siete. Si te cogen vivo, lo que venga después no es cosa nuestra.'}],
 cell:[{who:'CONTROL',text:'...'},{who:'———',freq:'000.00',port:'fuente',text:'te han bajado un piso. otro más y me oyes sin radio. el que reza fuera tiene un hermano aquí conmigo.'}],
 down:[{who:'CONTROL',text:'Estás bajo el patio. Eso no es esta noche, Cuttlas: mira lo que haya que mirar y sube. La puerta blindada del fondo no se abre desde fuera.'},{who:'———',freq:'000.00',port:'fuente',text:'más cerca. te oigo contar desde aquí. no bajes todavía: aún no sabes tu número.'}],
 vault:[{who:'CONTROL',text:'Puerta abierta. Coge el expediente y sal por la puerta sureste. No lo leas, Cuttlas. Eso no está en la misión.'}],
 file:[{who:'CONTROL',text:'...Te dije que no lo leyeras.'},{who:'CONTROL',text:'Da igual. Mañana no te acordarás. Sal por la puerta sureste y entrégalo. Corto.'},{who:'———',freq:'000.00',port:'fuente',text:'de profundis clamavi ad te. te oigo contar. tú también cuentas como ellos. baja. baja. baja.'},{who:'CUTTLAS',freq:'000.00',port:'fuente',text:'¿Quién habla?'},{who:'———',freq:'000.00',port:'fuente',text:'la que también clama. nadie la oye. tú sí.'}],
};

// ---------- RADIO (R): llamadas al estilo códec, con respuestas según el estado de la misión
function radioMenu(){ if(!started||uiOpen||S.over||cut)return; S.calls=S.calls||{control:0,roig:0,fuente:0};
  const opts=[{t:'141.12 · CONTROL',f:()=>{ closeDialog(); S.calls.control++; codec(controlLines()); }}];
  if(S.c)opts.push({t:'140.85 · ROIG'+(S.c.down>0?' · herida':''),f:()=>{ closeDialog(); S.calls.roig++; codec(roigLines()); }});
  if(!W.power||S.clues.includes('fuente')||S.capturedOnce)opts.push({t:'000.00 · ———',f:()=>{ closeDialog(); S.calls.fuente++; codec(fuenteLines()); }});
  opts.push({t:'Colgar',f:closeDialog}); openDialog('RADIO · ELIGE FRECUENCIA','<p>El auricular zumba. Nadie espera tu llamada y todos la cogen.</p>',opts); }
function controlLines(){ const me=S.p.name, n=S.calls.control, L=[]; const C=(t)=>L.push({who:'CONTROL',text:t}); const Y=(t)=>L.push({who:me,text:t});
  if(S.inCell){ C('No podemos sacarte. Oficialmente no estás ahí; oficialmente no estamos hablando.'); C('Habla con el cabo. Todo el mundo quiere algo, y el que reza quiere que alguien le escuche. Usa lo que hayas oído.'); }
  else if(S.dogs.some(d=>!d.dead)){ C('Los perros no entienden de sombras. Dispárales, apártalos de una patada o métete donde no quepan. No corras: corren mejor.'); }
  else if(!S.p.key&&!S.c.key&&!W.officeOpen){ C('La llave del despacho la lleva un cabo, Ibarra. Llega por detrás, agárralo y pregunta por la llave. Si se hace el sordo, aprieta. Aguanta tres.'); Y('¿Y si grita?'); C('Entonces habrás apretado cuatro.'); }
  else if(!W.vaultOpen){ C('El archivo pide cuatro cifras y Alarcón no apunta nada: reza. Lee lo que tenga en la mesa y escucha a quien le haya oído rezar.'); C('Y recuerda: ese hombre cuenta en latín.'); }
  else if(!S.p.file&&!S.c.file){ C('Dentro del archivo, el archivador. Coge LH-07 y no lo leas, '+(me==='ROIG'?'teniente':'Cuttlas')+'.'); }
  else if(S.base==='cierre'){ C('Base en cierre: han sellado la puerta entre patios y hay un refuerzo en la salida. Apaga el generador y pasa por la oscuridad, o pasa por encima de él.'); }
  else { C('Puerta sureste. Es lo único que te queda. '+(S.kill>0?'Deja los muertos donde están; la Compañía ya sabe que funcionas.':'Sin muertos. Así se sale de los sitios sin haber estado.')); }
  const extra=[
    ()=>{ C('¿Me oyes bien? Esta frecuencia no está en ningún manual. Está en el dorso de la caja. Siempre la tendrás ahí.'); },
    ()=>{ C('Guardo lo que haces cuando pasa algo importante. Si caes, vuelves al último punto. No preguntes cómo; yo tampoco lo sé.'); },
    ()=>{ Y('¿Quién eres?'); C('La voz que te dice adónde ir. Antes había otra. Tú la apagaste, o te la apagaron.'); },
    ()=>{ C('Si te pierdes, abre el cuaderno. Sí, el que tienes en la pantalla. No finjas que no lo ves.'); },
    ()=>{ C('Roig no figura en esta misión. No figura en ninguna. Cuídala; es la única que se acuerda de ti.'); },
  ]; extra[n%extra.length](); L.push({who:'CONTROL',text:'Corto.'}); return L; }
function roigLines(){ const me=S.p.name, R=S.c, n=S.calls.roig, L=[]; const RR=(t)=>L.push({who:'ROIG',port:'roig',freq:'140.85',text:t}); const Y=(t)=>L.push({who:me,freq:'140.85',text:t});
  if(me==='ROIG'){ L.push({who:'CUTTLAS',freq:'140.85',text:'...¿Roig? Soy yo. Estás hablando contigo misma. O conmigo. Da igual: pulsa X y vuelve.'}); return L; }
  if(R.down>0){ RR('...Estoy en el suelo. No me mires así, levántame luego. Sigo respirando y eso ya es más que la última vez.'); return L; }
  if(S.inCell){ RR('Estoy aquí dentro contigo. Nunca me dejas atrás, Cuttlas; ni cuando te lo pido.'); RR('El cabo escucha a Halloran. Mírala a ella cuando le hables a él.'); return L; }
  if(R.ammo===0)RR('Sin balas. Me quedan las manos y la mala leche. Si os ven, mantente cerca.');
  else if(R.ammo<=4)RR('Me quedan '+R.ammo+'. Después, las manos.');
  else if(S.cOrder==='wait')RR('Estoy donde me dejaste, agachada. Si disparo es porque os han visto. Si me quieres detrás, ya sabes cómo pedirlo.');
  else RR('Estoy a dos pasos. Si disparo es porque os han visto; si no disparo, agradécemelo luego.');
  if(S.kill>0&&!S.flashSeen.roigKill){ S.flashSeen.roigKill=true; RR('Has matado a uno. Antes no lo hacías. O sí, y no te acuerdas. Yo sí me acuerdo.'); }
  else if(!W.vaultOpen&&(S.clues.includes('peris')||S.clues.includes('c130'))&&!S.clues.includes('roma')&&!S.clues.includes('vulgata')&&n>=1){ RR('De profundis. Mi madre lo rezaba: es el ciento treinta... en nuestra Biblia. Alarcón no usa la nuestra. La suya va uno por detrás.'); addClue('roma'); }
  else { const extra=['¿Has probado a cambiar a mí? Pulsa X. Lo sé: es raro oírmelo decir.','Cuando esto acabe te llevo a esa cocina que sueñas. Si existe. Si no, a otra.','Cuttlas: la luz de la tarde no existe aquí. Solo llueve. Lo digo por si te orientas por eso.','Hablas dormido. Cuentas. Siempre te paras en ciento veintinueve y vuelves a empezar.']; RR(extra[n%extra.length]); }
  return L; }
function fuenteLines(){ const n=S.calls.fuente; const F=(t)=>({who:'———',freq:'000.00',port:'fuente',text:t});
  const sets=[[F('baja.'),F('te oigo contar. uno. dos. ciento veintinueve. vuelves a empezar.')],[F('el que reza fuera cuenta igual que yo. su hermano cuenta aquí abajo.')],[F('tienes una cocina dentro. luz de tarde. yo también tenía. me la quitaron para que diera luz a otros.')],[F('cuando apagan el generador no me callo. descanso. tú también deberías.')],[F('ella escribió que sufro. la encerraron por escribirlo. tú lo leíste. a ti te borrarán.')]];
  const s=sets[n%sets.length]; if(S.p.name==='ROIG'&&n===0)s.push({who:'ROIG',freq:'000.00',text:'...Eso no es la radio.'}); return s; }
