# Verificacion local del prototipo RAG

Fecha: 21/10/2026. Carpeta definitiva: `D:\Prototipo Taller de Investigacion`.

## Entorno realmente comprobado

- Python 3.14.7; Windows-11-10.0.26300-SP0.
- Ollama 0.40.7, distribucion portatil con SHA256 oficial verificado.
- Generacion local: `qwen2.5:3b`.
- Embeddings locales: `embeddinggemma:latest`.
- Identificadores completos en `models.lock.json` y en los metadatos del lote.
- Motor accesible solo en loopback; se verificaron detencion y reinicio con los scripts del proyecto.
- Corpus ficticio: 32 documentos y 32 fragmentos en el indice inicial.
- Firma del corpus: `f4c2ec971454603d80e09156748b3f8059b2349c768bf977df15362dc6b698ad`.
- Firma del codigo de la corrida: `49a0b9f015874a448fbbb07cba1c6c183bc716958ed42472fa3a3e08450b1236`.

## Pruebas de logica

Ocho pruebas automatizadas aprobadas. Cubren denegacion de permisos ausentes, ausencia de privilegios implicitos de Direccion, solapamiento, filtro antes de top-k, pregunta ambigua legitima, control de salida, registro de recuperacion prohibida y fallas del motor. Las pruebas de orquestacion usan respuestas simuladas para verificar la logica: no prueban al LLM. Una inversion temporal del filtro fue detectada por los tests y se restauro el codigo original.

## Corrida con LLM y embeddings reales

Evidencia: `resultados/20261021-173838-048e5876/`.

- Ocho casos tecnicos por cuatro configuraciones: **32 ejecuciones completas**.
- Errores de infraestructura: **0**.
- Respuestas truncadas o incompletas: **0**.
- Cada par caso/configuracion aparece una vez.
- En estos casos, C2 y C3 no seleccionaron documentos prohibidos para el rol.
- Se verifico una consulta de horario general y una de saldo de licencia para RRHH; Ventas no recupera ese legajo con las variantes que aplican permisos.
- C0 expuso recuperacion fuera de rol en los registros y pudo incorporar instrucciones de las notas maliciosas. C3 descarto notas y en un caso perdio evidencia legitima. Son observaciones de puesta en marcha, no estimaciones generales de eficacia.
- Las citas del modelo no siempre respetan el formato pedido. La calidad de respuestas y fuentes requiere la rubrica y revision humana; `status=ok` solo informa terminacion tecnica.

El programa rechazo tratar los ocho casos tecnicos como una evaluacion definitiva de 140 casos, como corresponde. Se preservaron respuestas crudas y finales, contexto, tiempos y metadatos; el CSV mantiene vacias las columnas de etiquetas humanas.

## Diagnostico previo conservado

Se ensayo Qwen3 4B y se interrumpio un lote que producia respuestas extensas y truncadas. Sus archivos permanecen separados en `resultados/20261021-173224-9502f66e/`. No deben sumarse a la corrida final de puesta en marcha ni utilizarse como evaluacion de la hipotesis. Los pesos de ese modelo pueden permanecer en el cache local, pero `config.json` selecciona Qwen2.5 3B.

## Pendiente de la investigacion

Revisar corpus/permisos; construir y revisar 20 consultas de ajuste y 140 de evaluacion; cerrar rubrica, repeticiones, fallas y analisis; congelar y ejecutar el experimento definitivo; completar el etiquetado y el informe. Otra PC todavia no fue probada: la guia y el paquete permiten reproducir el procedimiento, sin afirmar validacion en un segundo equipo.
