# Catatan Rilis HaloDeck v1.1.1

Rilis pemeliharaan (**patch**) ini menghadirkan penyempurnaan pada antarmuka jendela konektor Windows, opsi mulai senyap di system tray, serta perbaikan otomatisasi pada installer.

## Berkas Rilis

| Berkas | Fungsi |
|---|---|
| **`HaloDeck-Win-Setup-1.1.1.exe`** | **Disarankan** — Installer Windows (per-user, tanpa admin) |
| `HaloDeck-Win-1.1.1.zip` | Paket kode Python murni tanpa instalasi |

> **Catatan Firmware & Android:**
> Firmware ESP8266 (`HaloDeck-ESP-1.1.0.bin`) dan aplikasi Android (`HaloDeck-Android-1.1.0.apk`) **tidak berubah** dan tetap menggunakan berkas dari rilis [v1.1.0](https://github.com/wayangm/HaloDeck/releases/tag/v1.1.0).

---

## Yang Baru & Perbaikan

### 1. Penyederhanaan Jendela UI Konektor
* **Menghapus Tombol Makro PC:** Bagian *Tombol Makro* di jendela PC telah dihapus karena fungsinya sudah sepenuhnya dipusatkan pada HP Android sebagai perangkat macro pad fisik/layar sentuh.
* **Ukuran Jendela Lebih Ringkas:** Layout disesuaikan menjadi lebih ramping dan proporsional (`680x500`), memberikan ruang log yang lebih lega dan rapi.

### 2. Opsi Sembunyi di Tray saat Mulai Otomatis
* Ditambahkan opsi checkbox di jendela UI (*Pembaruan & Pengaturan*):
  `[✓] Sembunyi di tray saat start otomatis`
  *(Otomatis aktif hanya jika "Mulai otomatis bersama Windows" dicentang).*
* Ditambahkan toggle menu di klik kanan ikon tray: *Sembunyi di Tray saat Mulai Otomatis*.
* Ketika Windows menyala, aplikasi akan berjalan senyap di background/tray tanpa menampilkan jendela visual bila opsi ini aktif. Saat pengguna membuka aplikasi secara manual via pintasan Desktop/Start Menu, jendela UI akan tetap terbuka otomatis seperti biasa.

### 3. Perbaikan Efek Hover / Sorot Tombol
* Memperbaiki masalah visual di mana efek hover pada tombol *Periksa Pembaruan* sempat berkedip/hilang setiap 400 milidetik.
* Menambahkan *state caching* pada siklus penyegaran UI sehingga komponen hanya diperbarui saat nilainya benar-benar berubah, menjaga stabilitas animasi visual Windows (`ttk`).

### 4. Perbaikan Pemasangan & Pembaruan pada Installer
* Installer kini secara otomatis mendeteksi dan mematikan proses HaloDeck yang sedang aktif di latar belakang sebelum memperbarui berkas.
* Menghilangkan kendala dialog *Windows Restart Manager* (*"The following applications are using files..."*) yang sebelumnya gagal menutup aplikasi background.

---

## Verifikasi Integritas (SHA-256)

Setiap aset rilis dilengkapi berkas `.sha256` untuk verifikasi keamanan dan integritas berkas.
