import json
import time
import urllib.request
from pathlib import Path

cfg = json.loads((Path(__file__).resolve().parent / 'config.json').read_text(encoding='utf-8'))
if cfg['ollama_url'] != 'http://127.0.0.1:11434':
    raise SystemExit('Este instalador solo descarga sobre el motor local predeterminado.')
for model in (cfg['chat_model'], cfg['embedding_model']):
    print('Descargando o verificando:', model, flush=True)
    request = urllib.request.Request(cfg['ollama_url'] + '/api/pull',
        data=json.dumps({'model': model}).encode(), headers={'Content-Type': 'application/json'})
    last = 0
    with urllib.request.urlopen(request, timeout=1800) as response:
        for line in response:
            row = json.loads(line)
            if row.get('error'):
                raise SystemExit(row['error'])
            if time.monotonic()-last > 10 or row.get('status') == 'success':
                print(row.get('status'), round(row.get('completed', 0)/1024**2), '/',
                      round(row.get('total', 0)/1024**2), 'MiB', flush=True)
                last = time.monotonic()
print('Descargas completadas. Ejecutar python rag.py doctor.')
