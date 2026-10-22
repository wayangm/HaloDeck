// ============================================================
// HALODECK - FASE 2 (Firmware Final)
// Board: Wemos D1 Mini (ESP8266)
// Tugas :
//  - USB Serial PRIORITAS + Wi-Fi Station TCP :8080 CADANGAN (HP)
//  - Wi-Fi Station TCP :8082 khusus PC BRIDGE -> PC bisa bekerja
//    tanpa kabel USB (temukan IP via UDP :8081, lalu sambung :8082)
//  - Kredensial Wi-Fi DISIMPAN di LittleFS (tanpa edit kode!)
//  - Fallback hotspot "HALODECK-SETUP" bila belum ada kredensial
//    atau jaringan gagal -> HP kirim SSID+password via aplikasi
//  - UDP Discovery :8081 -> aplikasi Android & PC menemukan IP otomatis
// Komentar dalam Bahasa Indonesia
// ============================================================

#include <ESP8266WiFi.h>
#include <LittleFS.h>      // Sistem file untuk simpan kredensial
#include <WiFiUdp.h>       // Untuk fitur temukan-otomatis
#include <ESP8266WebServer.h>  // Halaman web setup (captive portal)
#include <DNSServer.h>         // Arahkan semua domain ke portal setup

// ---------- KONFIGURASI ----------
const int   PORT_TCP   = 8080;   // Port TCP (perintah dari HP)
const int   PORT_TCP_PC = 8082;  // Port TCP khusus PC bridge (tanpa USB)
const int   PORT_UDP   = 8081;   // Port UDP (discovery otomatis)
const long  BAUD_RATE  = 115200;
const char* NAMA_AP    = "HALODECK-SETUP";   // Hotspot fallback

// ---------- VARIABEL GLOBAL ----------
WiFiServer server(PORT_TCP);
WiFiServer serverPc(PORT_TCP_PC);   // Jalur khusus PC bridge (terpisah dari HP)
WiFiUDP udp;
ESP8266WebServer webServer(80);   // Portal setup di http://192.168.4.1
DNSServer dnsServer;              // Captive portal: semua domain -> portal
WiFiClient clientAktif;           // Client HP (port 8080)
WiFiClient clientPc;              // Client PC bridge (port 8082)
String bufferSerial = "";
String bufferTcp    = "";
String bufferTcpPc  = "";
bool   modeAP       = false;     // true = hotspot setup, false = station
bool   mintaRestart = false;     // Flag restart aman dari handler web
String ssidTersimpan = "";
String passTersimpan = "";

// ---------- LED ----------
void kedipLed() {
  digitalWrite(LED_BUILTIN, LOW);
  delay(25);
  digitalWrite(LED_BUILTIN, HIGH);
  delay(25);
}

// Deklarasi maju (didefinisikan di bawah)
void kirimKeHP(String pesan);
void kirimKePC(String pesan);

// ============================================================
// PENYIMPANAN KREDENSIAL (LittleFS) - TIDAK PERLU EDIT KODE
// ============================================================
void muatKredensial() {
  File berkas = LittleFS.open("/wifi.txt", "r");
  if (!berkas) return;
  ssidTersimpan = berkas.readStringUntil('\n');
  passTersimpan = berkas.readStringUntil('\n');
  berkas.close();
  ssidTersimpan.trim();
  passTersimpan.trim();
}

void simpanKredensial(String ssid, String pass) {
  File berkas = LittleFS.open("/wifi.txt", "w");
  if (!berkas) {
    Serial.println("ERR:GAGAL_SIMPAN");
    return;
  }
  berkas.println(ssid);
  berkas.println(pass);
  berkas.close();
  ssidTersimpan = ssid;
  passTersimpan = pass;
}

void hapusKredensial() {
  LittleFS.remove("/wifi.txt");
  ssidTersimpan = "";
  passTersimpan = "";
}

// ============================================================
// CAPTIVE PORTAL: halaman web setup di http://192.168.4.1
// Bisa diakses dari browser HP mana pun (tanpa aplikasi)
// ============================================================
const char HALAMAN_WEB[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Setup HaloDeck</title>
<style>
  body{font-family:sans-serif;background:#121212;color:#fff;
       display:flex;justify-content:center;padding:24px}
  .kartu{background:#1e1e2e;border-radius:12px;padding:24px;
         width:100%;max-width:360px}
  h2{margin-top:0;color:#4FC3F7}
  label{display:block;margin:14px 0 4px;color:#9e9e9e;font-size:14px}
  input{width:100%;padding:12px;border:none;border-radius:8px;
        background:#2a2a3d;color:#fff;font-size:16px;box-sizing:border-box}
  button{width:100%;margin-top:20px;padding:14px;border:none;
         border-radius:8px;background:#4FC3F7;color:#121212;
         font-size:16px;font-weight:bold}
  .catatan{color:#9e9e9e;font-size:12px;margin-top:16px}
</style>
</head>
<body>
<div class="kartu">
  <h2>Hybrid HaloDeck</h2>
  <p style="color:#9e9e9e;font-size:14px">
    Masukkan jaringan Wi-Fi rumah Anda. ESP8266 akan menyimpannya
    dan langsung menyambung (otomatis restart ~15 detik).</p>
  <form method="POST" action="/simpan">
    <label>Nama Jaringan (SSID)</label>
    <input name="ssid" id="ssid" required maxlength="32" autocomplete="off">
    <button type="button" onclick="pindai()" style="background:#2a2a3d;color:#4FC3F7;margin-top:8px">
      Pindai Jaringan di Sekitar</button>
    <div id="hasil" style="margin-top:8px"></div>
    <label>Password</label>
    <input name="sandi" type="password" maxlength="64">
    <button type="submit">Sambungkan</button>
  </form>
  <p class="catatan">Setelah tersambung, buka aplikasi HaloDeck —
     ia akan menemukan ESP secara otomatis.</p>
</div>
<script>
async function pindai(){
  var h=document.getElementById('hasil');
  h.innerHTML='<p style="color:#9e9e9e">Memindai sekitar 5 detik...</p>';
  try{
    var r=await fetch('/pindai');
    var d=await r.json();
    if(!d.length){h.innerHTML='<p style="color:#EF5350">Tidak ada jaringan. Coba lagi.</p>';return;}
    h.innerHTML=d.map(function(n){
      var nama=n.ssid?n.ssid:'(jaringan tersembunyi)';
      var kunci=n.aman?'[terkunci]':'[terbuka]';
      return '<div class="wifi" onclick="pilih(this)" data-ssid="'+
        n.ssid.replace(/"/g,'&quot;')+'" style="background:#2a2a3d;padding:10px;'+
        'margin:4px 0;border-radius:8px;cursor:pointer">'+nama+' '+kunci+
        ' <span style="color:#9e9e9e;font-size:12px">'+n.rssi+' dBm</span></div>';
    }).join('');
  }catch(e){h.innerHTML='<p style="color:#EF5350">Gagal memindai.</p>';}
}
function pilih(el){
  document.getElementById('ssid').value=el.getAttribute('data-ssid');
  document.getElementById('hasil').innerHTML='';
}
</script>
</body>
</html>
)rawliteral";

void tanganiHalamanUtama() {
  webServer.send_P(200, "text/html", HALAMAN_WEB);
}

// Handler: pindai jaringan Wi-Fi di sekitar -> JSON untuk halaman web
void tanganiPindaiWifi() {
  int jumlah = WiFi.scanNetworks();     // Pindai (mode AP_STA, ~3-5 detik)
  String json = "[";
  for (int i = 0; i < jumlah; i++) {
    if (i > 0) json += ",";
    String ssid = WiFi.SSID(i);
    ssid.replace("\"", "\\\"");         // Amankan tanda kutip dalam JSON
    bool aman = WiFi.encryptionType(i) != ENC_TYPE_NONE;
    json += "{\"ssid\":\"" + ssid + "\",\"rssi\":" + String(WiFi.RSSI(i)) +
            ",\"aman\":" + (aman ? "true" : "false") + "}";
  }
  json += "]";
  WiFi.scanDelete();                    // Bebaskan memori hasil pindai
  webServer.send(200, "application/json", json);
}

void tanganiSimpanWifi() {
  String ssid = webServer.arg("ssid");
  String sandi = webServer.arg("sandi");
  ssid.trim();

  if (ssid.length() == 0) {
    webServer.send(400, "text/plain", "SSID tidak boleh kosong!");
    return;
  }

  simpanKredensial(ssid, sandi);

  // Halaman konfirmasi sebelum restart (String biasa, karena memuat variabel)
  String halamanOk =
    "<!DOCTYPE html><html lang=\"id\"><head><meta charset=\"UTF-8\">"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
    "<style>body{font-family:sans-serif;background:#121212;color:#66BB6A;"
    "display:flex;justify-content:center;padding:48px;text-align:center}"
    ".kartu{background:#1e1e2e;border-radius:12px;padding:32px;max-width:360px}"
    "h2{color:#66BB6A;margin-top:0}p{color:#ccc}</style></head><body>"
    "<div class=\"kartu\"><h2>Tersimpan!</h2>"
    "<p>ESP8266 menyimpan jaringan <b>" + ssid + "</b> "
    "dan sedang menyambung ulang.</p>"
    "<p>Lupakan hotspot <b>HALODECK-SETUP</b>, kembali ke Wi-Fi rumah, "
    "lalu buka aplikasi HaloDeck — koneksi otomatis.</p></div></body></html>";
  webServer.send(200, "text/html", halamanOk);

  // Restart dari loop() agar respons web terkirim dulu
  mintaRestart = true;
}

void jalankanPortalSetup() {
  // DNS wildcard: semua domain diarahkan ke portal (captive portal)
  dnsServer.start(53, "*", WiFi.softAPIP());

  webServer.on("/", HTTP_GET, tanganiHalamanUtama);
  webServer.on("/simpan", HTTP_POST, tanganiSimpanWifi);
  webServer.on("/pindai", HTTP_GET, tanganiPindaiWifi);
  webServer.onNotFound(tanganiHalamanUtama);   // Tangkap pemeriksaan captive OS
  webServer.begin();
}

// ============================================================
// PEMROSES PERINTAH WIFI (diterima via Serial ATAU TCP)
// Format : WIFI:<SSID>:<PASSWORD>
//          WIFI:HAPUS   (hapus kredensial tersimpan)
// ============================================================
void prosesPerintahWifi(String arg) {
  arg.trim();

  String argBesar = arg;          // Salinan untuk pengecekan huruf besar
  argBesar.toUpperCase();
  if (argBesar == "HAPUS") {
    hapusKredensial();
    Serial.println("ACK:WIFI:DIHAPUS");
    kirimKeHP("ACK:WIFI:DIHAPUS");
    return;
  }

  // Pisahkan SSID dan password di titik dua PERTAMA setelah "WIFI:"
  int pos = arg.indexOf(':');
  if (pos == -1) {
    Serial.println("ERR:FORMAT_WIFI");
    kirimKeHP("ERR:FORMAT_WIFI");
    return;
  }

  String ssid = arg.substring(0, pos);
  String pass = arg.substring(pos + 1);
  ssid.trim();

  if (ssid.length() == 0) {
    Serial.println("ERR:SSID_KOSONG");
    kirimKeHP("ERR:SSID_KOSONG");
    return;
  }

  simpanKredensial(ssid, pass);
  Serial.print("ACK:WIFI:MENYIMPAN:");
  Serial.println(ssid);
  kirimKeHP("ACK:WIFI:MENYIMPAN");

  // Beri tahu sebelum restart agar HP sempat membaca balasan
  delay(1200);
  Serial.println("RESTART:MENGHUBUNGKAN_ULANG");
  ESP.restart();
}

// ---------- KIRIM KE HP (TCP) ----------
void kirimKeHP(String pesan) {
  if (clientAktif && clientAktif.connected()) {
    clientAktif.println(pesan);
    kedipLed();
  }
}

// ---------- KIRIM KE PC BRIDGE (TCP 8082) ----------
// Dipakai saat PC tersambung lewat Wi-Fi (kabel USB dicabut).
// Jalur serial TETAP dikirim juga agar monitor Arduino IDE tetap bisa
// memantau, dan agar PC yang tersambung via USB tidak kehilangan data.
void kirimKePC(String pesan) {
  if (clientPc && clientPc.connected()) {
    clientPc.println(pesan);
    kedipLed();
  }
  Serial.println(pesan);
}

// ============================================================
// PEMROSES DATA DARI HP (TCP)
// ============================================================
void prosesDataTcp(String data) {
  data.trim();
  if (data.length() == 0) return;

  int posTitikDua = data.indexOf(':');
  if (posTitikDua == -1) {
    if (data == "PING") {
      kirimKeHP("PONG");
    } else if (data == "STAT") {
      kirimKeHP("OK:SIAP:FASE2");
      kirimKeHP(modeAP ? "OK:MODE:AP" : "OK:MODE:STA");
    } else {
      kirimKeHP("ERR:FORMAT");
    }
    return;
  }

  String tipe = data.substring(0, posTitikDua);
  String arg  = data.substring(posTitikDua + 1);
  tipe.toUpperCase();

  if (tipe == "BTN") {
    arg.toUpperCase();
    kirimKePC("BTN:" + arg);            // Teruskan ke PC (TCP 8082 + serial)
    kirimKeHP("ACK:BTN:" + arg);
    kedipLed();

  } else if (tipe == "VOL") {
    // Slider volume dari HP. Angka murni, jadi TIDAK perlu toUpperCase
    // dan TIDAK perlu LED kedip (kiriman bisa banyak saat digeser).
    kirimKePC("VOL:" + arg);            // Teruskan ke PC (TCP 8082 + serial)

  } else if (tipe == "WIFI") {
    prosesPerintahWifi(arg);            // Simpan kredensial + restart

  } else if (tipe == "ACK" || tipe == "ERR") {
    // Balasan dari PC bridge (konfirmasi) -> jangan dibalas lagi,
    // supaya tidak terjadi loop saling membalas
    return;

  } else if (tipe == "PING") {
    kirimKeHP("PONG");

  } else if (tipe == "STAT") {
    kirimKeHP("OK:SIAP:FASE2");

  } else {
    kirimKeHP("ERR:PERINTAH_TIDAK_DIKENAL");
  }
}

// ============================================================
// PEMROSES DATA DARI PC BRIDGE (TCP 8082 — jalur tanpa USB)
// Protokol identik dengan jalur serial. Balasan dikirim HANYA ke
// clientPc (bukan Serial) supaya tidak menduplikasi kiriman
// kirimKePC() yang memang sudah mengirim ke dua tempat.
// ============================================================
void prosesDataTcpPc(String data) {
  data.trim();
  if (data.length() == 0) return;

  int posTitikDua = data.indexOf(':');
  if (posTitikDua == -1) {
    if (data == "PING") {
      clientPc.println("PONG");
    } else if (data == "STAT") {
      clientPc.println("OK:SIAP:FASE2");
    } else {
      clientPc.println("ERR:FORMAT");
    }
    return;
  }

  String tipe = data.substring(0, posTitikDua);
  String arg  = data.substring(posTitikDua + 1);
  tipe.toUpperCase();

  if (tipe == "PROF") {
    arg.toUpperCase();
    kirimKeHP("PROF:" + arg);           // Context-switching ke HP
    clientPc.println("ACK:PROF:" + arg);
    kedipLed();

  } else if (tipe == "VOL") {
    // Volume PC yang diubah lewat keyboard/tombol fisik -> teruskan ke HP
    // supaya posisi slider di HP ikut menyesuaikan (sinkron dua arah).
    kirimKeHP("VOL:" + arg);

  } else if (tipe == "ACK" || tipe == "ERR") {
    // Balasan konfirmasi -> jangan dibalas (hindari loop saling membalas)
    return;

  } else if (tipe == "PING") {
    clientPc.println("PONG");

  } else if (tipe == "STAT") {
    clientPc.println("OK:SIAP:FASE2");

  } else if (tipe == "BTN") {
    arg.toUpperCase();
    clientPc.println("ACK:BTN:" + arg);

  } else if (tipe == "WIFI") {
    prosesPerintahWifi(arg);            // Setup Wi-Fi juga bisa via TCP PC

  } else {
    clientPc.println("ERR:PERINTAH_TIDAK_DIKENAL");
  }
}

// ============================================================
// PEMROSES DATA DARI PC (Serial - jalur PRIORITAS)
// ============================================================
void prosesDataSerial(String data) {
  data.trim();
  if (data.length() == 0) return;

  int posTitikDua = data.indexOf(':');
  if (posTitikDua == -1) {
    if (data == "PING") {
      Serial.println("PONG");
    } else if (data == "STAT") {
      Serial.println("OK:SIAP:FASE2");
    } else {
      Serial.println("ERR:FORMAT");
    }
    return;
  }

  String tipe = data.substring(0, posTitikDua);
  String arg  = data.substring(posTitikDua + 1);
  tipe.toUpperCase();

  if (tipe == "PROF") {
    arg.toUpperCase();
    kirimKeHP("PROF:" + arg);           // Context-switching ke HP
    Serial.println("ACK:PROF:" + arg);
    kedipLed();

  } else if (tipe == "WIFI") {
    prosesPerintahWifi(arg);            // Setup Wi-Fi juga bisa via Serial

  } else if (tipe == "ACK" || tipe == "ERR") {
    // Balasan konfirmasi dari PC bridge -> jangan dibalas (hindari loop)
    return;

  } else if (tipe == "PING") {
    Serial.println("PONG");

  } else if (tipe == "STAT") {
    Serial.println("OK:SIAP:FASE2");

  } else if (tipe == "BTN") {
    arg.toUpperCase();
    Serial.println("ACK:BTN:" + arg);

  } else if (tipe == "VOL") {
    // Volume PC -> teruskan ke HP, supaya posisi slider di HP ikut
    // menyesuaikan (sinkron dua arah).
    //
    // PENTING: jangan pernah membalas "VOL:" lewat Serial.println di sini.
    // Serial adalah jalur dari PC bridge, sehingga apapun yang ditulis ke
    // situ akan dibaca bridge sebagai kiriman dari HP lalu dieksekusi
    // sebagai volume baru. Itu membuat loop pantulan tak berujung.
    // Cukup diteruskan ke HP, tanpa balasan apa pun.
    kirimKeHP("VOL:" + arg);

  } else {
    Serial.println("ERR:PERINTAH_TIDAK_DIKENAL");
  }
}

// ============================================================
// SETUP
// ============================================================
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);

  Serial.begin(BAUD_RATE);
  delay(500);

  Serial.println();
  Serial.println("=========================================");
  Serial.println(" HALODECK - FASE 2");
  Serial.println(" Serial: PRIORITAS | Wi-Fi: CADANGAN");
  Serial.println("=========================================");

  // --- Sistem file untuk kredensial ---
  LittleFS.begin();

  // --- Muat kredensial tersimpan (bila ada) ---
  muatKredensial();

  WiFi.mode(WIFI_STA);

  if (ssidTersimpan.length() > 0) {
    // --- Ada kredensial: coba sambung ke router ---
    Serial.print("Menghubungkan Wi-Fi: ");
    Serial.println(ssidTersimpan);
    WiFi.begin(ssidTersimpan.c_str(), passTersimpan.c_str());

    int percobaan = 0;
    while (WiFi.status() != WL_CONNECTED && percobaan < 30) {
      delay(500);
      Serial.print(".");
      percobaan++;
    }
  }

  if (WiFi.status() == WL_CONNECTED) {
    // --- SUKSES station mode (jalur cadangan aktif) ---
    modeAP = false;
    Serial.println();
    Serial.print("OK:WIFI:TERSAMBUNG:");
    Serial.println(WiFi.localIP());
    Serial.println("OK:MODE:STA");
  } else {
    // --- GAGAL / belum ada kredensial: buat hotspot setup ---
    // HP tinggal sambung ke "HALODECK-SETUP" dan kirim SSID+password
    modeAP = true;
    WiFi.mode(WIFI_AP_STA);        // AP + STA: hotspot sambil bisa PINDAI Wi-Fi
    WiFi.softAP(NAMA_AP);
    jalankanPortalSetup();          // Aktifkan halaman web http://192.168.4.1
    Serial.println();
    Serial.print("OK:MODE:AP - Hotspot: ");
    Serial.print(NAMA_AP);
    Serial.print(" | IP: ");
    Serial.println(WiFi.softAPIP());    // 192.168.4.1
    Serial.println("HP: sambung hotspot, kirim WIFI:<SSID>:<PASS>");
  }

  server.begin();
  serverPc.begin();                   // Jalur khusus PC bridge (TCP 8082)
  udp.begin(PORT_UDP);                  // Siap terima paket discovery

  // Catat sisa heap: ESP8266 punya ~40 KB, dan kini memuat DUA
  // WiFiServer + DUA WiFiClient. Angka ini dipantau saat pengujian
  // untuk memastikan tidak ada kebocoran memori antar siklus loop.
  Serial.print("OK:HEAP:");
  Serial.println(ESP.getFreeHeap());

  Serial.println("OK:SIAP");
  for (int i = 0; i < 3; i++) kedipLed();
}

// ============================================================
// LOOP UTAMA
// ============================================================
void loop() {
  // --- 0. Portal setup (mode AP): layani halaman web & DNS ---
  if (modeAP) {
    dnsServer.processNextRequest();
    webServer.handleClient();
    if (mintaRestart) {
      delay(500);                    // Beri waktu respons web terkirim tuntas
      Serial.println("RESTART:MENGHUBUNGKAN_ULANG");
      ESP.restart();
    }
  }

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
      if (bufferSerial.length() > 96) {
        Serial.println("ERR:PANJANG_BUFFER");
        bufferSerial = "";
      }
    }
  }

  // --- 2. Jalur CADANGAN: TCP dari HP ---
  // Selalu layani client baru: bila ada koneksi masuk, client lama
  // (kemungkinan stale/putus tak rapi) ditutup dan digantikan.
  // Tanpa ini, ESP bisa terkunci membaca client mati selamanya.
  WiFiClient baru = server.available();
  if (baru) {
    if (clientAktif) {
      clientAktif.stop();          // Tutup client lama (stale)
    }
    clientAktif = baru;
    clientAktif.setNoDelay(true);  // Latensi rendah untuk tombol makro
    kirimKeHP(modeAP ? "OK:TERHUBUNG:AP" : "OK:TERHUBUNG:STA");
  }

  if (clientAktif && clientAktif.connected()) {
    while (clientAktif.available()) {
      char c = clientAktif.read();
      if (c == '\n' || c == '\r') {
        if (bufferTcp.length() > 0) {
          prosesDataTcp(bufferTcp);
          bufferTcp = "";
        }
      } else {
        bufferTcp += c;
        if (bufferTcp.length() > 96) {
          kirimKeHP("ERR:PANJANG_BUFFER");
          bufferTcp = "";
        }
      }
    }
  }

  // --- 2b. Jalur PC BRIDGE: TCP 8082 (dipakai saat kabel USB dicabut) ---
  // Port TERPISAH dari HP supaya keduanya tidak saling mengusir client.
  WiFiClient baruPc = serverPc.available();
  if (baruPc) {
    if (clientPc) {
      clientPc.stop();            // Tutup client lama (stale)
    }
    clientPc = baruPc;
    clientPc.setNoDelay(true);
    clientPc.println(modeAP ? "OK:TERHUBUNG:AP" : "OK:TERHUBUNG:STA");
    Serial.println("OK:PC_BRIDGE:TERHUBUNG");
  }

  if (clientPc && clientPc.connected()) {
    while (clientPc.available()) {
      char c = clientPc.read();
      if (c == '\n' || c == '\r') {
        if (bufferTcpPc.length() > 0) {
          prosesDataTcpPc(bufferTcpPc);
          bufferTcpPc = "";
        }
      } else {
        bufferTcpPc += c;
        if (bufferTcpPc.length() > 96) {
          clientPc.println("ERR:PANJANG_BUFFER");
          bufferTcpPc = "";
        }
      }
    }
  } else if (clientPc) {
    // Client PC hilang (putus/timeout) -> bersihkan agar siap menerima
    // koneksi berikutnya tanpa harus menunggu koneksi baru masuk.
    clientPc.stop();
    bufferTcpPc = "";
  }

  // --- 3. UDP Discovery: HP broadcast "DISCOVER" -> ESP balas IP ---
  int ukuranPaket = udp.parsePacket();
  if (ukuranPaket) {
    String isi = udp.readStringUntil('\n');
    isi.trim();
    String isiBesar = isi;        // Salinan untuk pengecekan huruf besar
    isiBesar.toUpperCase();
    if (isiBesar == "DISCOVER") {
      udp.beginPacket(udp.remoteIP(), udp.remotePort());
      udp.print("HALODECK:");
      udp.print(modeAP ? "AP" : "STA");
      udp.print(":");
      udp.println(modeAP ? WiFi.softAPIP() : WiFi.localIP());
      udp.endPacket();
    }
  }
}
