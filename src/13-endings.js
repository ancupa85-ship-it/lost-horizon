'use strict';
// ---------- FINALES
function showEnd(won,how){ try{document.exitPointerLock();}catch(e){} uiOpen=true; let h,p;
  if(!won&&how==='cell'){ h='LA CELDA'; p='<p>Vidal no abrió. Al amanecer bajan a por ti y a por Halloran. En la excavación, dicen, se deja de contar los salmos.</p>'; }
  else if(!won){ h='CAPTURADO'; p='<p>Te llevan al pabellón médico. Cuarta sesión. Mañana no recordarás la cocina, ni el nombre, ni esta noche. Alarcón rezará por ti con la Vulgata.</p>'; }
  else if(S.kill===0&&S.alarms===0){ h='EL HOMBRE QUE BORRARON'; p='<p>Sales de Tarsis sin que nadie sepa que has pasado. Llevas el expediente, un nombre que no es Cuttlas y la certeza de que abajo hay algo que descansa cuando apagan la luz.</p>'; }
  else if(S.kill>=2){ h='EL ARMA QUE FABRICARON'; p='<p>Sales dejando '+S.kill+' cuerpos. La Compañía ya sabe que funcionas. El expediente no te dice quién eras; te confirma lo que eres.</p>'; }
  else { h='ENTRE DOS MEMORIAS'; p='<p>Sales con la base en '+S.base+'. Hay recuerdos de dos vidas y no encajan. Eso, de momento, es lo más parecido a ser alguien.</p>'; }
  if(won&&S.halloTalked)p+='<p>Halloran te lo dijo todo y no la creíste hasta ver el teclado. Nadie la cree hasta que es tarde.</p>';
  p+='<p class="m">Laura Sorolla, 2026: «El expediente dice que volvió. No dice adónde.»</p>';
  el('end').innerHTML='<h2>'+h+'</h2>'+p+'<p class="m">Derribos: '+S.ko+' (Roig: '+S.teamKO+') · Muertes: '+S.kill+' · Alarmas: '+S.alarms+' · Interrogatorios: '+S.interro+' · Pistas: '+S.clues.length+'/'+Object.keys(CLUES).length+' · Cambios: '+S.swaps+'</p><button id="btnAgain">OTRA VEZ</button> <button id="btnMenu" class="ghost">MENÚ</button>';
  el('menu').hidden=true; el('end').hidden=false; ov.hidden=false; el('btnAgain').onclick=()=>{ reset(); el('end').hidden=true; ov.hidden=true; uiOpen=false; S.over=false; try{gl.requestPointerLock();}catch(e){} }; el('btnMenu').onclick=()=>{ reset(); S.over=false; started=false; showMenu('main'); }; }
