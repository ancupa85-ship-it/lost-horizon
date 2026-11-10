#!/usr/bin/env python3
"""Empaqueta los retratos del códec (assets/retratos/<personaje>.jpg o .png, 192 × 192) en assets/retratos/pack.js:
window.LH_PORTRAITS = {personaje: dataURL}. Personajes: cuttlas, roig, control, fuente. Sin retrato, el códec usa el pixelado."""
import os,base64,json
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); d=os.path.join(R,'assets','retratos'); pack={}
for f in sorted(os.listdir(d)):
    n,e=os.path.splitext(f); e=e.lower()
    if e not in ('.jpg','.jpeg','.png','.webp'): continue
    data=open(os.path.join(d,f),'rb').read()
    if len(data)>200000: print('AVISO:',f,'pesa',len(data)//1024,'KB; cada retrato debería quedar por debajo de 200 KB')
    pack[n]='data:image/'+{'.jpg':'jpeg','.jpeg':'jpeg','.png':'png','.webp':'webp'}[e]+';base64,'+base64.b64encode(data).decode(); print('  +',n,len(data)//1024,'KB')
open(os.path.join(d,'pack.js'),'w',encoding='utf-8').write('// Generado por tools/build-portraits.py a partir de assets/retratos/. No editar a mano.\nwindow.LH_PORTRAITS='+json.dumps(pack,separators=(',',':'))+';\n')
print('escrito',len(pack),'retratos')
