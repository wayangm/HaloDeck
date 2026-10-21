# ============================================================
# HALODECK - FASE 2b (Bridge Terintegrasi)
# Tugas : Deteksi active window + eksekusi aksi BTN dari serial
# Alur  : HP/ESP8266 kirim "BTN:<AKSI>" -> Bridge eksekusi di PC
# Platform: Windows 10/11, Python 3.10
# Komentar dalam Bahasa Indonesia
# ============================================================

import sys
import os
import time

# Izinkan impor modul aksi dari folder yang sama
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge_fase2a import (DetektorJendela, ManajerOtomatis, PEMETA_PROFIL,
                           PROFIL_DEFAULT)
from aksi import eksekusi_perintah

# ---------- KONFIGURASI ----------
PORT_TARGET   = "COM4"
BAUD_RATE     = 115200
INTERVAL_POLL = 0.5
INTERVAL_PING = 5.0
# IP ESP statis; kosongkan "" untuk dicari otomatis lewat UDP discovery
HOST_TARGET   = ""


def jalankan_bridge_penuh():
    print("=" * 55)
    print(" PYTHON BRIDGE - FASE 2b (TERINTEGRASI)")
    print(" 1. Deteksi active window -> kirim PROF")
    print(" 2. Terima BTN:<AKSI> dari jalur USB/Wi-Fi -> eksekusi aksi PC")
    print("=" * 55)

    detektor = DetektorJendela()
    # ManajerOtomatis: USB dulu, lalu jatuh ke Wi-Fi (TCP 8082) bila
    # kabel tidak terpasang — PC tetap bisa dipakai tanpa USB.
    serial_mgr = ManajerOtomatis(PORT_TARGET, BAUD_RATE, host_target=HOST_TARGET)
    serial_mgr.coba_sambung()

    profil_sekarang = None
    waktu_ping_terakhir = 0.0

    try:
        while True:
            waktu = time.time()

            # --- Heartbeat PING berkala ---
            if waktu - waktu_ping_terakhir >= INTERVAL_PING:
                waktu_ping_terakhir = waktu
                serial_mgr.kirim("PING")

            # --- Baca semua balasan/perintah masuk dari ESP8266 ---
            while True:
                balasan = serial_mgr.baca_balasan()
                if balasan is None:
                    break

                if balasan.startswith("BTN:"):
                    # PERINTAH AKSI dari jalur ESP8266/HP -> eksekusi!
                    print(f"  <- Perintah aksi diterima: {balasan}")
                    eksekusi_perintah(balasan)
                    # Balas ACK ke ESP8266 sebagai konfirmasi
                    serial_mgr.kirim(f"ACK:{balasan}")
                else:
                    # Balasan biasa (PONG, ACK:PROF, dst.)
                    print(f"  <- ESP8266: {balasan}")

            # --- Deteksi jendela aktif -> kirim profil bila berubah ---
            judul, nama_proses = detektor.ambil_jendela_aktif()
            if nama_proses:
                profil_baru = PEMETA_PROFIL.get(nama_proses.lower(), PROFIL_DEFAULT)
            else:
                profil_baru = PROFIL_DEFAULT

            if profil_baru != profil_sekarang:
                if serial_mgr.kirim(f"PROF:{profil_baru}"):
                    print(f"  -> Profil: {profil_sekarang} -> {profil_baru}"
                          f"   (aplikasi: {nama_proses})")
                    profil_sekarang = profil_baru

            time.sleep(INTERVAL_POLL)

    except KeyboardInterrupt:
        print("\n[BRIIDGE] Dihentikan oleh pengguna.")
        serial_mgr.putus()


if __name__ == "__main__":
    jalankan_bridge_penuh()
