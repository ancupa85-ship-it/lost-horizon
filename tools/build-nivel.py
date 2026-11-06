#!/usr/bin/env python3
"""Empaqueta el nivel «La Torre» (nivel/) en un único HTML (dist/la-torre.html) para publicarlo como Artifact.
Three.js r128 desde cdnjs y la banda sonora incrustada en base64."""
import os,re,base64
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html=open(os.path.join(R,'nivel','index.html'),encoding='utf-8').read()
js=open(os.path.join(R,'nivel','torre.js'),encoding='utf-8').read()
for k in ('sigilo','accion'):
    mp=os.path.join(R,'assets','music',k+'.mp3')
    js=js.replace("'../assets/music/"+k+".mp3'","'data:audio/mpeg;base64,"+base64.b64encode(open(mp,'rb').read()).decode()+"'")
style=re.search(r'<style>(.*?)</style>',html,re.S).group(1)
body=re.search(r'<body>\n(.*?)\n<script src="../vendor/three.min.js">',html,re.S).group(1)
out=('<title>Lost Horizon: La Torre</title>\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
 '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap">\n'
 '<style>'+style+'</style>\n'+body+'\n'
 '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>\n<script>\n'+js+'\n</script>\n')
os.makedirs(os.path.join(R,'dist'),exist_ok=True)
p=os.path.join(R,'dist','la-torre.html'); open(p,'w',encoding='utf-8').write(out); print('escrito',p,len(out),'bytes')
