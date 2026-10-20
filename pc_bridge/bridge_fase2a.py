# ============================================================
# HALODECK - FASE 2a (Python Bridge)
# Tugas : Deteksi active window + koneksi serial auto-reconnect
# Platform: Windows 10/11, Python 3.10
# Dependensi: pyserial (sudah terpasang). Lainnya pakai ctypes asli.
# Komentar dalam Bahasa Indonesia
# ============================================================

import ctypes
import ctypes.wintypes
import threading
import time
import serial
import serial.tools.list_ports

# ---------- KONFIGURASI ----------
PORT_TARGET     = "COM4"          # Port Wemos D1 Mini (kosongkan "" untuk auto-cari)
BAUD_RATE       = 115200
INTERVAL_POLL   = 0.5             # Detik antar pengecekan jendela aktif
INTERVAL_PING   = 5.0             # Detik antar heartbeat PING ke ESP8266

# ---------- PEMETA APLIKASI -> PROFIL ----------
# Kunci: nama executable (huruf kecil). Nilai: nama profil (dikirim sebagai PROF:<NILAI>)
PEMETA_PROFIL = {
    "photoshop.exe":    "PHOTOSHOP",
    "premiere.exe":     "PREMIERE",
    "afterfx.exe":      "AFTEREFFECTS",
    "illustrator.exe":  "ILLUSTRATOR",
    "code.exe":         "VSCODE",
    "notepad.exe":      "NOTEPAD",
    "chrome.exe":       "BROWSER",
    "firefox.exe":      "BROWSER",
    "msedge.exe":       "BROWSER",
    "explorer.exe":     "DEFAULT",
}
PROFIL_DEFAULT = "DEFAULT"


# ============================================================
# BAGIAN 1: DETEKTOR JENDELA AKTIF (API Win32 via ctypes)
# ============================================================
class DetektorJendela:
    """Mengambil judul & nama proses dari jendela yang sedang aktif (foreground)."""

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

    def ambil_jendela_aktif(self):
        """Mengembalikan (judul_jendela, nama_proses) atau (None, None)."""
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return None, None

        # --- Ambil judul jendela ---
        panjang = self.user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(panjang + 1)
        self.user32.GetWindowTextW(hwnd, buffer, panjang + 1)
        judul = buffer.value

        # --- Ambil nama proses pemilik jendela ---
        pid = ctypes.wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        # Buka proses untuk membaca nama executable-nya
        HAK_Akses = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
        proses = self.kernel32.OpenProcess(HAK_Akses, False, pid.value)
        if not proses:
            return judul, None

        buffer_nama = ctypes.create_unicode_buffer(260)
        ukuran = ctypes.wintypes.DWORD(260)
        berhasil = self.kernel32.QueryFullProcessImageNameW(
            proses, 0, buffer_nama, ctypes.byref(ukuran)
        )
        self.kernel32.CloseHandle(proses)

        if not berhasil:
            return judul, None

        # Ambil hanya nama file-nya (potong jalur penuh)
        nama_proses = buffer_nama.value.split("\\")[-1]
        return judul, nama_proses


# ============================================================
# BAGIAN 2: MANAJER KONEKSI SERIAL (auto-reconnect)
# ============================================================
class ManajerSerial:
    """Menjaga koneksi serial ke ESP8266 tetap hidup, dengan reconnect otomatis."""

    def __init__(self, port_target, baud):
        self.port_target = port_target
        self.baud = baud
        self.koneksi = None
        self.status_tersambung = False

    def cari_port(self):
        """Cari port Wemos/CH340 secara otomatis bila port_target kosong."""
        if self.port_target:
            return self.port_target
        for p in serial.tools.list_ports.comports():
            if "CH340" in p.description or "CP210" in p.description:
                return p.device
        return None

    def coba_sambung(self):
        """Coba buka koneksi serial. Berhasil -> True."""
        port = self.cari_port()
        if not port:
            return False
        try:
            self.koneksi = serial.Serial(port, self.baud, timeout=1)
            time.sleep(2)  # Tunggu ESP8266 reset setelah port dibuka
            self.koneksi.reset_input_buffer()
            self.status_tersambung = True
            print(f"[SERIAL] Tersambung ke {port} @ {self.baud} baud")
            return True
        except serial.SerialException:
            self.status_tersambung = False
            return False

    def pastikan_sambungan(self):
        """Cek koneksi; kalau putus, coba sambung ulang."""
        if self.koneksi and self.koneksi.is_open:
            return True
        self.status_tersambung = False
        print("[SERIAL] Koneksi putus, mencoba sambung ulang...")
        return self.coba_sambung()

    def kirim(self, perintah):
        """Kirim perintah string ke ESP8266 (ditambah newline)."""
        if not self.pastikan_sambungan():
            return False
        try:
            self.koneksi.write((perintah + "\n").encode("utf-8"))
            return True
        except serial.SerialException:
            self.status_tersambung = False
            return False

    def baca_balasan(self):
        """Baca satu baris balasan dari ESP8266 (atau None)."""
        if not self.status_tersambung:
            return None
        try:
            if self.koneksi.in_waiting:
                baris = self.koneksi.readline().decode("utf-8", errors="ignore").strip()
                return baris if baris else None
        except serial.SerialException:
            self.status_tersambung = False
        return None


# ============================================================
# BAGIAN 3: PROGRAM UTAMA (loop deteksi + kirim profil)
# ============================================================
def jalankan_bridge():
    print("=" * 55)
    print(" PYTHON BRIDGE - FASE 2a")
    print(" Deteksi active window -> kirim PROF ke ESP8266")
    print("=" * 55)

    detektor = DetektorJendela()
    serial_mgr = ManajerSerial(PORT_TARGET, BAUD_RATE)
    serial_mgr.coba_sambung()

    profil_sekarang = None          # Profil terakhir yang terkirim
    waktu_ping_terakhir = 0.0

    try:
        while True:
            waktu_sekarang = time.time()

            # --- Heartbeat PING berkala (cek ESP8266 masih hidup) ---
            if waktu_sekarang - waktu_ping_terakhir >= INTERVAL_PING:
                waktu_ping_terakhir = waktu_sekarang
                serial_mgr.kirim("PING")

            # --- Cek balasan dari ESP8266 (ACK/ERR/PONG) ---
            balasan = serial_mgr.baca_balasan()
            if balasan:
                print(f"  <- ESP8266: {balasan}")

            # --- Deteksi jendela aktif ---
            judul, nama_proses = detektor.ambil_jendela_aktif()

            # --- Petakan ke profil ---
            if nama_proses:
                profil_baru = PEMETA_PROFIL.get(nama_proses.lower(), PROFIL_DEFAULT)
            else:
                profil_baru = PROFIL_DEFAULT

            # --- Kirim hanya bila profil BERUBAH (hemat lalu lintas serial) ---
            if profil_baru != profil_sekarang:
                berhasil = serial_mgr.kirim(f"PROF:{profil_baru}")
                if berhasil:
                    print(f"  -> Profil berubah: {profil_sekarang} -> {profil_baru}"
                          f"   (dari: {nama_proses} | '{judul[:40]}')")
                    profil_sekarang = profil_baru

            time.sleep(INTERVAL_POLL)

    except KeyboardInterrupt:
        print("\n[BRIIDGE] Dihentikan oleh pengguna. Sampai jumpa!")
        if serial_mgr.koneksi:
            serial_mgr.koneksi.close()


if __name__ == "__main__":
    jalankan_bridge()
