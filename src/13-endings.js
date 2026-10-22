'use strict';
// ---------- FINALES
// «¿SNAKE? ¡SNAAAAAKE!»: estira la última vocal del nombre
function stretch(n){ let i=n.length-1; while(i>0&&!'AEIOU'.includes(n[i]))i--; return n.slice(0,i)+n[i].repeat(5)+n.slice(i+1); }
function showEnd(won,how){ unlockPtr(); uiOpen=true; let h,p;
  const me=S.p.name==='ROIG'?'ROIG':'CUTTLAS'; const yell='<div class="yell"><span>¿'+me+'?</span><span>¡'+me+'!</span><span>¡'+stretch(me)+'!</span></div>';
  if(!won&&how==='cell'){ h='LA CELDA'; p='<p>Vidal no abrió. Al amanecer bajan a por ti y a por Halloran. En la excavación, dicen, se deja de contar los salmos.</p>'+yell; }
  else if(!won){ h='CUARTA SESIÓN'; p='<p>Esta vez no hay celda. Te llevan al pabellón médico. Mañana no recordarás la cocina, ni el nombre, ni esta noche. Alarcón rezará por ti con la Vulgata.</p>'+yell; }
  else if(S.kill===0&&S.alarms===0){ h='EL HOMBRE QUE BORRARON'; p='<p>Sales de Tarsis sin que nadie sepa que has pasado. Llevas el expediente, un nombre que no es Cuttlas y la certeza de que abajo hay algo que descansa cuando apagan la luz.</p>'; }
  else if(S.kill>=2){ h='EL ARMA QUE FABRICARON'; p='<p>Sales dejando '+S.kill+' cuerpos. La Compañía ya sabe que funcionas. El expediente no te dice quién eras; te confirma lo que eres.</p>'; }
  else { h='ENTRE DOS MEMORIAS'; p='<p>Sales con la base en '+S.base+'. Hay recuerdos de dos vidas y no encajan. Eso, de momento, es lo más parecido a ser alguien.</p>'; }
  if(won&&S.halloTalked)p+='<p>Halloran te lo dijo todo y no la creíste hasta ver el teclado. Nadie la cree hasta que es tarde.</p>';
  if(won&&S.cellEscaped)p+='<p>Vidal te vio cruzar el patio y miró a otro lado. Halloran se quedó en la celda por decisión propia: «Alguien tiene que contarlo desde dentro.»</p>';
  if(won&&S.teamKO>0)p+='<p>Roig durmió a '+S.teamKO+(S.teamKO===1?' hombre':' hombres')+' sin que nadie supiera desde dónde. En su informe no aparece. En el tuyo, tampoco.</p>';
  p+='<p class="m">Laura Sorolla, 2026: «El expediente dice que volvió. No dice adónde.»</p>';
  el('end').innerHTML='<h2>'+h+'</h2>'+p+'<p class="m">Derribos: '+S.ko+' (Roig: '+S.teamKO+') · Muertes: '+S.kill+' · Alarmas: '+S.alarms+' · Interrogatorios: '+S.interro+' · Pistas: '+S.clues.length+'/'+Object.keys(CLUES).length+' · Cambios: '+S.swaps+'</p>'+(hasSave()&&!won?'<button id="btnAgain">ÚLTIMO PUNTO</button> ':'')+'<button id="btnRestart2" class="'+(hasSave()&&!won?'ghost':'')+'">DESDE EL PRINCIPIO</button> <button id="btnMenu" class="ghost">MENÚ</button>';
  el('menu').hidden=true; el('end').hidden=false; ov.hidden=false; if(!won&&how!=='cell'){ let k=0; const iv=setInterval(()=>{ k++; beep(1800,0.05,'sine',0.03); if(k>5||el('end').hidden)clearInterval(iv); },700); }
  const ba=el('btnAgain'); if(ba)ba.onclick=()=>{ S.over=false; continueGame(); }; el('btnRestart2').onclick=()=>{ reset(); S.over=false; el('end').hidden=true; ov.hidden=true; uiOpen=false; try{gl.requestPointerLock();}catch(e){} codec(CODEC.start); }; el('btnMenu').onclick=()=>{ reset(); S.over=false; started=false; showMenu('main'); }; }
