Rilis perdana **HaloDeck** — makro pad hybrid (Android → ESP8266 → PC Windows)
dengan context-switching otomatis. Kode 100% terbuka (MIT).

## Berkas rilis

| Berkas | Fungsi |
|---|---|
| **`HaloDeck-Win-Setup-1.0.0.exe`** | **Mulai di sini.** Installer Windows (per-user, tanpa admin): Python portable + kode `.py` asli HaloDeck yang bisa dibaca & dimodifikasi |
| `HaloDeck-Win-1.0.0.zip` | Kode `.py` murni untuk yang ingin menjalankan tanpa installer |
| `HaloDeck-Android-1.0.0.apk` | Aplikasi HP (temuan otomatis IP ESP lewat UDP) |
| `HaloDeck-ESP-1.0.0.bin` | Firmware ESP8266 **disarankan** (fase2): portal setup `HALODECK-SETUP`, SSID tidak perlu diedit di kode |
| `HaloDeck-ESP-1.0.0-fase1c.bin` | Firmware varian stabil (fase1c): Serial + Wi-Fi TCP |

Setiap berkas disertai berkas `.sha256` — cocokkan sebelum dipakai:

```powershell
Get-FileHash .\HaloDeck-Win-Setup-1.0.0.exe -Algorithm SHA256
```

## Pemasangan

1. **PC** — jalankan `HaloDeck-Win-Setup-1.0.0.exe` → Next sampai selesai.
   Konektor langsung menyala sebagai tray icon (hijau = ESP tersambung) dan
   otomatis terdaftar di Startup Windows.
2. **ESP8266** — unduh `HaloDeck-ESP-1.0.0.bin`, lalu:
   ```powershell
   pip install esptool
   esptool.py --port COM4 erase_flash
   esptool.py --port COM4 --baud 460800 write_flash 0x0 HaloDeck-ESP-1.0.0.bin
   ```
   Saat pertama kali, papan membuat hotspot **`HALODECK-SETUP`** → buka
   `http://192.168.4.1` dari HP untuk memasukkan SSID & password Wi-Fi.
3. **HP** — pasang `HaloDeck-Android-1.0.0.apk`, buka **HaloDeck**, tekan
   **Hubungkan** (IP ESP ditemukan otomatis). Siap dipakai.

> **Catatan migrasi:** ESP harus di-flash ulang karena firmware kini memakai
> nama hotspot & protokol `HALODECK-*`. Aplikasi Android lama
> (`com.wgmedia.macropad`) harus di-uninstall dulu sebelum memasang yang baru.

## Pembaruan otomatis (Windows)

Konektor memeriksa rilis terbaru ini setiap 24 jam, atau manual lewat
menu tray → *Periksa Pembaruan*. Paket diverifikasi SHA-256, file `.py` lama
dicadangkan, lalu aplikasi menutup & membuka dirinya sendiri.

## Perubahan

- Rebrand total **WGMediaDECK → HaloDeck** (PC, Android, firmware)
- Pembaruan otomatis via GitHub Releases dengan verifikasi checksum & cadangan
- Installer Inno Setup per-user tanpa admin
- Terbit firmware & APK langsung di repo yang sama (pemisah: awalan asset
  `HaloDeck-Win-*`, `HaloDeck-ESP-*`, `HaloDeck-Android-*`)

## Kebutuhan

- Windows 10/11 64-bit · ESP8266 (Wemos D1 Mini) · Android 8+
- Board ESP8266: **LOLIN(WEMOS) D1 R2 & mini**, flash 4 MB

Lisensi: [MIT](https://github.com/wayangm/HaloDeck/blob/master/LICENSE).
