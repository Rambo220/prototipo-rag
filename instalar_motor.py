"""Descarga oficial y verificable de Ollama portatil para Windows x64."""
import hashlib
import platform
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent / '.runtime'
VERSION = 'v0.40.7'
NAME = 'ollama-windows-amd64.zip'
SHA256 = 'e6527768c53e85ec4596495fb0f035ef07f437b4b591ebc3581684699a4668f4'
URL = f'https://github.com/ollama/ollama/releases/download/{VERSION}/{NAME}'


def main():
    if platform.system() != 'Windows' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise SystemExit('Este instalador corresponde a Windows x64. Consultar la guia para otros sistemas.')
    ROOT.mkdir(exist_ok=True)
    archive = ROOT / NAME
    if not archive.exists():
        partial = ROOT / (NAME + '.partial')
        with urllib.request.urlopen(URL, timeout=120) as src, partial.open('wb') as dst:
            total = 0
            while block := src.read(8 * 1024**2):
                dst.write(block)
                total += len(block)
                if total % (128 * 1024**2) == 0:
                    print(f'Descargados {total // 1024**2} MiB', flush=True)
        with partial.open('rb') as f:
            if hashlib.file_digest(f, 'sha256').hexdigest() != SHA256:
                raise SystemExit('Hash incorrecto. No se extrae el archivo descargado.')
        partial.replace(archive)
    with archive.open('rb') as f:
        if hashlib.file_digest(f, 'sha256').hexdigest() != SHA256:
            raise SystemExit('El ZIP existente no coincide con el hash oficial.')
    target = (ROOT / 'ollama').resolve()
    if (target / 'ollama.exe').exists():
        print('El motor ya existe. Su version se comprueba al iniciar; no se sobrescribe.')
        return
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if not (target / item.filename).resolve().is_relative_to(target):
                raise SystemExit('Ruta inesperada dentro del ZIP.')
        z.extractall(target)
    print('Motor extraido. Ejecutar iniciar_motor.ps1 y descargar_modelos.py.')


if __name__ == '__main__':
    main()
