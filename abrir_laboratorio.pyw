"""Acceso de escritorio sin consola. No descarga modelos ni cambia el experimento."""
import ctypes
import json
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT/'.runtime'
URL = 'http://127.0.0.1:8765'


def local_json(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=3) as response:
        return json.load(response)


def available(url):
    try:
        return local_json(url)
    except (OSError, ValueError):
        return None


def main():
    RUNTIME.mkdir(exist_ok=True)
    existing = available(URL+'/api/status')
    if existing and existing.get('application') != 'taller-rag-comparador-1':
        raise RuntimeError('El puerto 8765 pertenece a otra aplicación. Revisá la guía del laboratorio.')
    if not available('http://127.0.0.1:11434/api/version'):
        exe = ROOT/'.runtime'/'ollama'/'ollama.exe'
        if exe.exists():
            env = dict(os.environ, OLLAMA_HOST='127.0.0.1:11434',
                       OLLAMA_MODELS=str(RUNTIME/'models'), OLLAMA_NO_CLOUD='1')
            with (RUNTIME/'server.stdout.log').open('ab') as out, (RUNTIME/'server.stderr.log').open('ab') as err:
                motor = subprocess.Popen([str(exe),'serve'], cwd=ROOT, env=env,
                    stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
            (RUNTIME/'server.pid').write_text(str(motor.pid), encoding='ascii')
            for _ in range(40):
                if available('http://127.0.0.1:11434/api/version'):
                    break
                time.sleep(.25)
    if existing:
        webbrowser.open(URL)
        return
    with (RUNTIME/'interfaz.stdout.log').open('ab') as out, (RUNTIME/'interfaz.stderr.log').open('ab') as err:
        subprocess.Popen([sys.executable,str(ROOT/'interfaz.py')], cwd=ROOT,
                         stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(40):
        state = available(URL+'/api/status')
        if state and state.get('application') == 'taller-rag-comparador-1':
            webbrowser.open(URL)
            return
        time.sleep(.25)
    raise RuntimeError('No se pudo abrir el laboratorio. Revisá .runtime/interfaz.stderr.log y la guía de instalación.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        RUNTIME.mkdir(exist_ok=True)
        (RUNTIME/'error-apertura.txt').write_text(str(exc), encoding='utf-8')
        ctypes.windll.user32.MessageBoxW(None, str(exc), 'Laboratorio RAG', 0x10)
