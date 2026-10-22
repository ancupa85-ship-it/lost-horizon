'use strict';
// ---------- CÓDEC (retratos pixelados, texto mecanografiado)
const PORT={
 cuttlas:["................","....xxxxxxxx....","...xxxxxxxxxx...","...xxhhhhhhxx...","...xhhhhhhhhx...","...xhhkhhkhhx...","...xhhhhhhhhx...","....hhhnnhhh....","....hhhhhhhh....","....hhsssshh....",".....hhhhhh.....","......uuuu......","....uuuuuuuu....","...uuuuuuuuuu...","..uuuuuuuuuuuu..",".uuuuuuuuuuuuuu."],
 control:["................","................","......####......",".....######.....","....########....","....########....","....########....",".....######.....","......####......","....########....","..############..",".##############.","################","################","################","################"],
 fuente: ["................","................","................",".......ff.......","......ffff......",".....ffffff.....","....ffffffff....","...ffffffffff...","..ffffffffffff..","...ffffffffff...","....ffffffff....",".....ffffff.....","......ffff......",".......ff.......","................","................"],
};
const PPAL={x:'#2a1a10',h:'#e8b890',k:'#111',n:'#c08868',s:'#a07858',u:'#3a4238','#':'#143a28',f:'#7fd4a0'};
function drawPort(cv,key,t){ const x=cv.getContext('2d'); x.fillStyle='#031a10'; x.fillRect(0,0,32,32); const rows=PORT[key]; const ox=8,oy=4; rows.forEach((r,j)=>{for(let i=0;i<16;i++){const ch=r[i]; if(ch==='.')continue; x.fillStyle=PPAL[ch]||'#fff'; if(key==='control'&&Math.random()<0.25)x.fillStyle='#0f2a1c'; if(key==='fuente')x.fillStyle=(i+j+((t*6)|0))%3?'#3a8a60':'#9ff0c0'; x.fillRect(ox+i,oy+j,1,1);}}); x.fillStyle='rgba(0,0,0,.35)'; for(let y=0;y<32;y+=2)x.fillRect(0,y,32,1); }
const codecEl=el('codec'); let codecQ=null, codecIdx=0, typeT=0, typed=0, codecDone=null;
function codec(lines,done){ codecQ=lines; codecIdx=0; typed=0; codecDone=done||null; uiOpen=true; codecEl.hidden=false; el('top').style.opacity=0.25; beep(1800,0.06,'sine',0.04); setTimeout(()=>beep(1800,0.06,'sine',0.04),120); setTimeout(()=>beep(1800,0.06,'sine',0.04),240); showCodecLine(); }
function showCodecLine(){ const L=codecQ[codecIdx]; el('cWho').textContent=L.who; el('cFreq').textContent=L.freq||'141.12'; drawPort(el('pL'),'cuttlas',0); drawPort(el('pR'),L.port||'control',0); typed=0; typeT=0; el('cTxt').innerHTML=''; }
function codecTick(dt){ if(!codecQ)return; const L=codecQ[codecIdx]; drawPort(el('pR'),L.port||'control',S.t||0); if(typed<L.text.length){ typeT+=dt; while(typeT>0.022&&typed<L.text.length){typeT-=0.022;typed++; if(typed%3===0)beep(L.port==='fuente'?220:900,0.02,'square',0.012);} el('cTxt').innerHTML='<span class="cur">'+L.text.slice(0,typed)+'</span>'; } }
function codecNext(){ if(!codecQ)return; const L=codecQ[codecIdx]; if(typed<L.text.length){typed=L.text.length; el('cTxt').innerHTML='<span class="cur">'+L.text+'</span>'; return;} codecIdx++; if(codecIdx>=codecQ.length){ codecQ=null; codecEl.hidden=true; uiOpen=false; el('top').style.opacity=1; const d=codecDone; codecDone=null; if(d)d(); return; } showCodecLine(); }
const CODEC={
 start:[{who:'CONTROL',text:'Cuttlas. Estás en el patio norte. El edificio bajo, con la antena, es comunicaciones. El archivo está detrás, puerta blindada.'},{who:'CONTROL',text:'Quiero el expediente LH-07. No hables con nadie que no haga falta. No leas lo que no es tuyo.'},{who:'CUTTLAS',text:'...¿Y qué es mío?'},{who:'CONTROL',text:'Esta noche, el expediente. Corto.'}],
 alarm:[{who:'CONTROL',text:'Te han visto. Ahora eres ruido. Si te cogen, no te conocemos; si sales, tampoco.'}],
 warn:[{who:'CONTROL',text:'Llevas demasiado dentro. A las 02:19 sueltan la perrera: siete perros. No les ganas corriendo; o los paras o te paran.'}],
 dogs:[{who:'CONTROL',text:'Perrera abierta. Siete. Si te cogen vivo, lo que venga después no es cosa nuestra.'}],
 cell:[{who:'CONTROL',text:'...'},{who:'———',freq:'000.00',port:'fuente',text:'te han bajado un piso. otro más y me oyes sin radio. el que reza fuera tiene un hermano aquí conmigo.'}],
 vault:[{who:'CONTROL',text:'Puerta abierta. Coge el expediente y sal por la puerta sureste. No lo leas, Cuttlas. Eso no está en la misión.'}],
 file:[{who:'CONTROL',text:'...Te dije que no lo leyeras.'},{who:'CONTROL',text:'Da igual. Mañana no te acordarás. Sal por la puerta sureste y entrégalo. Corto.'},{who:'———',freq:'000.00',port:'fuente',text:'de profundis clamavi ad te. te oigo contar. tú también cuentas como ellos. baja. baja. baja.'},{who:'CUTTLAS',freq:'000.00',port:'fuente',text:'¿Quién habla?'},{who:'———',freq:'000.00',port:'fuente',text:'la que también clama. nadie la oye. tú sí.'}],
};
