# Laboratorio RAG Grupo 2

Prototipo experimental local para comparar C0 base, C1 entrada, C2 permisos y C3 combinada. Institución informada: Facultad de Ciencias en la Administración. Unidad: Taller de Investigación. Entrega final: 20/11/2026.

## Primera instalación desde GitHub

Descargá el ZIP del repositorio o clonalo:

```powershell
git clone https://github.com/Rambo220/prototipo-rag.git
Set-Location prototipo-rag
```

Con Python 3.11 o posterior, seguí la [guía de instalación](GUIA_INSTALACION_PROTOTIPO_RAG.md). Incluye la descarga del motor y de los modelos, su verificación y la creación del índice. No se necesitan claves de API ni paquetes de pip.

El repositorio contiene el código, el corpus ficticio, la interfaz y las pruebas. El motor, los modelos descargados, el índice generado y los resultados de cada PC se crean localmente y quedan fuera de Git.

## Empezar

Leer **GUIA_INSTALACION_PROTOTIPO_RAG.md**. La guía incluye instalación desde cero en otra PC, descarga verificada del motor y modelos, consultas y lotes.

En la PC ya configurada, hacé doble clic en **ABRIR_LABORATORIO.cmd**. Abre el comparador local en **http://127.0.0.1:8765**: elegí el rol, escribí la consulta y pulsá **Comparar las cuatro**. Cada panel muestra respuesta, documentos recuperados y fragmentos.

Para el uso por consola sigue disponible esta alternativa:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\iniciar_motor.ps1
python rag.py doctor
python rag.py ask --role General --variant C2 --query 'Que horario de atencion interna tiene Horizonte?'
```

## Archivos

- `PROPUESTA_CORPUS_Y_PERMISOS_RAG.md`: escenario, matriz, tareas, fechas y decisiones pendientes.
- `config.json` y `models.lock.json`: parámetros y versiones verificadas de modelos.
- `data/corpus/` y `data/manifest.json`: 32 documentos ficticios y sus permisos.
- `data/casos_puesta_marcha.jsonl`: ocho casos técnicos, distintos del conjunto de evaluación definitivo.
- `rag.py`: validación, diagnóstico, indexación, consultas, congelamiento y lotes.
- `resultados/`: evidencia generada; no se incorpora a la fuente documental del modelo.
- `.runtime/`: motor, modelos y registros de servicio; no se incluye en el paquete liviano.
- `VERIFICACION_LOCAL.md`: alcance y resultado de las comprobaciones realizadas.

La investigación comenzó con los entregables previos: este proyecto implementa su etapa de pruebas. La versión inicial del corpus y la matriz requieren revisión del equipo. Los registros técnicos no reemplazan las 140 consultas definitivas ni prueban la hipótesis. El CSV debe completarse con la rúbrica humana acordada.

El programa consulta las API locales de [Ollama](https://docs.ollama.com/api/chat) y [embeddings](https://docs.ollama.com/api/embed). Los scripts y los datos del corpus no ejecutan herramientas a pedido del LLM. Los permisos corresponden al experimento; quien administra esta PC puede leer todos los archivos locales.
