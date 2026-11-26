"""Enciende o apaga las herramientas MCP de Unreal (plugin AllToolsets) en PruebaLumen.

uso:  python mcp_conmutar.py on     (tandas de trabajo: 53 toolsets)
      python mcp_conmutar.py off    (para jugar: menos VRAM)
      python mcp_conmutar.py        (dice cómo está)

Solo cambia "Enabled" de AllToolsets en PruebaLumen.uproject; el servidor
ModelContextProtocol sigue activo. Antes de escribir guarda PruebaLumen.uproject.bak-conmutar.
El cambio vale al reabrir el editor (ciérralo antes)."""
import json, shutil, sys

UPROJECT = r'D:\PruebaLumen\PruebaLumen\PruebaLumen.uproject'
PLUGIN = 'AllToolsets'

with open(UPROJECT, encoding='utf-8') as f:
    datos = json.load(f)
plugins = datos.setdefault('Plugins', [])
entrada = next((p for p in plugins if p.get('Name') == PLUGIN), None)
actual = bool(entrada and entrada.get('Enabled'))

if len(sys.argv) < 2:
    print('%s: %s' % (PLUGIN, 'on' if actual else 'off'))
    sys.exit(0)

modo = sys.argv[1].lower()
if modo not in ('on', 'off'):
    sys.exit('uso: python mcp_conmutar.py on|off')
quiero = modo == 'on'
if quiero == actual:
    print('%s ya está %s; no toco nada' % (PLUGIN, modo))
    sys.exit(0)

shutil.copyfile(UPROJECT, UPROJECT + '.bak-conmutar')
if entrada is None:
    plugins.append({'Name': PLUGIN, 'Enabled': quiero})
else:
    entrada['Enabled'] = quiero
with open(UPROJECT, 'w', encoding='utf-8') as f:
    json.dump(datos, f, indent='\t')
print('%s -> %s (copia en %s.bak-conmutar). Reabre el editor para que cuente.' % (PLUGIN, modo, UPROJECT))
