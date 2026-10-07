# RimayMaki

Juego web local para practicar letras estáticas de LSP. Chrome solicita acceso a la cámara al iniciar una partida; los fotogramas se procesan localmente con MediaPipe y los modelos ya entrenados. La pantalla inicial contiene **RIMAYMAKI**, su lema y **START**.

## Ejecutar el juego

```powershell
python -m pip install -r requirements.txt
python main.py
```

Se abre `http://127.0.0.1:5000` en Chrome cuando está instalado (con respaldo al navegador predeterminado). Si aún no hay modelos, al pulsar START se muestra “No hay letras entrenadas disponibles.”

El panel de desarrollo local está disponible en `http://127.0.0.1:5000/training`. Captura landmarks desde la cámara, permite ver el conteo por letra y entrena directamente el modelo que después consume el juego. No genera muestras ni modelos de ejemplo.

## Flujo exclusivo de desarrollo

Captura muestras reales para una letra (SPACE guarda una secuencia de 20 cuadros):

```powershell
python training/collect_data.py A
```

Entrena solo esa letra cuando tenga al menos 20 muestras:

```powershell
python training/train_model.py A
```

Esto crea `models/A/classifier.joblib` y su metadata. Repite el flujo para B, C, etc. El juego los incorpora automáticamente sin editar `main.py`. Las capturas se guardan únicamente en `datasets/<LETRA>/`; no se generan muestras ni modelos de ejemplo.

## Referencia visual

Agrega manualmente una referencia verificada para cada letra en `static/assets/signs/A.png` (o `B.png`, etc.). Si no existe la imagen, el juego muestra “Referencia no disponible” sin afectar el reconocimiento.
python main.py
## Parámetros

En `config.py` puedes ajustar `CONFIDENCE_THRESHOLD`, `PREDICTION_HISTORY_SIZE`, `STABLE_FRAMES_REQUIRED`, `RECOGNITION_FPS`, `SAMPLE_CAPTURE_INTERVAL_SECONDS`, `MIN_SAMPLES_PER_CLASS`, `TOTAL_ROUNDS`, `SHOW_LANDMARKS` y `DEBUG_MODE`.

Los modelos estáticos actuales se entrenan con los frames normalizados de cada captura. Esto mantiene las mismas capturas de 20 frames para recolectar variación, pero permite clasificar desde el primer frame durante el juego.
