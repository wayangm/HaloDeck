// ============================================================
// HALODECK - FASE 1c
// Board: Wemos D1 Mini (ESP8266)
// Tugas : Wi-Fi Station Mode + TCP Server (jalur CADANGAN)
//         Routing dua arah: Serial (prioritas) <-> Wi-Fi
//         - Dari HP (Wi-Fi):  "BTN:<AKSI>"   -> diteruskan ke PC (Serial)
//         - Dari PC (Serial): "PROF:<NAMA>"  -> diteruskan ke HP (Wi-Fi)
// Komentar dalam Bahasa Indonesia
// ============================================================

#include <ESP8266WiFi.h>

// ---------- KONFIGURASI WI-FI (ISI DENGAN MILIK ANDA) ----------
const char* SSID_KAMU     = "ISI_NAMA_WIFI_ANDA";   // <-- GANTI
const char* PASSWORD_KAMU = "ISI_PASSWORD_WIFI";    // <-- GANTI
const int   PORT_TCP      = 8080;                   // Port server di ESP8266

// ---------- KONFIGURASI SERIAL (PRIORITAS) ----------
const long BAUD_RATE = 115200;

// ---------- VARIABEL GLOBAL ----------
WiFiServer server(PORT_TCP);
WiFiClient clientAktif;          // Client HP yang sedang terhubung
String bufferSerial = "";        // Buffer data dari PC
String bufferTcp    = "";        // Buffer data dari HP

// ---------- LED INDIKATOR ----------
void kedipLed() {
  digitalWrite(LED_BUILTIN, LOW);
  delay(25);
  digitalWrite(LED_BUILTIN, HIGH);
  delay(25);
}

// ---------- KIRIM KE HP (via TCP, bila ada client) ----------
void kirimKeHP(String pesan) {
  if (clientAktif && clientAktif.connected()) {
    clientAktif.println(pesan);
    kedipLed();
  }
}

// ---------- TERIMA DARI HP, TERUSKAN KE PC (Serial) ----------
void prosesDataTcp(String data) {
  data.trim();
  if (data.length() == 0) return;

  int posTitikDua = data.indexOf(':');
  if (posTitikDua == -1) {
    if (data == "PING") {
      kirimKeHP("PONG");          // Heartbeat dari HP
    } else if (data == "STAT") {
      kirimKeHP("OK:SIAP:FASE1C");
    } else {
      kirimKeHP("ERR:FORMAT");
    }
    return;
  }

  String tipe = data.substring(0, posTitikDua);
  String arg  = data.substring(posTitikDua + 1);
  tipe.toUpperCase();
  arg.toUpperCase();

  if (tipe == "PING") {
    // Heartbeat dari HP dijawab langsung oleh ESP8266
    kirimKeHP("PONG");

  } else if (tipe == "BTN") {
    // Perintah tombol dari HP -> TERUSKAN ke PC via Serial (prioritas)
    Serial.println("BTN:" + arg);
    kirimKeHP("ACK:BTN:" + arg);   // Konfirmasi ke HP
    kedipLed();

  } else if (tipe == "STAT") {
    kirimKeHP("OK:SIAP:FASE1C");

  } else {
    kirimKeHP("ERR:PERINTAH_TIDAK_DIKENAL");
  }
}

// ---------- TERIMA DARI PC (Serial), ROUTING ----------
void prosesDataSerial(String data) {
  data.trim();
  if (data.length() == 0) return;

  int posTitikDua = data.indexOf(':');
  if (posTitikDua == -1) {
    if (data == "PING") {
      Serial.println("PONG");     // Heartbeat dari PC bridge
    } else if (data == "STAT") {
      Serial.println("OK:SIAP:FASE1C");
    } else {
      Serial.println("ERR:FORMAT");
    }
    return;
  }

  String tipe = data.substring(0, posTitikDua);
  String arg  = data.substring(posTitikDua + 1);
  tipe.toUpperCase();
  arg.toUpperCase();

  if (tipe == "PROF") {
    // Update profil dari deteksi PC -> TERUSKAN ke HP
    kirimKeHP("PROF:" + arg);
    Serial.println("ACK:PROF:" + arg);
    kedipLed();

  } else if (tipe == "PING") {
    Serial.println("PONG");

  } else if (tipe == "STAT") {
    Serial.println("OK:SIAP:FASE1C");

  } else if (tipe == "BTN") {
    // Pintasan: PC juga boleh kirim BTN (jarang dipakai, untuk uji)
    Serial.println("ACK:BTN:" + arg);

  } else {
    Serial.println("ERR:PERINTAH_TIDAK_DIKENAL");
  }
}

// ---------- SETUP ----------
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);

  Serial.begin(BAUD_RATE);
  delay(500);

  Serial.println();
  Serial.println("=========================================");
  Serial.println(" HALODECK - FASE 1c");
  Serial.println(" Serial: PRIORITAS | Wi-Fi: CADANGAN");
  Serial.println("=========================================");

  // --- Sambung Wi-Fi Station Mode (menumpang router yang sama) ---
  WiFi.mode(WIFI_STA);              // BUKAN Access Point -> internet PC/HP normal
  WiFi.begin(SSID_KAMU, PASSWORD_KAMU);
  Serial.print("Menghubungkan Wi-Fi");
  int percobaan = 0;
  while (WiFi.status() != WL_CONNECTED && percobaan < 40) {
    delay(500);
    Serial.print(".");
    percobaan++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("OK:WIFI:TERSAMBUNG:");
    Serial.println(WiFi.localIP());   // IP ini harus dimasukkan di aplikasi Android
    server.begin();
  } else {
    Serial.println();
    Serial.println("WIFI:GAGAL (jalur USB Serial tetap jalan - prioritas)");
    // Sistem TETAP berfungsi via USB Serial meski Wi-Fi gagal
  }

  Serial.println("OK:SIAP");
  for (int i = 0; i < 3; i++) kedipLed();
}

// ---------- LOOP UTAMA ----------
void loop() {
  // --- 1. Jalur PRIORITAS: Serial dari PC ---
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (bufferSerial.length() > 0) {
        prosesDataSerial(bufferSerial);
        bufferSerial = "";
      }
    } else {
      bufferSerial += c;
      if (bufferSerial.length() > 64) {
        Serial.println("ERR:PANJANG_BUFFER");
        bufferSerial = "";
      }
    }
  }

  // --- 2. Jalur CADANGAN: Wi-Fi TCP dari HP ---
  if (WiFi.status() == WL_CONNECTED) {
    // Terima client baru (HP) bila belum ada
    if (!clientAktif || !clientAktif.connected()) {
      WiFiClient baru = server.available();
      if (baru) {
        clientAktif = baru;
        kirimKeHP("OK:TERHUBUNG:FASE1C");
      }
    } else {
      // Baca data dari HP yang sedang terhubung
      while (clientAktif.available()) {
        char c = clientAktif.read();
        if (c == '\n' || c == '\r') {
          if (bufferTcp.length() > 0) {
            prosesDataTcp(bufferTcp);
            bufferTcp = "";
          }
        } else {
          bufferTcp += c;
          if (bufferTcp.length() > 64) {
            kirimKeHP("ERR:PANJANG_BUFFER");
            bufferTcp = "";
          }
        }
      }
    }
  }
}
