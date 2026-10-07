# RimayMaki

Juego web para practicar señas estáticas de LSP con cámara. El juego reconoce los modelos entrenados, da retroalimentación visual y muestra una referencia de la seña.

## Uso local

```powershell
python -m pip install -r requirements.txt
python main.py
```

Abre `http://127.0.0.1:5000`. El panel de entrenamiento está en `http://127.0.0.1:5000/training`.

## Entrenar cualquier seña

En el panel escribe una etiqueta propia: `M`, `1`, `HOLA` o `NÚMERO 1`. Luego:

1. Sube la imagen de referencia de esa seña (PNG, JPG o WEBP).
2. Activa **Capturar muestras** y registra al menos 20 muestras reales.
3. Pulsa **Entrenar modelo**.

La misma etiqueta, modelo e imagen aparecen automáticamente en el juego. Las capturas guardan landmarks, no fotos de la cámara. Las etiquetas aceptan hasta 32 caracteres: letras, números, espacios, guiones y guion bajo.

## Publicar en Render para trabajo en equipo

El repositorio incluye `render.yaml`. En Render crea un **Blueprint** desde este repositorio y el archivo configurará el servidor, `SECRET_KEY` y un disco persistente en `/var/data`.

El disco persistente es importante: guarda muestras, modelos e imágenes de referencia aun cuando Render reinicie o haga un despliegue. Sin disco persistente esos datos se perderían al redeploy. El servicio se inicia con un único proceso para que todos los compañeros vean el mismo conjunto de modelos.

Después de publicar, cada integrante abre `https://tu-servicio.onrender.com/training` para aportar muestras. Cada navegador tiene su propia sesión de cámara; los modelos y las referencias sí son compartidos por el equipo. Como el panel permite crear y borrar datos comunes, compártelo solo con el equipo o protégelo antes de hacerlo público.

## Parámetros

`config.py` reúne los valores de reconocimiento, como `CONFIDENCE_THRESHOLD`, `MIN_SAMPLES_PER_CLASS`, `TOTAL_ROUNDS` y `SHOW_LANDMARKS`.
