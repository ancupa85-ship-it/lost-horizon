'use strict';
// ---------- MAPA POR ZONAS (2 m por casilla). Cada zona tiene su plano; enterZone() (10-zones) carga una y descarga la anterior.
const T=2;
const ZONES={};                       // id → definición de zona (10-zones.js)
let ZONE=null, map=[], COLS=0, ROWS=0, start={x:2,y:2}, OUTDOOR=[], SOLIDS=new Set();
let barsMesh=null;                    // reja de la celda (zona base)
let INTER=[];                          // puntos de interacción de la zona cargada
const W={officeOpen:false,vaultOpen:false,yardDoorClosed:false,power:true,cellOpen:false,hatchOpen:false};
// carga el plano de una zona en las variables globales del mapa
function setMap(z){ ZONE=z; map=z.src.map(r=>r.split('')); ROWS=map.length; COLS=map[0].length; start={x:z.start[0],y:z.start[1]};
  for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++)if(map[y][x]==='P'){start={x,y};map[y][x]='.';}
  SOLIDS=new Set((z.solids||[]).map(p=>p[0]+','+p[1]));
  OUTDOOR=[]; if(z.outdoor)for(let y=1;y<ROWS-1;y++)for(let x=1;x<COLS-1;x++)if(!interior(x,y)&&cell(x,y)!=='#'&&cell(x,y)!=='W')OUTDOOR.push([x,y]); }
function cell(x,y){ if(x<0||y<0||x>=COLS||y>=ROWS)return '#'; return map[y][x]; }
// '#' roca/muro exterior · 'W' pared · 'T' camión · 'c' caja · 'g' generador · 'b' reja · 'B' puerta blindada · 'L' despacho · 'V' archivo · 'D' puerta · 'U' escalera · 's' sombra/agua · 'z' sombra interior · 'l' farola
function solidT(x,y){ const c=cell(x,y); if(SOLIDS.has(x+','+y))return true;
  switch(c){case '#':case 'W':case 'T':case 'c':case 'g':case 'B':return true; case 'b':return !W.cellOpen; case 'L':return !W.officeOpen; case 'V':return !W.vaultOpen; case 'D':return ZONE.id==='base'&&x===18&&y===4&&W.yardDoorClosed; default:return false;} }
function sightT(x,y){ const c=cell(x,y);
  switch(c){case '#':case 'W':case 'T':case 'c':case 'g':case 'B':return true; case 'L':return !W.officeOpen; case 'V':return !W.vaultOpen; case 'D':return ZONE.id==='base'&&x===18&&y===4&&W.yardDoorClosed; default:return false;} }
function roomy(x,y){ const c=cell(x,y); return c==='_'||c==='z'||c==='L'||c==='V'; }
function interior(x,y){ if(ZONE&&ZONE.indoor){ const c=cell(x,y); return c!=='#'&&c!=='W'&&c!=='B'; } if(roomy(x,y))return true; const c=cell(x,y); if(c==='c'||c==='b'||(c==='D'&&y!==4))return roomy(x-1,y)||roomy(x+1,y)||roomy(x,y-1)||roomy(x,y+1); return false; }
function shadowT(x,y){ const c=cell(x,y); if(c==='z'||c==='s')return true; if(!W.power)return c==='.'||c==='_'||c==='D'||c==='G'||c==='U'; return false; }
function wx(tx){return tx*T+T/2;} function tile(v){return Math.floor(v/T);}
