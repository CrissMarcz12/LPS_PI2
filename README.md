# Reconocedor LSP: alfabeto y signos estáticos

El vocabulario base contiene las **27 letras** de Lengua de Señas Peruana: `A-Z` incluyendo `Ñ`; `LL` se excluye. También permite añadir palabras que el usuario declara y captura como **signos estáticos**. No construye frases ni conversaciones, y no inventa una seña LSP para una palabra.

## Preparación

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --force-reinstall -r requirements.txt
```

Se fija `mediapipe==0.10.14`: el código usa su API estable `mp.solutions.hands`.
La versión 1.x no es compatible con esa API. El arranque también evita la
importación de la utilidad 3D opcional de Matplotlib de MediaPipe; así no se
activa `kiwisolver`, que Windows App Control puede bloquear. La aplicación no
usa Matplotlib para reconocer ni dibujar landmarks.

## Recopilar datos

Captura al menos 40 secuencias variadas y estables por letra; cambia iluminación, distancia y orientación sin ocultar la mano. Para las letras de movimiento (`J`, `Ñ`, `Z`), ejecuta el movimiento completo durante los 20 cuadros anteriores a `SPACE`.

```powershell
python main.py --collect A
python main.py --collect Ñ
```

`SPACE` guarda una muestra, `R` borra el buffer actual y `ESC` sale. Las muestras quedan en `data/lsp_alphabet_landmarks.npz`; cada una conserva su etiqueta de letra.

## Añadir una palabra estática

Antes de capturar una palabra, regístrala explícitamente. Por ejemplo:

```powershell
python manage_vocabulary.py add HOLA
python main.py --collect HOLA
```

Captura al menos 40 muestras de `HOLA`, igual que para una letra. Solo añade palabras cuyo gesto sea estático y cuya referencia LSP hayas validado; no agregues una palabra dinámica como si fuera una postura fija. Consulta o elimina palabras antes de entrenar con:

```powershell
python manage_vocabulary.py list
python manage_vocabulary.py remove HOLA
```

## Añadir una palabra con movimiento

Registra primero la clase dinámica. `HOLA` ya está registrada como ejemplo:

```powershell
python manage_vocabulary.py add-dynamic HOLA
python main.py --collect-dynamic HOLA
```

En la ventana, pulsa `SPACE` para iniciar la grabación, realiza el movimiento
completo y pulsa `SPACE` de nuevo para guardar la secuencia. Se normaliza a 48
cuadros de landmarks, de modo que distintas velocidades se puedan comparar.
Repite al menos 40 veces. `R` cancela una grabación en curso.

Las letras `J`, `Ñ` y `Z` también se consideran dinámicas; captúralas con
`--collect-dynamic`, no con `--collect`.

## Entrenar

El entrenamiento crea dos modelos: uno para posturas y otro para movimientos.
Se bloquea si falta cualquiera de las 27 letras o de las palabras activas, o
si una clase tiene menos de 40 muestras.

```powershell
python train.py
```

El modelo se guarda en `models/lsp_alphabet_classifier.joblib`.


## Reconocer y aprender

```powershell
python main.py
python main.py --educational --target A
```

El modo educativo enseña la letra solicitada, la letra estable reconocida, confianza y puntaje. `ENTER` selecciona otra letra objetivo. La aplicación muestra `—` hasta que haya una predicción suficientemente confiable y estable; nunca sustituye una letra por una clase genérica.

## Estructura

- `data/labels.py`: vocabulario cerrado de 27 letras.
- `features/landmarks.py`: centra los landmarks en la muñeca y los escala por la palma; además construye secuencias temporales.
- `data/dataset.py`: dataset incremental por letra.
- `recognition/classifier.py`: SVM probabilística, umbral y estabilización temporal.
- `train.py`: validación de las 27 clases y entrenamiento.
- `main.py`: cámara, MediaPipe, interfaz, captura y modo educativo.

No añadas otra etiqueta a `LSP_ALPHABET`; hacerlo cambiaría el alcance del sistema y rompería la garantía de 27 clases.
