'use strict';
// ---------- MAPA (36×28, 2 m por casilla)
const T=2, COLS=36, ROWS=28;
const MAPSRC=[
"####################################",
"#..........l......#..............l.#",
"#.P.......cc......#..TT............#",
"#.ss.......c......#..TT............#",
"#.ss..............D................#",
"#.........l.......#......WWWWWWWWWW#",
"#.................#......W________W#",
"#....TT...........#......W_zz_____W#",
"#....TT........ss.#..g...D____WWDWW#",
"#...............s.#......W____W__zW#",
"#WWWWWWDWWWW......#......W____W___W#",
"#_____z____W......#......WWWWWW___W#",
"#__cc__z___W....l.#..........WWbWWW#",
"#______z___D......#..........W___W.#",
"#______z___W......#.......l..W___W.#",
"#WWWLWWWWWWW..........ss.....WWWWW.#",
"#_____W____W...............s.......#",
"#_____W____V.............s.........#",
"#_z___W_zz_W...cc..................#",
"#_____W____W.......l...............#",
"#WWWWWWWWWWW.......................#",
"#.............l.........ss....TT...#",
"#......................ss.....TT...#",
"#..cc..............................#",
"#..cc.................l............#",
"#.......................ss.........#",
"#.ss..........l...................G#",
"####################################"];
const map=MAPSRC.map(r=>r.split(''));
let start={x:2,y:2};
for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++)if(map[y][x]==='P'){start={x,y};map[y][x]='.';}
const W={officeOpen:false,vaultOpen:false,yardDoorClosed:false,power:true,cellOpen:false};
const OBJ=new Set(['1,12','3,17','8,17']);
function cell(x,y){ if(x<0||y<0||x>=COLS||y>=ROWS)return '#'; return map[y][x]; }
function solidT(x,y){ const c=cell(x,y); if(OBJ.has(x+','+y))return true;
  switch(c){case '#':case 'W':case 'T':case 'c':case 'g':return true; case 'b':return !W.cellOpen; case 'L':return !W.officeOpen; case 'V':return !W.vaultOpen; case 'D':return x===18&&y===4&&W.yardDoorClosed; default:return false;} }
function sightT(x,y){ const c=cell(x,y);
  switch(c){case '#':case 'W':case 'T':case 'c':case 'g':return true; case 'L':return !W.officeOpen; case 'V':return !W.vaultOpen; case 'D':return x===18&&y===4&&W.yardDoorClosed; default:return false;} }
function roomy(x,y){ const c=cell(x,y); return c==='_'||c==='z'||c==='L'||c==='V'; }
function interior(x,y){ if(roomy(x,y))return true; const c=cell(x,y); if(c==='c'||c==='b'||(c==='D'&&y!==4))return roomy(x-1,y)||roomy(x+1,y)||roomy(x,y-1)||roomy(x,y+1); return false; }
function shadowT(x,y){ const c=cell(x,y); if(c==='z'||c==='s')return true; if(!W.power)return c==='.'||c==='_'||c==='D'||c==='G'; return false; }
function wx(tx){return tx*T+T/2;} function tile(v){return Math.floor(v/T);}
const OUTDOOR=[]; for(let y=1;y<ROWS-1;y++)for(let x=1;x<COLS-1;x++)if(!interior(x,y)&&cell(x,y)!=='#'&&cell(x,y)!=='W')OUTDOOR.push([x,y]);
