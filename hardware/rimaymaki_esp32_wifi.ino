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
unsigned long ultimoLogHttp = 0;
int ultimoEstadoWiFi = -1;

const char* nombreEstadoWiFi(wl_status_t estado) {
  switch (estado) {
    case WL_CONNECTED: return "CONECTADO";
    case WL_NO_SSID_AVAIL: return "RED NO ENCONTRADA";
    case WL_CONNECT_FAILED: return "CLAVE O RED INCORRECTA";
    case WL_CONNECTION_LOST: return "CONEXIÓN PERDIDA";
    case WL_DISCONNECTED: return "DESCONECTADO";
    default: return "CONECTANDO";
  }
}

void mostrarEstadoWiFi() {
  int estado = WiFi.status();
  if (estado == ultimoEstadoWiFi) return;
  ultimoEstadoWiFi = estado;
  Serial.printf("[WIFI] %s", nombreEstadoWiFi((wl_status_t)estado));
  if (estado == WL_CONNECTED) Serial.printf(" · IP: %s", WiFi.localIP().toString().c_str());
  Serial.println();
}

void mostrarErrorHttp(const char* accion, int codigo) {
  if (codigo >= 200 && codigo < 300) return;
  if (millis() - ultimoLogHttp < 3000) return;
  ultimoLogHttp = millis();
  Serial.printf("[RENDER] %s falló · HTTP %d\n", accion, codigo);
  if (codigo == 401) Serial.println("[RENDER] Revisa DEVICE_TOKEN y ESP32_DEVICE_TOKEN.");
  if (codigo == 404) Serial.println("[RENDER] Revisa API_URL: no debe terminar en /game.");
}

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
  // WiFi.begin se ejecuta solo en setup. Volver a llamarlo mientras STA está
  // conectando produce "sta is connecting, cannot set config".
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
  int codigo = http.POST(cuerpo);
  if (codigo >= 200 && codigo < 300) Serial.printf("[BOTÓN] %s enviado\n", evento);
  else mostrarErrorHttp("evento", codigo);
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
  if (comando.length()) Serial.printf("[JUEGO] comando: %s\n", comando.c_str());
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
  else mostrarErrorHttp("consulta", codigo);
  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== RimayMaki ESP32 Wi-Fi ===");
  Serial.printf("[CONFIG] Dispositivo: %s · API: %s\n", DEVICE_ID, API_URL);
  Serial.printf("[WIFI] Conectando a: %s\n", WIFI_SSID);
  for (int i = 0; i < 4; i++) pinMode(botones[i], INPUT_PULLDOWN);
  pinMode(LED_VERDE, OUTPUT); pinMode(LED_ROJO, OUTPUT);
  buzzerInit();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void loop() {
  mostrarEstadoWiFi();
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
