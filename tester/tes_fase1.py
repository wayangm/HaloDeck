# ============================================================
# HALODECK - FASE 1d
# Tester otomatis ESP8266 via USB Serial (COM4)
# Tugas : Verifikasi semua protokol Fase 1 secara otomatis
# Komentar dalam Bahasa Indonesia
# ============================================================

import time
import serial  # Modul pyserial

# ---------- KONFIGURASI ----------
PORT_COM   = "COM4"
BAUD_RATE  = 115200
TIMEOUT    = 2  # detik

# ---------- KASUS UJI ----------
# Format: (perintah_kirim, jawaban_yang_diharapkan)
KASUS_UJI = [
    ("PING",           "PONG"),
    ("STAT",           "OK:SIAP:FASE2"),
    ("BTN:LOCK",       "ACK:BTN:LOCK"),
    ("BTN:mute",       "ACK:BTN:MUTE"),          # Huruf kecil -> otomatis kapital
    ("BTN:BROWSER",    "ACK:BTN:BROWSER"),
    ("BTN:TASKMGR",    "ACK:BTN:TASKMGR"),
    ("PROF:DEFAULT",   "ACK:PROF:DEFAULT"),
    ("PROF:PHOTOSHOP", "ACK:PROF:PHOTOSHOP"),
    ("PROF:PREMIERE",  "ACK:PROF:PREMIERE"),
    ("ASDF",           "ERR:FORMAT"),            # Format salah
    ("XYZ:123",        "ERR:PERINTAH_TIDAK_DIKENAL"),  # Perintah tak dikenal
]


def jalankan_tes():
    print("=" * 55)
    print(" TESTER OTOMATIS - HALODECK FASE 1")
    print(f" Port: {PORT_COM} @ {BAUD_RATE} baud")
    print("=" * 55)

    try:
        koneksi = serial.Serial(PORT_COM, BAUD_RATE, timeout=TIMEOUT)
    except serial.SerialException as galat:
        print(f"[GAGAL] Tidak bisa membuka {PORT_COM}: {galat}")
        print("Pastikan tidak ada aplikasi lain (mis. Serial Monitor) yang memegang port.")
        return

    time.sleep(2)  # Tunggu ESP8266 reset setelah port dibuka

    # --- Bersihkan boot message (banner + log koneksi Wi-Fi) ---
    # Firmware 1c mengeluarkan log Wi-Fi saat boot, tunggu sampai tenang.
    print("  Menunggu boot firmware selesai (drain buffer)...")
    waktu_mulai = time.time()
    while time.time() - waktu_mulai < 25:   # Maksimal 25 detik
        if koneksi.in_waiting:
            koneksi.read(koneksi.in_waiting)   # Buang semua data lama
            waktu_mulai = time.time()          # Reset timer bila masih ada data
        else:
            time.sleep(0.2)
    koneksi.reset_input_buffer()
    print("  Buffer bersih, memulai pengujian...\n")

    jumlah_lulus = 0
    jumlah_total = len(KASUS_UJI)

    def baca_balasan_yang_diharapkan(perintah, harapan):
        """Baca baris dari ESP8266 sampai menemukan yang diharapkan (atau timeout).
        Melewati baris sampah seperti titik boot Wi-Fi."""
        batas_waktu = time.time() + 3
        while time.time() < batas_waktu:
            baris = koneksi.readline().decode("utf-8", errors="ignore").strip()
            if not baris:
                continue
            if baris == harapan:
                return baris          # Tepat yang dicari
            if baris.startswith(("PONG", "ACK:", "ERR:", "OK:")):
                return baris          # Balasan valid lain (untuk laporan GAGAL)
            # Baris lain (mis. titik boot "..") -> abaikan, lanjut baca
        return "(tidak ada balasan)"

    for perintah, harapan in KASUS_UJI:
        # Kirim perintah + newline
        koneksi.write((perintah + "\n").encode("utf-8"))

        # Baca balasan (lewati noise boot)
        balasan = baca_balasan_yang_diharapkan(perintah, harapan)

        # Verifikasi
        if balasan == harapan:
            status = "LULUS"
            jumlah_lulus += 1
        else:
            status = "GAGAL"

        print(f"  [{status}]  kirim: {perintah:<18} | balas: {balasan:<28} | harap: {harapan}")

        time.sleep(0.1)  # Jeda kecil antar perintah

    koneksi.close()

    print("=" * 55)
    print(f" HASIL: {jumlah_lulus}/{jumlah_total} tes LULUS")
    if jumlah_lulus == jumlah_total:
        print(" STATUS: SEMUA PERINTAH BERFUNGSI NORMAL [OK]")
    else:
        print(" STATUS: ADA GANGGUAN, CEK KABEL/PORT [!]")
    print("=" * 55)


if __name__ == "__main__":
    jalankan_tes()
