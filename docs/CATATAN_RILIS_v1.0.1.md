HaloDeck **v1.0.1** — pembaruan kecil untuk konektor Windows.

## Berkas rilis

| Berkas | Fungsi |
|---|---|
| **`HaloDeck-Win-Setup-1.0.1.exe`** | Installer Windows (per-user, tanpa admin) |
| `HaloDeck-Win-1.0.1.zip` | Kode `.py` murni untuk instalasi tanpa installer |

Firmware ESP & APK **tidak berubah** — tetap pakai berkas dari rilis
[v1.0.0](https://github.com/wayangm/HaloDeck/releases/tag/v1.0.0).

## Perubahan

- Menu tray baru: **Unduh Berkas Lain (Firmware & APK)** — membuka halaman
  rilis di peramban, jadi firmware ESP & APK bisa diambil langsung dari tray
  tanpa perlu menghafal alamat repo
- Tautan mengikuti `repo` di `update_config.json`, jadi tetap benar walau
  repo dipindah
- Perbaikan: instalasi baru kini ikut memasang `update_config.json`, dan
  updater punya nilai bawaan `repo: wayangm/HaloDeck` — konektor langsung
  bisa memeriksa pembaruan sejak pertama kali menyala

> **Sudah memasang v1.0.0?** Jalankan `HaloDeck-Win-Setup-1.0.1.exe` sekali
> untuk menimpa instalasi (folder & menu Start tetap sama). Sejak v1.0.1
> pembaruan berikutnya terpasang otomatis lewat tray.

## Pembaruan otomatis

Konektor akan mendeteksi versi ini sendiri dalam 24 jam, atau bisa dicek
manual: klik kanan ikon tray → **Periksa Pembaruan** → **Pasang Pembaruan**.
Aplikasi menutup diri, memasang, lalu membuka kembali otomatis.

Lisensi: [MIT](https://github.com/wayangm/HaloDeck/blob/master/LICENSE).
