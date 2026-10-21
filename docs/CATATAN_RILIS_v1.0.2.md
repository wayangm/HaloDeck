HaloDeck **v1.0.2** — konektor Windows kini punya jendela UI sungguhan.

## Berkas rilis

| Berkas | Fungsi |
|---|---|
| **`HaloDeck-Win-Setup-1.0.2.exe`** | Installer Windows (per-user, tanpa admin) |
| `HaloDeck-Win-1.0.2.zip` | Kode `.py` murni untuk instalasi tanpa installer |
| `HaloDeck-Android-1.0.2.apk` | Aplikasi HP (versi 1.0.2) |

Firmware ESP **tidak berubah** — tetap pakai berkas dari rilis
[v1.0.0](https://github.com/wayangm/HaloDeck/releases/tag/v1.0.0).

## Yang baru: jendela UI

Selama ini konektor hanya berupa ikon tray. Sekarang ada jendela yang bisa
dibuka dengan **klik ganda ikon tray** (atau menu *Buka Jendela*):

- **Kartu status** — koneksi ESP8266, profil aktif, jumlah aksi, port
- **Tombol makro** — klik langsung dieksekusi di PC: kunci PC, mute, browser,
  undo/redo, makro Photoshop (zoom, fit, layer, flatten) dan Premiere
  (cut, mark in/out, export frame). Berguna saat HP sedang tidak dipegang.
- **Pembaruan** — versi saat ini + tombol *Periksa* / *Pasang* (tanpa perlu
  membuka menu tray)
- **Pengaturan** — mulai otomatis bersama Windows, jalankan ulang koneksi
- **Log langsung** — isi `konektor.log` tampil & mengalir sendiri di jendela

Menutup jendela hanya menyembunyikannya ke tray — konektor tetap bekerja.
Benar-benar keluar lewat tombol *Keluar* atau menu tray.

Menjalankan langsung dengan jendela terbuka:

```powershell
pythonw app\connector_app.py --buka-ui
```

## Aplikasi Android: tombol "Atur Wi-Fi" dihapus

Pengaturan Wi-Fi dilakukan lewat **portal browser ESP**, bukan lewat aplikasi:

- Setelah kredensial tersimpan, ESP berjalan mode station saja — **tidak lagi
  memancarkan hotspot `HALODECK-SETUP`**, sehingga alur kirim SSID dari aplikasi
  tidak akan pernah menemukan hotspot (muncul sebagai tombol tak merespons).
- Aplikasi kini menampilkan arahan bila ESP masih mode setup:
  *sambung hotspot `HALODECK-SETUP`, lalu buka `http://192.168.4.1`*.
- Izin lokasi (`ACCESS_FINE/COARSE_LOCATION`) ikut dihapus dari manifest —
  aplikasi tak pernah lagi meminta izin tersebut (hanya dipakai pindai Wi-Fi).

## Catatan teknis

- UI memakai **tkinter** (bawaan Python) sehingga tidak ada dependensi baru.
  Karena Python portable bawaan installer tidak menyertakan Tcl/Tk, skrip
  build menyalin **Tcl/Tk 8.6 + paket `Lib\tkinter`** dari instalasi Python
  lengkap yang sudah ada di mesin build (mis. `C:\Python310`). Pembaruan ini
  juga menaikkan ukuran installer dari 12,7 MB menjadi 15,1 MB.
- Skrip build **tidak pernah lagi menjalankan pemasang Python** — hanya
  pencarian & penyalinan berkas lokal, tanpa unduhan pemasang dan tanpa
  instalasi senyap ke sistem (pelajaran dari insiden v1.0.2-awal yang
  merusak instalasi Python di mesin).
- Jendela berjalan di thread utama, tray berjalan `run_detached()`; perintah
  dari tray dikirim lewat antrean `queue` agar aman dari race condition.
- UI tetap opsional: bila tkinter gagal dimuat, aplikasi otomatis kembali ke
  mode tray murni seperti sebelumnya.

## Pembaruan otomatis

Konektor akan mendeteksi versi ini sendiri dalam 24 jam, atau bisa dicek
manual: klik kanan ikon tray → **Periksa Pembaruan** → **Pasang Pembaruan**
(bisa juga dari jendela UI).

Lisensi: [MIT](https://github.com/wayangm/HaloDeck/blob/master/LICENSE).
