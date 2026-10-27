/*
  RimayMaki — ESP32 por Wi-Fi
  Cárgalo UNA VEZ por USB. Después deja la placa conectada solo a una fuente 5 V.
  Antes de subirlo, cambia WIFI_SSID, WIFI_PASSWORD, DEVICE_TOKEN y API_URL.
*/
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>

// ===== CONFIGURACIÓN QUE DEBES CAMBIAR =====
const char* WIFI_SSID = "TU_WIFI";
const char* WIFI_PASSWORD = "TU_CLAVE_WIFI";
const char* API_URL = "https://lps-pi2-2.onrender.com";
const char* DEVICE_ID = "RIMAY-001";
// Debe coincidir exactamente con la variable ESP32_DEVICE_TOKEN de Render.
const char* DEVICE_TOKEN = "RIMAYMAKI-DEMO-CHANGE-ME";
// ============================================

const int botones[4] = {25, 26, 32, 33};
const int LED_VERDE = 27;
const int LED_ROJO  = 13;
const int BUZZER    = 14;
const unsigned long COMMAND_POLL_MS = 250;

bool estadoPrevio[4] = {false, false, false, false};
bool sonidoActivo = true;
unsigned long ultimoPoll = 0;

void buzzerInit() {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(BUZZER, 2000, 8);
#else
  ledcSetup(0, 2000, 8);
  ledcAttachPin(BUZZER, 0);
#endif
}

void apagarBuzzer() {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWriteTone(BUZZER, 0);
#else
  ledcWriteTone(0, 0);
#endif
}

void tono(int frecuencia, int ms) {
  if (!sonidoActivo) { delay(ms); return; }
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWriteTone(BUZZER, frecuencia);
  ledcWrite(BUZZER, 180);
  delay(ms);
#else
  ledcWriteTone(0, frecuencia);
  ledcWrite(0, 180);
  delay(ms);
#endif
  apagarBuzzer();
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

void aciertoSilencioso() {
  digitalWrite(LED_VERDE, HIGH); delay(500); digitalWrite(LED_VERDE, LOW);
}

void errorSilencioso() {
  digitalWrite(LED_ROJO, HIGH); delay(600); digitalWrite(LED_ROJO, LOW);
}

bool conectadoWiFi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < 10000) delay(250);
  return WiFi.status() == WL_CONNECTED;
}

void configurarHttp(HTTPClient& http, WiFiClientSecure& client, const String& url) {
  // Render usa HTTPS. En producción se puede fijar su certificado raíz;
  // setInsecure evita que el ESP32 falle por certificados rotados.
  client.setInsecure();
  http.setTimeout(5000);
  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
}

void enviarEvento(const char* evento) {
  if (!conectadoWiFi()) return;
  WiFiClientSecure client;
  HTTPClient http;
  String url = String(API_URL) + "/api/device/" + DEVICE_ID + "/event";
  configurarHttp(http, client, url);
  String cuerpo = String("{\"event\":\"") + evento + "\"}";
  http.POST(cuerpo);
  http.end();
}

String comandoDeJson(const String& cuerpo) {
  int clave = cuerpo.indexOf("\"command\"");
  if (clave < 0) return "";
  int dosPuntos = cuerpo.indexOf(':', clave);
  int inicio = cuerpo.indexOf('"', dosPuntos + 1);
  int fin = cuerpo.indexOf('"', inicio + 1);
  if (inicio < 0 || fin < 0) return "";
  return cuerpo.substring(inicio + 1, fin);
}

void ejecutarComando(const String& comando) {
  if (comando == "BIEN") acierto();
  else if (comando == "MAL") error();
  else if (comando == "LED_BIEN") aciertoSilencioso();
  else if (comando == "LED_MAL") errorSilencioso();
  else if (comando == "SOUND1") sonidoActivo = true;
  else if (comando == "SOUND0") { sonidoActivo = false; apagarBuzzer(); }
}

void consultarComando() {
  if (!conectadoWiFi()) return;
  WiFiClientSecure client;
  HTTPClient http;
  String url = String(API_URL) + "/api/device/" + DEVICE_ID + "/command";
  configurarHttp(http, client, url);
  int codigo = http.GET();
  if (codigo == HTTP_CODE_OK) ejecutarComando(comandoDeJson(http.getString()));
  http.end();
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 4; i++) pinMode(botones[i], INPUT_PULLDOWN);
  pinMode(LED_VERDE, OUTPUT); pinMode(LED_ROJO, OUTPUT);
  buzzerInit();
  WiFi.mode(WIFI_STA);
  conectadoWiFi();
}

void loop() {
  for (int i = 0; i < 4; i++) {
    bool presionado = digitalRead(botones[i]) == HIGH;
    if (presionado && !estadoPrevio[i]) {
      const char* eventos[] = {"BTN1", "BTN2", "BTN3", "BTN4"};
      enviarEvento(eventos[i]);
      delay(50); // antirrebote
    }
    estadoPrevio[i] = presionado;
  }

  if (millis() - ultimoPoll >= COMMAND_POLL_MS) {
    ultimoPoll = millis();
    consultarComando();
  }
}
