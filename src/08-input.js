'use strict';
// ---------- ENTRADA
function norm(k){ return k.length===1?k.toLowerCase():k; }
addEventListener('keydown',e=>{ const k=norm(e.key);
  if(cut){ if(k==='e'||k==='Enter'||k===' '){cutSkip();e.preventDefault();} return; }
  if(codecQ){ if(k==='e'||k==='Enter'||k===' '){codecNext();e.preventDefault();} return; }
  if(keypadMode){ if(/^[0-9]$/.test(k)){keypadIn(k);e.preventDefault();return;} if(k==='Backspace'){keypadIn('del');e.preventDefault();return;} if(k==='Enter'){keypadIn('ok');e.preventDefault();return;} if(k==='Escape'){closeDialog();return;} return; }
  if(paused){ if(k==='Escape')resumeGame(); return; }
  if(uiOpen){ if(/^[1-9]$/.test(k)&&dlgOpts[+k-1]){dlgOpts[+k-1].f();e.preventDefault();} else if(k==='Escape'){closeDialog();} return; }
  if(k==='Escape'){ if(started&&!S.over)pauseGame(); return; }
  if(k==='Tab'){ noteEl.hidden=!noteEl.hidden; e.preventDefault(); return; }
  if(k==='x'){ swapChar(); return; } if(k==='g'){ teamOrder(); return; } if(k==='t'){ toggleSilencer(); return; } if(k==='r'){ radioMenu(); return; } if(k==='h'){ OPT.hints=!OPT.hints; saveOpt(); guideEl.hidden=!OPT.hints; return; }
  keys[k]=true; if(k==='Control'||k==='Shift'||k===' ')e.preventDefault();
  if(k==='b')scopeKey=true; if(k==='z')throwDecoy(); if(k==='e')doUse(); if(k==='f')doGrab(); if(k==='c')doCarry(); if(k==='Control')S.p.crouch=!S.p.crouch; if(k==='v'){third=!third; beep(700,0.04,'square',0.03);} if(k==='q')startSmoke(); });
addEventListener('keyup',e=>{ const k=norm(e.key); keys[k]=false; if(k==='b')scopeKey=false; });
// prismáticos también con el botón derecho del ratón
gl.addEventListener('mousedown',e=>{ if(e.button===2){ scopeBtn=true; e.preventDefault(); } }); addEventListener('mouseup',e=>{ if(e.button===2)scopeBtn=false; }); gl.addEventListener('contextmenu',e=>e.preventDefault()); addEventListener('blur',()=>{ scopeKey=false; scopeBtn=false; });
gl.addEventListener('click',()=>{ if(!started||paused)return; if(cut){cutSkip();return;} if(codecQ){codecNext();return;} if(uiOpen)return; if(document.pointerLockElement!==gl){ try{gl.requestPointerLock();}catch(e){} return; } shoot(); });
// el juego suelta el puntero a propósito (diálogo, códec, captura, final): esa soltura no debe pausar
let ptrGrace=0; function unlockPtr(){ ptrGrace=performance.now()+1500; try{document.exitPointerLock();}catch(e){} }
document.addEventListener('pointerlockchange',()=>{ locked=document.pointerLockElement===gl; if(locked)ptrGrace=0; else if(!locked&&started&&!uiOpen&&!cut&&!S.over&&!paused&&!S.capturing&&performance.now()>ptrGrace)pauseGame(); });
addEventListener('mousemove',e=>{ if(!locked||uiOpen||cut)return; if(Math.abs(e.movementX)>200||Math.abs(e.movementY)>200)return; const lk=lookK(); yaw-=e.movementX*0.0022*OPT.sens*lk; pitch=Math.max(-1.4,Math.min(1.4,pitch-e.movementY*0.0022*OPT.sens*lk*(OPT.invY?-1:1))); });
