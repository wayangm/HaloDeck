# HaloDeck

[![Rilis](https://img.shields.io/github/v/release/wayangm/HaloDeck?label=rilis)](https://github.com/wayangm/HaloDeck/releases)
[![Lisensi](https://img.shields.io/badge/lisensi-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Android%20%7C%20ESP8266-lightgrey.svg)](https://github.com/wayangm/HaloDeck)

Makro pad hybrid: **Android (HP) → ESP8266 → PC Windows**, dengan
context-switching otomatis (PC mendeteksi aplikasi aktif, HP menampilkan
tombol makro yang sesuai).

Kode **100% terbuka** (MIT) — versi Windows berupa `.py` asli, jadi bisa
dibaca, dimodifikasi, dan ditiru bebas. Installer hanya membungkusnya
bersama Python portable.

## Mulai Cepat (Windows)

1. Unduh **`HaloDeck-Win-Setup-<versi>.exe`** dari
   [Releases](https://github.com/wayangm/HaloDeck/releases) → jalankan → *Next*
   sampai selesai (instal per-user, **tanpa admin**).
2. Konektor langsung menyala sebagai **tray icon** dan otomatis terdaftar di
   Startup Windows.
3. Unduh **`HaloDeck-Android-1.0.0.apk`** → pindah ke HP → instal.
   *Uninstall dulu aplikasi lama (`com.wgmedia.macropad`) bila ada.*
4. Flash ESP8266 dengan **`HaloDeck-ESP-1.0.0.bin`** (lihat bagian *Firmware*),
   lalu buka aplikasi **HaloDeck** di HP — IP ESP ditemukan otomatis lewat UDP.

> Ingin tanpa instalasi / mau lihat kodenya dulu? Unduh
> `HaloDeck-Win-<versi>.zip` (kode `.py` murni) dan jalankan
> `pythonw connector_app.py` dengan Python 3.10 + `pip install pyserial pystray pillow`.

## Arsitektur

```
┌─────────────┐   USB Serial (PRIORITAS)   ┌──────────────────┐
│  PC Windows │◄──────────────────────────►│  Wemos D1 Mini   │
│  (Bridge    │   COM4 @ 115200 baud       │  (ESP8266)       │
│   Python)   │                            │                  │
└──────┬──────┘                            └────────┬─────────┘
       │ Deteksi active window                     │ Wi-Fi Station
       │ Eksekusi aksi (lock, mute, dll)           │ TCP :8080 (CADANGAN)
       │                                           │
       │                            ┌──────────────▼─────────┐
       │   PROF:<NAMA> (dari PC)    │  HP Android (Kotlin)   │
       └────────────────────────────│  Tombol makro dinamis  │
                                    └────────────────────────┘
```

**Aturan jalur:** USB Serial selalu prioritas (latensi nol + suplai daya).
Wi-Fi hanya cadangan — internet PC & HP tetap normal karena ESP8266
mode Station (menumpang router yang sama).

## Struktur Proyek

```
HaloDeck/
├── LICENSE                      Lisensi MIT
├── firmware/
│   ├── macro_pad_fase1/         Firmware dasar (Serial only) — arsip
│   ├── macro_pad_fase1c/        Firmware stabil (Serial + Wi-Fi TCP)
│   └── macro_pad_fase2/         Firmware final & disarankan (Wi-Fi + portal setup)
├── pc_bridge/
│   ├── bridge_fase2a.py         Deteksi active window + serial
│   ├── bridge_fase2b.py         Bridge terintegrasi (JALANKAN INI)
│   ├── aksi.py                  20 aksi: LOCK, MUTE, makro PS/PR, dll
│   ├── connector_app.py         Konektor tray (auto-start Windows)
│   ├── versi.py                 Nomor versi (satu-satunya sumber)
│   ├── updater.py               Pembaruan otomatis dari GitHub Releases
│   └── update_config.json       Repo rilis + preferensi pembaruan
├── tools/
│   ├── buat_paket_rilis.py      Kemas pc_bridge -> dist/*.zip (buat rilis)
│   └── buat_installer.py        Rakit installer Inno Setup (dist/*.exe)
├── tester/
│   └── tes_fase1.py             Test otomatis protokol (11/11 lulus)
└── android_app/                 Proyek Android native (Kotlin)
    ├── gradlew                  Wrapper Gradle 8.10
    └── app/src/main/java/com/halodeck/macropad/
```
> Folder `build/`, `dist/`, dan `android_app/app/build/` adalah hasil build —
> tidak ikut di-commit. APK debug: `android_app/gradlew assembleDebug`.

## Cara Pakai

### 1. Firmware (sekali saja)

**Cara cepat — pakai berkas `.bin` dari rilis (tanpa Arduino IDE):**

```powershell
# Unduh HaloDeck-ESP-1.0.0.bin dari rilis, lalu flash:
pip install esptool
esptool.py --port COM4 erase_flash
esptool.py --port COM4 --baud 460800 write_flash 0x0 HaloDeck-ESP-1.0.0.bin
```

| Berkas rilis | Untuk siapa |
|---|---|
| `HaloDeck-ESP-1.0.0.bin` | **Disarankan** — firmware final (fase2): portal setup `HALODECK-SETUP`, SSID tidak perlu diedit di kode |
| `HaloDeck-ESP-1.0.0-fase1c.bin` | Varian stabil (fase1c): Serial + Wi-Fi TCP, SSID diisi di kode |

**Cara build sendiri (dari sumber):**

- Isi SSID & password Wi-Fi di `firmware/macro_pad_fase1c/macro_pad_fase1c.ino`
  (2 baris: `SSID_KAMU` dan `PASSWORD_KAMU`), lalu upload via Arduino IDE
  atau arduino-cli. Board: **LOLIN(WEMOS) D1 R2 & mini**.
- Lihat Serial Monitor @115200 — catat IP yang tampil (`OK:WIFI:TERSAMBUNG:<IP>`).
- Firmware `macro_pad_fase2` menyimpan kredensial di LittleFS + punya portal
  setup (`HALODECK-SETUP`) sehingga SSID tidak perlu diedit di kode.
- Dengan arduino-cli:
  ```powershell
  arduino-cli core install esp8266:esp8266 \
    --additional-urls https://arduino.esp8266.com/stable/package_esp8266com_index.json
  arduino-cli compile --fqbn esp8266:esp8266:d1_mini --export-binaries firmware/macro_pad_fase2
  ```

### 2. Konektor Windows (OTOMATIS — tidak perlu dijalankan manual)
Aplikasi konektor berjalan **otomatis bersama Windows** sebagai tray icon,
tanpa jendela konsol.

- **Status otomatis:** terdaftar di Startup Windows (Registry HKCU Run) —
  menyala sendiri saat login, mati sendiri saat logout.
- **Tray icon:** titik **hijau** = ESP tersambung, **merah** = masih mencari.
- **Menu tray** (klik kanan ikon):
  - *Status / Profil aktif / Jumlah aksi* — pantauan langsung
  - *Jalankan Ulang Koneksi* — sambung ulang ke ESP
  - *Mulai Otomatis Bersama Windows* — toggle on/off
  - *Buka Berkas Log* — lihat riwayat di `pc_bridge/konektor.log`
  - *Versi … / Periksa Pembaruan / Pasang Pembaruan* — pembaruan otomatis
  - *Keluar*

Menjalankan manual (hanya bila perlu):
```
pythonw <folder-hasil-instalasi>\app\connector_app.py
```
> `pythonw` (bukan `python`) agar tanpa jendela konsol. Aman dijalankan
> berkali-kali — aplikasi kedua otomatis keluar (anti double-instance).

Berkas:
- `connector_app.py` — aplikasi konektor (tray + auto-start)
- `versi.py` — nomor versi aplikasi PC (satu-satunya sumber)
- `updater.py` + `update_config.json` — pembaruan otomatis (bagian 4)
- `konektor.log` — riwayat log (heartbeat PONG sengaja tidak dicatat)

### 3. Aplikasi Android

**Cara cepat:** unduh **`HaloDeck-Android-1.0.0.apk`** dari
[Releases](https://github.com/wayangm/HaloDeck/releases) → pindah ke HP →
buka untuk instal (izin "sumber tidak dikenal" perlu sekali).

> **Penting — migrasi dari versi lama:** `applicationId` kini
> `com.halodeck.macropad`, sedangkan versi lama masih `com.wgmedia.macropad`.
> Keduanya dianggap aplikasi berbeda, jadi **uninstall yang lama dulu** sebelum
> memasang yang baru.

**Build sendiri:**
- `android_app/gradlew assembleDebug` (butuh Android SDK + Java 17+), hasilnya
  `android_app/app/build/outputs/apk/debug/app-debug.apk`.

**Cara pakai:**
- Buka **HaloDeck** di HP (temuan otomatis lewat UDP — IP tidak perlu diketik),
  atau masukkan IP ESP8266 (dari Serial Monitor) port `8080` lalu **Hubungkan**.
- Buka aplikasi lain di PC (Photoshop, Premiere, Notepad) — tombol di HP
  otomatis berganti mengikuti aplikasi aktif.

### 4. Pembaruan Otomatis (GitHub Releases)

Konektor memeriksa rilis terbaru **setiap 24 jam** (sekali tiap hari), bisa
juga dicek manual dari menu tray. Bila ada versi lebih baru: unduh paket →
cocokkan checksum SHA-256 → cadangkan `.py` lama → timpa → **tutup &
buka lagi dirinya sendiri**.

**Konfigurasi** — `pc_bridge/update_config.json`:

```json
{
  "repo": "wayangm/HaloDeck",
  "prefiks_aset": "halodeck-win",
  "cek_otomatis": true,
  "pasang_otomatis": false
}
```

| Kolom | Arti |
|---|---|
| `repo` | Repo GitHub tempat rilis diunggah — *wajib diisi* |
| `prefiks_aset` | Awalan nama asset zip yang dipakai (mis. `HaloDeck-Win-1.1.0.zip`) |
| `cek_otomatis` | `false` = matikan pengecekan berkala |
| `pasang_otomatis` | `true` = langsung pasang tanpa konfirmasi (default `false`) |

> Satu repo dipakai bersama untuk rilis Windows **dan** nanti rilis ESP —
> pembatasnya adalah awalan asset: `HaloDeck-Win-*` (PC) dan `HaloDeck-ESP-*`
> (firmware), sehingga updater tiap komponen hanya mengambil paketnya sendiri.

**Menu tray bagian pembaruan:**
- `Versi 1.0.0 — ...` — status versi saat ini
- `Periksa Pembaruan` — cek sekarang juga
- `Pasang Pembaruan 1.1.0` — hanya muncul bila ada rilis lebih baru;
  muncul konfirmasi dulu, lalu aplikasi menutup diri, memasang, dan
  membuka kembali otomatis

**Pengaman yang dipasang updater:**
- Paket **ditolak** bila checksum tidak cocok, zip tidak memuat `versi.py`,
  struktur tidak dikenal, atau versi paket **tidak lebih baru** (anti-downgrade)
- `update_config.json`, `konektor.log`, `konektor.lock` **tidak pernah**
  ditimpa update
- Sebelum menimpa, semua `.py` dicadangkan ke `<instalasi>/app/_cadangan/`
  (5 cadangan terakhir disimpan)

## Menerbitkan Rilis

```powershell
# 1. Naikkan VERSI di pc_bridge/versi.py (mis. 1.0.0 -> 1.1.0)
python tools/buat_paket_rilis.py      # -> dist/HaloDeck-Win-<v>.zip + .sha256
python tools/buat_installer.py        # -> dist/HaloDeck-Win-Setup-<v>.exe + .sha256

# 2. (Bila firmware berubah) kompile ESP -> .bin, lalu salin ke dist/
arduino-cli compile --fqbn esp8266:esp8266:d1_mini --export-binaries firmware/macro_pad_fase2
cp firmware/macro_pad_fase2/build/esp8266.esp8266.d1_mini/macro_pad_fase2.ino.bin dist/HaloDeck-ESP-<v>.bin

# 3. (Bila Android berubah) build APK -> salin ke dist/
android_app/gradlew assembleDebug
cp android_app/app/build/outputs/apk/debug/app-debug.apk dist/HaloDeck-Android-<v>.apk

# 4. Beri label checksum pada tiap berkas, commit & push
foreach ($f in Get-ChildItem dist/*-<v>.* -Exclude *.sha256) {
  "$((Get-FileHash $f -Algorithm SHA256).Hash.ToLower())  $($f.Name)" | Set-Content "$($f.FullName).sha256"
}
git add -A; git commit -m "rilis v1.1.0"; git push

# 5. Terbitkan rilis + unggah semua asset
gh release create v1.1.0 (Get-ChildItem dist/*-1.1.0.*) `
  --title "HaloDeck v1.1.0" --notes "Catatan rilis..."
```

**Berkas rilis** (pemisah antar komponen = awalan nama, jadi updater tiap
komponen hanya mengambil paketnya sendiri):

| Awalan asset | Komponen |
|---|---|
| `HaloDeck-Win-Setup-<v>.exe` | Installer Windows (**utama**) |
| `HaloDeck-Win-<v>.zip` | Kode `.py` murni untuk Windows |
| `HaloDeck-ESP-<v>.bin` | Firmware ESP8266 (d1_mini) |
| `HaloDeck-Android-<v>.apk` | Aplikasi HP |

Syarat build installer: **Inno Setup 6** (`winget install JRSoftware.InnoSetup`)
dan Python 3.10 (untuk mengambil dependensi). Skrip mengunduh Python portable
resmi, menaruh `pyserial`/`pystray`/`Pillow`, lalu menyalin `.py` HaloDeck
apa adanya — **tidak dikompilasi**.

## Daftar Profil & Makro

| Profil (aplikasi aktif) | Tombol di HP |
|---|---|
| DEFAULT / lainnya | Kunci PC, Mute, Browser, Task Manager |
| Notepad | Simpan, Baru, Undo, Redo |
| VS Code | Simpan, Undo, Redo, Kunci PC |
| Photoshop | Zoom In/Out, Fit Layar, Layer Baru, Flatten |
| Premiere Pro | Undo, Cut, Mark In, Mark Out, Export Frame |
| Browser | Tab Baru, Simpan, Undo, Kunci PC |

## Roadmap Pengujian (sesuai PRD)

- [x] **Tahap 1 — Universal:** LOCK, MUTE, BROWSER, TASKMGR (teruji otomatis)
- [x] **Tahap 2 — Produktivitas:** Notepad, VS Code (aksi teruji)
- [x] **Tahap 3 — Kreatif:** Photoshop, Premiere (makro teruji import; uji
      manual di aplikasinya masing-masing)
- [x] **Tahap 4 — Distribusi:** installer Inno Setup + updater GitHub Releases +
      rilis firmware (`.bin`) dan APK di GitHub Releases

## Protokol Serial/TCP

Format: `KATA:ARGUMEN` (satu baris per perintah, diakhiri newline).

| Perintah | Arah | Arti |
|---|---|---|
| `PING` / `PONG` | dua arah | Heartbeat |
| `BTN:<AKSI>` | HP→PC | Eksekusi aksi (LOCK, MUTE, PS_ZOOMIN, dst.) |
| `PROF:<NAMA>` | PC→HP | Context-switching profil |
| `ACK:...` | balasan | Konfirmasi diterima |
| `ERR:...` | balasan | Format salah / tak dikenal |
| `DISCOVER` → `HALODECK:<MODE>:<IP>` | HP↔ESP (UDP :8081) | Temuan otomatis IP ESP (`STA` = normal, `AP` = mode hotspot `HALODECK-SETUP`) |
| `WIFI:<SSID>:<PASS>` | HP→ESP | Simpan kredensial Wi-Fi lalu ESP restart |

## Lisensi

[MIT](LICENSE) — bebas dipakai, dimodifikasi, dan didistribusikan, dengan
syarat pemberitahuan hak cipta tetap ada.

Kode `.py` sengaja tidak dikompilasi supaya siapa pun bisa membaca dan
mengembangkannya; `python.exe` di dalam installer hanyalah mesin Python
portable resmi dari python.org.
