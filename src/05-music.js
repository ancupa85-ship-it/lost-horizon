'use strict';
// ---------- MÚSICA: dos temas (sigilo / acción) con fundidos; se atenúa con códec y diálogos
const MUSIC_SRC={sigilo:'assets/music/sigilo.mp3',accion:'assets/music/accion.mp3'};
const music={tracks:{},cur:null,vol:{},want:null,ready:false,
  init(){ if(this.ready)return; this.ready=true; for(const k in MUSIC_SRC){ const a=new Audio(); a.src=MUSIC_SRC[k]; a.loop=true; a.preload='auto'; a.volume=0; this.tracks[k]=a; this.vol[k]=0; } },
  // qué debería sonar ahora
  pick(){ if(typeof S==='undefined')return 'sigilo'; if(started&&!S.over&&S.alertT>0)return 'accion'; return 'sigilo'; },
  // factor de atenuación: códec/diálogo bajan, el menú de inicio suena suave
  duck(){ if(typeof started==='undefined')return 1; if(!started)return 0.55; if(typeof codecQ!=='undefined'&&codecQ)return 0.3; if(uiOpen&&!paused)return 0.45; if(paused)return 0.4; return 1; },
  play(k){ const a=this.tracks[k]; if(!a||!a.paused)return; const p=a.play(); if(p&&p.catch)p.catch(()=>{}); },
  tick(dt){ if(!this.ready)return; const base=(typeof OPT!=='undefined')?OPT.vol*OPT.music:0.5; const want=this.pick(); if(want!==this.cur){ this.cur=want; this.play(want); }
    const d=this.duck(); for(const k in this.tracks){ const a=this.tracks[k]; const target=(k===this.cur)?base*d:0; const v=this.vol[k]; const sp=(target<v?1.2:0.6)*dt; this.vol[k]=Math.abs(target-v)<sp?target:v+Math.sign(target-v)*sp; a.volume=Math.max(0,Math.min(1,this.vol[k])); if(this.vol[k]<=0.001&&k!==this.cur&&!a.paused){ a.pause(); a.currentTime=0; } } },
  stop(){ for(const k in this.tracks){ const a=this.tracks[k]; a.pause(); a.currentTime=0; this.vol[k]=0; a.volume=0; } this.cur=null; } };
// el navegador exige un gesto del usuario para sonar: el primer clic o tecla arranca la música
['pointerdown','keydown'].forEach(ev=>document.addEventListener(ev,()=>{ music.init(); music.cur=null; },{once:true}));
