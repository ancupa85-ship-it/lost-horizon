#!/usr/bin/env python3
"""Empaqueta los modelos de Blender (assets/models/*.glb) en assets/models/pack.js para que el juego los cargue
sin pedir nada por red: window.LH_MODELS = {hueco: base64}. El nombre del archivo es el nombre del hueco
(caja.glb, camion.glb, generador.glb, farola.glb, torreta.glb). Guía de medidas: docs/ASSETS.md.
Uso: python3 tools/build-models.py [carpeta_de_glb] [salida_pack.js]"""
import os,sys,base64,json,struct,re
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src=sys.argv[1] if len(sys.argv)>1 else os.path.join(R,'assets','models')
out=sys.argv[2] if len(sys.argv)>2 else os.path.join(R,'assets','models','pack.js')
slots=set(re.findall(r"^  (\w+):\{desc:",open(os.path.join(R,'src','03-models.js'),encoding='utf-8').read(),re.M))
pack={}; total=0
for f in sorted(os.listdir(src)):
    if not f.lower().endswith('.glb'): continue
    name=os.path.splitext(f)[0]; data=open(os.path.join(src,f),'rb').read()
    if data[:4]!=b'glTF': print('AVISO:',f,'no es un .glb binario (exporta en Blender como «glTF Binary (.glb)»); se salta'); continue
    if name not in slots: print('AVISO:',f,'no corresponde a ningún hueco conocido ('+', '.join(sorted(slots))+'); se empaqueta, pero el juego no lo usará')
    if len(data)>1500000: print('AVISO:',f,'pesa',len(data)//1024,'KB; procura que cada modelo quede por debajo de 1,5 MB')
    pack[name]=base64.b64encode(data).decode(); total+=len(data); print('  +',name,len(data)//1024,'KB')
open(out,'w',encoding='utf-8').write('// Generado por tools/build-models.py a partir de assets/models/*.glb. No editar a mano.\nwindow.LH_MODELS='+json.dumps(pack,separators=(',',':'))+';\n')
print('escrito',out,'·',len(pack),'modelos ·',total//1024,'KB')
