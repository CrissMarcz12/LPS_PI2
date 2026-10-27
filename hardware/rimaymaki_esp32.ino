// RimayMaki: ESP32 por USB serial a 115200 baudios.
// BTN1 inicio/apagado visual, BTN2 siguiente, BTN3 volumen buzzer, BTN4 reinicio.
const int botones[4] = {25, 26, 32, 33};
const int LED_VERDE = 27;
const int LED_ROJO  = 13;
const int BUZZER    = 14;
bool estadoPrevio[4] = {false, false, false, false};
int volumenBuzzer = 179;  // 70 % de 255

void buzzerInit() {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(BUZZER, 2000, 8);
#else
  ledcSetup(0, 2000, 8);
  ledcAttachPin(BUZZER, 0);
#endif
}

void tono(int frecuencia, int ms) {
  if (volumenBuzzer == 0) { delay(ms); return; }
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWriteTone(BUZZER, frecuencia);
  ledcWrite(BUZZER, volumenBuzzer);
  delay(ms);
  ledcWriteTone(BUZZER, 0);
#else
  ledcWriteTone(0, frecuencia);
  ledcWrite(0, volumenBuzzer);
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
      delay(50);
    }
    estadoPrevio[i] = presionado;
  }

  if (Serial.available()) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();
    if (msg == "BIEN") acierto();
    else if (msg == "MAL") error();
    else if (msg.startsWith("VOL")) {
      int porcentaje = constrain(msg.substring(3).toInt(), 0, 100);
      volumenBuzzer = map(porcentaje, 0, 100, 0, 255);
    }
  }
}
