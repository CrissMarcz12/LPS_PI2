# RimayMaki

Juego web para practicar señas estáticas de LSP con cámara. El juego reconoce los modelos entrenados, da retroalimentación visual y muestra una referencia de la seña.

## Uso local

```powershell
python -m pip install -r requirements.txt
python main.py
```

Abre `http://127.0.0.1:5000`. La ruta de entrenamiento se entrega únicamente al equipo responsable del modelo.

## Entrenar cualquier seña

En el panel escribe una etiqueta propia: `M`, `1`, `HOLA` o `NÚMERO 1`. Luego:

1. Sube la imagen de referencia de esa seña (PNG, JPG o WEBP).
2. Activa **Capturar muestras** y registra al menos 20 muestras reales.
3. Pulsa **Entrenar modelo**.

La misma etiqueta, modelo e imagen aparecen automáticamente en el juego. Las capturas guardan landmarks, no fotos de la cámara. Las etiquetas aceptan hasta 32 caracteres: letras, números, espacios, guiones y guion bajo.

## Tableta y botones físicos

`/game` abre directamente en modo quiosco: solo se ve la cámara, la seña de referencia y los puntos dentro de ella. La detección de la mano ocurre en la tableta con MediaPipe Web; al servidor se envían únicamente 63 valores de landmarks, no fotos, para mantener el vídeo y los puntos suaves.

El juego no reproduce sonidos por los parlantes de la pantalla: toda la retroalimentación sonora sale del buzzer ESP32. Al abrir `/game` se muestra la portada y espera `BTN1` (**START**). Durante la partida, el mismo `BTN1` la termina y muestra “Gracias por jugar”; `BTN2` pasa a la siguiente seña correcta, `BTN3` cambia **SONIDO: SÍ/NO** y `BTN4` reinicia puntuación y racha. Con sonido apagado los LEDs siguen indicando acierto/error, pero el buzzer no recibe tonos.

### ESP32 por Wi-Fi (tableta sin cable)

En la aplicación publicada con HTTPS, el juego usa automáticamente Wi-Fi. Sube una vez [`hardware/rimaymaki_esp32_wifi.ino`](hardware/rimaymaki_esp32_wifi.ino) por USB, edita `WIFI_SSID`, `WIFI_PASSWORD`, `API_URL`, `DEVICE_ID` y `DEVICE_TOKEN`, y después alimenta la placa solo desde un cargador USB de 5 V. La tableta puede abrir el juego en cualquier navegador moderno; si ambos usan la misma red Wi-Fi también funcionará, aunque la comunicación viaja de forma segura por Render.

En Render, agrega una variable de entorno `ESP32_DEVICE_TOKEN` con exactamente el mismo valor definido en `DEVICE_TOKEN`. No publiques una clave real en GitHub. El ejemplo trae una clave de demostración que debes reemplazar antes de usarlo fuera de pruebas. Para conservar la conexión USB local existe [`hardware/rimaymaki_esp32.ino`](hardware/rimaymaki_esp32.ino); abre `/game?transport=usb` en un navegador compatible con Web Serial.

## Entrenamiento compartido con GitHub

Cada integrante trabaja una letra diferente. Solo necesita dos comandos desde la carpeta del proyecto:

```powershell
# 1. Antes de capturar: actualiza GitHub y abre RimayMaki para entrenar C.
python training/team_sync.py entrenar C

# 2. Cuando ya pulsó ENTRENAR MODELO y cerró el servidor con Ctrl+C:
python training/team_sync.py publicar C
```

El primero hace `pull` automáticamente antes de abrir la cámara. El segundo vuelve a actualizar el repositorio, guarda en GitHub el modelo, las muestras de landmarks y la imagen de referencia de `C`, crea el commit y hace `push`. Para la siguiente persona sería exactamente igual con `D`. No se suben vídeos ni fotos de cámara: solo los puntos de la mano y la imagen de guía.

La página para capturar y entrenar es `http://127.0.0.1:5000/api/lab/rm-7f3a/entrenar`. Es una ruta técnica para el equipo, no para los niños. No entrenen simultáneamente la misma etiqueta; para letras distintas (`C`, `D`, `HOLA`) el flujo integra sus cambios sin mezclar los modelos.

## Publicar gratis en Render

El archivo `render.yaml` está preparado para el plan gratuito: en Render crea un **Blueprint** desde este repositorio. Cada `push` a `main` despliega la versión actual del juego y sus letras entrenadas.

El plan gratuito no tiene disco persistente, por eso el entrenamiento se hace localmente con los dos comandos anteriores y GitHub es la fuente compartida. Al iniciar Render copia las letras, modelos, muestras y referencias que ya están versionados en el repositorio. No uses el panel de entrenamiento en Render para guardar trabajo nuevo, porque Render puede reiniciarse y perder esos cambios; publícalo desde un equipo mediante `team_sync.py`.

## Parámetros

`config.py` reúne los valores de reconocimiento, como `CONFIDENCE_THRESHOLD`, `MIN_SAMPLES_PER_CLASS`, `TOTAL_ROUNDS` y `SHOW_LANDMARKS`.
