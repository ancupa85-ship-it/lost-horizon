#!/usr/bin/env python3
"""Empaqueta el juego en un único HTML (dist/lost-horizon-fps.html) para publicarlo como Artifact de Claude.
El Artifact exige: sin doctype/html/head/body, <title> primero, y scripts externos solo desde cdnjs."""
import os,re
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html=open(os.path.join(R,'index.html'),encoding='utf-8').read()
css=open(os.path.join(R,'css','style.css'),encoding='utf-8').read()
srcs=sorted(f for f in os.listdir(os.path.join(R,'src')) if f.endswith('.js'))
js=[]
for f in srcs:
    t=open(os.path.join(R,'src',f),encoding='utf-8').read()
    t=re.sub(r"^'use strict';\n",'',t)
    t=t.replace("throw new Error('THREE no cargado');","return;")
    js.append('// ===== '+f+'\n'+t)
body=re.search(r'<body>\n(.*?)\n<script src="vendor/three.min.js">',html,re.S).group(1)
out=('<title>Lost Horizon: De Profundis</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
 '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap">\n'
 '<style>\n'+css+'</style>\n'+body+'\n'
 '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>\n'
 "<script>\n(function(){\n'use strict';\n"+'\n'.join(js)+'\n})();\n</script>\n')
os.makedirs(os.path.join(R,'dist'),exist_ok=True)
p=os.path.join(R,'dist','lost-horizon-fps.html'); open(p,'w',encoding='utf-8').write(out); print('escrito',p,len(out),'bytes')
