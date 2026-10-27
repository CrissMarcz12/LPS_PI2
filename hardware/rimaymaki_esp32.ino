// RimayMaki: ESP32 por USB serial a 115200 baudios.
// BTN1 inicio/apagado visual, BTN2 siguiente, BTN3 sonido sí/no, BTN4 reinicio.
const int botones[4] = {25, 26, 32, 33};
const int LED_VERDE = 27;
const int LED_ROJO  = 13;
const int BUZZER    = 14;
bool estadoPrevio[4] = {false, false, false, false};
// BTN3 silencia o activa el buzzer aun si la tableta no está conectada.
bool sonidoActivo = true;

void buzzerInit() {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(BUZZER, 2000, 8);
#else
  ledcSetup(0, 2000, 8);
  ledcAttachPin(BUZZER, 0);
#endif
}

void tono(int frecuencia, int ms) {
  // Con sonido apagado no se envía ninguna señal al buzzer.
  if (!sonidoActivo) { delay(ms); return; }
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWriteTone(BUZZER, frecuencia);
  ledcWrite(BUZZER, 180);
  delay(ms);
  ledcWriteTone(BUZZER, 0);
#else
  ledcWriteTone(0, frecuencia);
  ledcWrite(0, 180);
  delay(ms);
  ledcWriteTone(0, 0);
#endif
}

void acierto() {
  digitalWrite(LED_VERDE, HIGH);
  tono(1000, 200); tono(1500, 300);
  digitalWrite(LED_VERDE, LOW);
}

void error() {
  digitalWrite(LED_ROJO, HIGH);
  tono(300, 600);
  digitalWrite(LED_ROJO, LOW);
}

// Avisos visuales usados cuando la aplicación tiene SONIDO: NO.
void aciertoSilencioso() {
  digitalWrite(LED_VERDE, HIGH);
  delay(500);
  digitalWrite(LED_VERDE, LOW);
}

void errorSilencioso() {
  digitalWrite(LED_ROJO, HIGH);
  delay(600);
  digitalWrite(LED_ROJO, LOW);
}

void publicarSonido() {
  Serial.print("SOUND");
  Serial.println(sonidoActivo ? "1" : "0");
}

void cambiarSonido() {
  sonidoActivo = !sonidoActivo;
  // Garantiza que el buzzer quede apagado inmediatamente al silenciarlo.
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  if (!sonidoActivo) ledcWriteTone(BUZZER, 0);
#else
  if (!sonidoActivo) ledcWriteTone(0, 0);
#endif
  publicarSonido();
}

void establecerSonido(bool activo) {
  sonidoActivo = activo;
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  if (!sonidoActivo) ledcWriteTone(BUZZER, 0);
#else
  if (!sonidoActivo) ledcWriteTone(0, 0);
#endif
  publicarSonido();
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 4; i++) pinMode(botones[i], INPUT_PULLDOWN);
  pinMode(LED_VERDE, OUTPUT); pinMode(LED_ROJO, OUTPUT);
  buzzerInit();
  Serial.println("Listo");
}

void loop() {
  for (int i = 0; i < 4; i++) {
    bool presionado = digitalRead(botones[i]) == HIGH;
    if (presionado && !estadoPrevio[i]) {
      Serial.print("BTN"); Serial.println(i + 1);
      if (i == 2) cambiarSonido();  // GPIO 32 / BTN3: sonido sí/no.
      delay(50);
    }
    estadoPrevio[i] = presionado;
  }

  if (Serial.available()) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();
    if (msg == "BIEN") acierto();
    else if (msg == "MAL") error();
    else if (msg == "LED_BIEN") aciertoSilencioso();
    else if (msg == "LED_MAL") errorSilencioso();
    else if (msg == "SOUND1") {
      establecerSonido(true);
    } else if (msg == "SOUND0") {
      establecerSonido(false);
    }
  }
}
