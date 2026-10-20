# HaloDeck

Makro pad hybrid: **Android (HP) → ESP8266 → PC Windows**, dengan
context-switching otomatis (PC mendeteksi aplikasi aktif, HP menampilkan
tombol makro yang sesuai).

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
├── firmware/
│   ├── macro_pad_fase1/       Firmware dasar (Serial only) — arsip
│   └── macro_pad_fase1c/      Firmware AKTIF (Serial + Wi-Fi TCP)
├── pc_bridge/
│   ├── bridge_fase2a.py       Deteksi active window + serial
│   ├── bridge_fase2b.py       Bridge terintegrasi (JALANKAN INI)
│   ├── aksi.py                20 aksi: LOCK, MUTE, makro PS/PR, dll
│   ├── connector_app.py       Konektor tray (auto-start Windows)
│   ├── versi.py               Nomor versi (satu-satunya sumber)
│   ├── updater.py             Pembaruan otomatis dari GitHub Releases
│   └── update_config.json     Repo rilis + preferensi pembaruan
├── tools/
│   └── buat_paket_rilis.py    Kemas pc_bridge -> dist/*.zip (buat rilis)
├── dist/                      Paket rilis hasil tools (tidak di-commit)
├── tester/
│   └── tes_fase1.py           Test otomatis protokol (11/11 lulus)
└── android_app/               Proyek Android native (Kotlin)
    └── app/src/main/java/com/halodeck/macropad/
```
> APK debug dibuat sendiri: `android_app/gradlew assembleDebug` atau dari
> Android Studio. Folder `app/build/` tidak ikut di-commit.

## Cara Pakai

### 1. Firmware (sekali saja)
- Isi SSID & password Wi-Fi di `firmware/macro_pad_fase1c/macro_pad_fase1c.ino`
  (2 baris: `SSID_KAMU` dan `PASSWORD_KAMU`), lalu upload via Arduino IDE
  atau arduino-cli. Board: **LOLIN(WEMOS) D1 R2 & mini**.
- Lihat Serial Monitor @115200 — catat IP yang tampil (`OK:WIFI:TERSAMBUNG:<IP>`).

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
  - *Keluar*

Menjalankan manual (hanya bila perlu):
```
pythonw D:\DEV\OpenCode\WGMediaDECK\pc_bridge\connector_app.py
```
> `pythonw` (bukan `python`) agar tanpa jendela konsol. Aman dijalankan
> berkali-kali — aplikasi kedua otomatis keluar (anti double-instance).

Berkas:
- `connector_app.py` — aplikasi konektor (tray + auto-start)
- `versi.py` — nomor versi aplikasi PC (satu-satunya sumber)
- `updater.py` + `update_config.json` — pembaruan otomatis (bagian 4)
- `konektor.log` — riwayat log (heartbeat PONG sengaja tidak dicatat)

### 3. Aplikasi Android
- Instal `app-debug.apk` ke HP (pindahkan file, buka untuk instal —
  izin "sumber tidak dikenal" diperlukan sekali).
- Buka **HaloDeck** di HP (temuan otomatis lewat UDP — IP tidak perlu diketik),
  atau masukkan IP ESP8266 (dari Serial Monitor) port `8080` lalu **Hubungkan**.
- Buka aplikasi lain di PC (Photoshop, Premiere, Notepad) — tombol di HP
  otomatis berganti mengikuti aplikasi aktif.

### 4. Pembaruan Otomatis PC (GitHub Releases)

Konektor memeriksa rilis terbaru **setiap 24 jam** (sekali tiap hari), bisa
juga dicek manual dari menu tray. Bila ada versi lebih baru: unduh paket →
cocokkan checksum SHA-256 → cadangkan `.py` lama → timpa → **tutup &
buka lagi dirinya sendiri**.

**Konfigurasi** — `pc_bridge/update_config.json`:

```json
{
  "repo": "namapengguna/HaloDeck",
  "prefiks_aset": "halodeck-win",
  "cek_otomatis": true,
  "pasang_otomatis": false
}
```

| Kolom | Arti |
|---|---|
| `repo` | Repo GitHub tempat rilis diunggah — *wajib diisi* (mis. `user/HaloDeck`) |
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

**Menerbitkan rilis:**
1. Naikkan `VERSI` di `pc_bridge/versi.py` (mis. `1.0.0` → `1.1.0`)
2. Jalankan `python tools/buat_paket_rilis.py`
   → menghasilkan `dist/HaloDeck-Win-<versi>.zip` + `.sha256`
3. GitHub → **Releases** → *Draft a new release* → tag `v<versi>`
4. Unggah zip + `.sha256` sebagai asset, lalu terbitkan
5. Konektor yang berjalan mendeteksi & memasang sendiri

**Pengaman yang dipasang updater:**
- Paket **ditolak** bila checksum tidak cocok, zip tidak memuat `versi.py`,
  struktur tidak dikenal, atau versi paket **tidak lebih baru** (anti-downgrade)
- `update_config.json`, `konektor.log`, `konektor.lock` **tidak pernah**
  ditimpa update
- Sebelum menimpa, semua `.py` dicadangkan ke `pc_bridge/_cadangan/`
  (5 cadangan terakhir disimpan)

> Belum dikemas jadi installer — rencananya pakai **Inno Setup**; jalur
> pemasangan di `updater.py` akan disesuaikan (`/SILENT`) saat itu.

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
