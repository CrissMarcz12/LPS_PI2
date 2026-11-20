#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <BLE2902.h>

// RimayMaki: control Bluetooth BLE para Chrome/Android.
// Boton 1: inicio / detener. Boton 2: siguiente / confirmar.
// Boton 3: activar o silenciar buzzer. Boton 4: reiniciar.
const int botones[4] = {23, 21, 18, 16};
const int LED_VERDE = 27;
const int LED_ROJO = 25;
const int BUZZER = 32;

const char *DEVICE_NAME = "RIMAYMAKI-ESP32";
#define SERVICE_UUID "5d8f6d58-7190-4c4d-9f9e-910daebaa001"
#define CHANNEL_UUID "5d8f6d58-7190-4c4d-9f9e-910daebaa002"

BLECharacteristic *canalBLE = nullptr;
bool tabletConectada = false;
bool sonidoActivo = true;
bool estadoPrevio[4] = {false, false, false, false};
unsigned long ultimoBoton[4] = {0, 0, 0, 0};
const unsigned long ANTIRREBOTE_MS = 45;

enum Feedback { SIN_FEEDBACK, ACIERTO, ERROR_SENA };
Feedback feedbackActual = SIN_FEEDBACK;
unsigned long siguienteCambio = 0;
int faseFeedback = 0;

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

void sonar(int frecuencia) {
  if (!sonidoActivo) return;
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWriteTone(BUZZER, frecuencia);
#else
  ledcWriteTone(0, frecuencia);
#endif
}

void detenerFeedback() {
  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_ROJO, LOW);
  apagarBuzzer();
  feedbackActual = SIN_FEEDBACK;
  faseFeedback = 0;
}

void acierto() {
  detenerFeedback();
  digitalWrite(LED_VERDE, HIGH);
  sonar(1050);
  feedbackActual = ACIERTO;
  faseFeedback = 0;
  siguienteCambio = millis() + 160;
}

void error() {
  detenerFeedback();
  digitalWrite(LED_ROJO, HIGH);
  sonar(310);
  feedbackActual = ERROR_SENA;
  faseFeedback = 0;
  // El error se repite hasta que la aplicación indique que la mano cambió.
  siguienteCambio = millis() + 220;
}

void actualizarFeedback() {
  if (feedbackActual == SIN_FEEDBACK || millis() < siguienteCambio) return;

  if (feedbackActual == ACIERTO && faseFeedback == 0) {
    digitalWrite(LED_VERDE, LOW);
    apagarBuzzer();
    faseFeedback = 1;
    siguienteCambio = millis() + 70;
    return;
  }

  if (feedbackActual == ACIERTO && faseFeedback == 1) {
    digitalWrite(LED_VERDE, HIGH);
    sonar(1550);
    faseFeedback = 2;
    siguienteCambio = millis() + 220;
    return;
  }

  // Error: rojo y buzzer alternados, despacio y visibles.
  // No usamos delay(), por eso los botones Bluetooth siguen respondiendo.
  if (feedbackActual == ERROR_SENA) {
    if (faseFeedback == 0) {
      digitalWrite(LED_ROJO, LOW);
      apagarBuzzer();
      faseFeedback = 1;
      siguienteCambio = millis() + 170;
    } else {
      digitalWrite(LED_ROJO, HIGH);
      sonar(310);
      faseFeedback = 0;
      siguienteCambio = millis() + 260;
    }
    return;
  }

  detenerFeedback();
}

void enviarTablet(const String &mensaje) {
  Serial.println(mensaje);
  if (!tabletConectada || canalBLE == nullptr) return;
  canalBLE->setValue(mensaje.c_str());
  canalBLE->notify();
}

class ServidorCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *servidor) override {
    tabletConectada = true;
    Serial.println("Bluetooth conectado");
  }

  void onDisconnect(BLEServer *servidor) override {
    tabletConectada = false;
    Serial.println("Bluetooth desconectado; esperando nueva conexion");
    BLEDevice::startAdvertising();
  }
};

class CanalCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *caracteristica) override {
    // En ESP32 core 3.3.x getValue() devuelve String, no std::string.
    String comando = caracteristica->getValue();
    comando.trim();
    comando.toUpperCase();

    if (comando.length() == 0) return;

    Serial.print("Comando de tablet: ");
    Serial.println(comando);

    if (comando == "BIEN") acierto();
    else if (comando == "MAL") error();
    else if (comando == "DETENER_ERROR" && feedbackActual == ERROR_SENA) detenerFeedback();
    else if (comando == "SILENCIO_ON") {
      sonidoActivo = false;
      apagarBuzzer();
      enviarTablet("SONIDO_APAGADO");
    } else if (comando == "SILENCIO_OFF") {
      sonidoActivo = true;
      enviarTablet("SONIDO_ACTIVADO");
    } else if (comando == "PING") {
      enviarTablet("PONG");
    }
  }
};

void iniciarBluetooth() {
  BLEDevice::init(DEVICE_NAME);

  BLEServer *servidor = BLEDevice::createServer();
  servidor->setCallbacks(new ServidorCallbacks());

  BLEService *servicio = servidor->createService(SERVICE_UUID);
  canalBLE = servicio->createCharacteristic(
    CHANNEL_UUID,
    BLECharacteristic::PROPERTY_READ |
    BLECharacteristic::PROPERTY_WRITE |
    BLECharacteristic::PROPERTY_NOTIFY
  );

  canalBLE->addDescriptor(new BLE2902());
  canalBLE->setCallbacks(new CanalCallbacks());
  canalBLE->setValue("RIMAYMAKI_LISTO");
  servicio->start();

  BLEAdvertising *publicidad = BLEDevice::getAdvertising();
  publicidad->addServiceUUID(SERVICE_UUID);
  publicidad->setScanResponse(true);
  BLEDevice::startAdvertising();

  Serial.println("BLE listo: RIMAYMAKI-ESP32");
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 4; i++) pinMode(botones[i], INPUT_PULLDOWN);

  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_ROJO, OUTPUT);
  buzzerInit();
  detenerFeedback();

  iniciarBluetooth();
}

void loop() {
  actualizarFeedback();

  for (int i = 0; i < 4; i++) {
    bool presionado = digitalRead(botones[i]) == HIGH;
    unsigned long ahora = millis();

    if (presionado && !estadoPrevio[i] && ahora - ultimoBoton[i] >= ANTIRREBOTE_MS) {
      ultimoBoton[i] = ahora;
      enviarTablet("BTN" + String(i + 1));
    }
    estadoPrevio[i] = presionado;
  }
}
