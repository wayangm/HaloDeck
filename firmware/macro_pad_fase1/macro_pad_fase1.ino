// ============================================================
// HALODECK - FASE 1a & 1b
// Board: Wemos D1 Mini (ESP8266)
// Tugas : Setup dasar + Protokol parsing USB Serial (prioritas)
// Komentar dalam Bahasa Indonesia
// ============================================================

// ---------- PIN & KONFIGURASI ----------
const int PIN_LED       = LED_BUILTIN;   // LED bawaan D1 Mini (aktif LOW)
const int LED_ON        = LOW;
const int LED_OFF       = HIGH;
const long BAUD_RATE    = 115200;        // Kecepatan serial standar

// ---------- VARIABEL STATUS ----------
String bufferSerial = "";                // Buffer penampung data masuk

// ---------- FUNGSI UTILITAS LED ----------
void ledNyala()   { digitalWrite(PIN_LED, LED_ON); }
void ledMati()    { digitalWrite(PIN_LED, LED_OFF); }
void kedipLed()   { ledNyala(); delay(30); ledMati(); delay(30); }

// ---------- PENANGANAN PERINTAH ----------
// Format protokol: "KATA:ARGUMEN" (contoh: "BTN:LOCK", "PROF:PHOTOSHOP")
void prosesPerintah(String perintah) {
  int posTitikDua = perintah.indexOf(':');

  // Perintah tunggal (tanpa argumen): PING, STAT
  if (posTitikDua == -1) {
    if (perintah == "PING") {
      Serial.println("PONG");
    } else if (perintah == "STAT") {
      Serial.println("OK:SIAP:FASE1");
    } else {
      Serial.println("ERR:FORMAT");
    }
    return;
  }

  String tipe = perintah.substring(0, posTitikDua);   // Mis. "BTN"
  String arg  = perintah.substring(posTitikDua + 1);  // Mis. "LOCK"
  tipe.toUpperCase();
  arg.toUpperCase();

  // ---- ROUTING PERINTAH (Fase 1c akan menambah ini) ----
  if (tipe == "PING") {
    Serial.println("PONG");

  } else if (tipe == "BTN") {
    // Perintah tombol universal (Tahap Awal)
    // Format: BTN:LOCK, BTN:MUTE, BTN:BROWSER, BTN:TASKMGR
    Serial.print("ACK:BTN:");
    Serial.println(arg);
    kedipLed();

  } else if (tipe == "PROF") {
    // Ganti profil aplikasi (context-switching)
    // Format: PROF:DEFAULT, PROF:PHOTOSHOP, PROF:PREMIERE, dst.
    Serial.print("ACK:PROF:");
    Serial.println(arg);
    kedipLed();

  } else if (tipe == "STAT") {
    Serial.println("OK:SIAP:FASE1");

  } else {
    Serial.println("ERR:PERINTAH_TIDAK_DIKENAL");
  }
}

// ---------- SETUP ----------
void setup() {
  pinMode(PIN_LED, OUTPUT);
  ledMati();

  Serial.begin(BAUD_RATE);
  delay(500);

  Serial.println();
  Serial.println("=========================================");
  Serial.println(" HALODECK - FASE 1");
  Serial.println(" Status: USB Serial PRIORITAS aktif");
  Serial.println("=========================================");
  Serial.println("OK:SIAP");

  for (int i = 0; i < 3; i++) kedipLed();
}

// ---------- LOOP UTAMA ----------
void loop() {
  while (Serial.available()) {
    char karakter = Serial.read();

    if (karakter == '\n' || karakter == '\r') {
      if (bufferSerial.length() > 0) {
        prosesPerintah(bufferSerial);
        bufferSerial = "";
      }
    } else {
      bufferSerial += karakter;
      if (bufferSerial.length() > 64) {
        Serial.println("ERR:PANJANG_BUFFER");
        bufferSerial = "";
      }
    }
  }
}
