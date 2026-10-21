# ============================================================
# HALODECK - FASE 2a (Python Bridge)
# Tugas : Deteksi active window + koneksi serial auto-reconnect
# Platform: Windows 10/11, Python 3.10
# Dependensi: pyserial (sudah terpasang). Lainnya pakai ctypes asli.
# Komentar dalam Bahasa Indonesia
# ============================================================

import ctypes
import ctypes.wintypes
import select
import socket
import threading
import time
import serial
import serial.tools.list_ports

# ---------- KONFIGURASI ----------
PORT_TARGET     = "COM4"          # Port Wemos D1 Mini (kosongkan "" untuk auto-cari)
BAUD_RATE       = 115200
INTERVAL_POLL   = 0.5             # Detik antar pengecekan jendela aktif
INTERVAL_PING   = 5.0             # Detik antar heartbeat PING ke ESP8266

# ---------- KONFIGURASI JALUR JARINGAN (Wi-Fi, tanpa USB) ----------
# PC memakai port TERPISAH dari HP (8080). Firmware menyimpan hanya SATU
# client per port; kalau PC dan HP berbagi satu port, mereka saling
# mengusir dan terjadi loop konek-putus.
PORT_TCP_PC         = 8082        # Port TCP khusus jalur PC
PORT_UDP            = 8081        # Port UDP discovery (dipakai HP & PC)
TIMEOUT_DISCOVERY   = 1.5         # Detik menunggu balasan paket DISCOVER
KIRIM_TIMEOUT       = 2.0         # Detik menunggu socket siap menulis
TIMEOUT_SAMBUNG     = 3.0         # Detik timeout connect TCP

# Prefix balasan discovery. MACROPAD = firmware pra-rebrand,
# HALODECK = firmware v1.0.2+. Keduanya diterima agar ESP lama tetap ditemukan.
PREFIX_DISCOVERY = ("MACROPAD:", "HALODECK:")

# ---------- HOOK PENCATAT (diisi connector_app agar masuk log) ----------
# bridge_fase2a harus tetap bisa berdiri sendiri (dijalankan langsung),
# jadi default-nya cuma print. connector_app menggantinya dengan catat().
PENCATAT = lambda pesan: print(pesan)      # noqa: E731


def catat_jalur(pesan):
    """Catat peristiwa jalur koneksi (dipakai ManajerOtomatis)."""
    try:
        PENCATAT(pesan)
    except Exception:
        pass

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
# BAGIAN 2b: MANAJER KONEKSI JARINGAN (Wi-Fi TCP, tanpa USB)
# ============================================================
class ManajerTcp:
    """Menjaga koneksi TCP ke ESP8266 lewat Wi-Fi, dengan auto-reconnect.

    Dipakai saat kabel USB tidak terpasang. Port TERPISAH dari jalur HP
    (PC: 8082, HP: 8080) supaya keduanya tidak saling mengusir client.
    """

    def __init__(self, host_target="", port=PORT_TCP_PC):
        self.host_target = host_target    # IP statis; kosongkan untuk discovery
        self.port = port
        self.koneksi = None
        self.status_tersambung = False
        self.host_aktif = None            # IP yang benar-benar terpakai
        self._buffer = bytearray()        # Sisa baca yang belum jadi baris utuh

    # ---------- TEMUAN IP LEWAT UDP BROADCAST ----------
    def temukan_host(self):
        """Kirim DISCOVER (UDP broadcast) -> kembalikan IP ESP mode STA, atau None.

        Balasan firmware: "MACROPAD:STA:<IP>" atau "HALODECK:STA:<IP>".
        Prefix AP (mode setup) diabaikan — PC tidak bisa menolong saat ESP
        masih memancarkan hotspot; itu urusan setup via HP.
        """
        hasil = None
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(TIMEOUT_DISCOVERY)
                # Port sumber diikat agar balasan ESP pasti kembali ke kita
                sock.bind(("", 0))
                pesan = b"DISCOVER\n"
                tujuan = ("255.255.255.255", PORT_UDP)
                # Kirim 3 kali: broadcast UDP gampang hilang di beberapa router
                for _ in range(3):
                    try:
                        sock.sendto(pesan, tujuan)
                    except OSError:
                        break
                    if self._tunggu_balasan(sock):
                        hasil = self._host_temuan
                        break
                    time.sleep(0.15)
        except OSError:
            return None
        return hasil

    _host_temuan = None

    def _tunggu_balasan(self, sock):
        """True bila menemukan balasan discovery yang valid (isi _host_temuan)."""
        batas = time.time() + TIMEOUT_DISCOVERY
        while time.time() < batas:
            try:
                data, alamat = sock.recvfrom(256)
            except socket.timeout:
                return False
            except OSError:
                return False
            isi = data.decode("utf-8", errors="ignore").strip()
            if not isi.startswith(PREFIX_DISCOVERY):
                continue
            bagian = isi.split(":")
            # Format: <PREFIX>:<MODE>:<IP>. Pakai alamat pengirim (lebih
            # andal daripada IP yang tertulis di isi paket).
            if len(bagian) == 3 and bagian[1] == "STA":
                self._host_temuan = alamat[0]
                return True
        return False

    # ---------- KONEKSI TCP ----------
    def coba_sambung(self):
        """Coba sambung via Wi-Fi. Bila host_target kosong, lakukan discovery."""
        host = self.host_target or self.temukan_host()
        if not host:
            self.status_tersambung = False
            return False
        try:
            sock = socket.create_connection((host, self.port), timeout=TIMEOUT_SAMBUNG)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            # Non-blocking: baca_balasan() harus bisa dipolling tanpa menahan
            # loop utama. Pengiriman ditangani _kirim_penuh() dengan select.
            sock.setblocking(False)
            self.koneksi = sock
            self.host_aktif = host
            self.status_tersambung = True
            self._buffer.clear()
            print(f"[JARINGAN] Tersambung ke {host}:{self.port}")
            return True
        except OSError as galat:
            self.status_tersambung = False
            print(f"[JARINGAN] Gagal sambung ke {host}:{self.port} ({galat})")
            return False

    def _putus(self):
        """Tutup socket dan tandai terputus (dipanggil dari mana pun)."""
        self.status_tersambung = False
        if self.koneksi:
            try:
                self.koneksi.close()
            except OSError:
                pass
        self.koneksi = None

    def pastikan_sambungan(self):
        """Cek koneksi masih hidup; kalau putus, coba sambung ulang."""
        if self.koneksi is not None and self.status_tersambung:
            return True
        self._putus()
        print("[JARINGAN] Koneksi putus, mencoba sambung ulang...")
        return self.coba_sambung()

    # ---------- KIRIM ----------
    def _kirim_penuh(self, data):
        """Kirim seluruh byte pada socket non-blocking, tunggu dengan select."""
        tersisa = memoryview(data)
        while tersisa:
            _, siap, _ = select.select([], [self.koneksi], [], KIRIM_TIMEOUT)
            if not siap:
                return False
            try:
                terkirim = self.koneksi.send(tersisa)
            except BlockingIOError:
                continue
            except OSError:
                return False
            if terkirim == 0:
                return False
            tersisa = tersisa[terkirim:]
        return True

    def kirim(self, perintah):
        """Kirim perintah string ke ESP8266 (ditambah newline)."""
        if not self.pastikan_sambungan():
            return False
        if not self._kirim_penuh((perintah + "\n").encode("utf-8")):
            self._putus()
            return False
        return True

    # ---------- BACA ----------
    def baca_balasan(self):
        """Baca satu baris balasan dari ESP8266 (atau None).

        Berbeda dari serial: recv() bisa mengembalikan potongan baris yang
        terpotong atau beberapa baris sekaligus. Semua masuk ke _buffer,
        lalu dipetik per baris. Maka method ini aman dipanggil berulang
        dalam satu siklus poll.
        """
        if not self.status_tersambung or self.koneksi is None:
            return None

        # 1. Isi buffer selama data masih mengalir
        while True:
            siap, _, _ = select.select([self.koneksi], [], [], 0)
            if not siap:
                break
            try:
                potongan = self.koneksi.recv(4096)
            except BlockingIOError:
                break
            except OSError:
                self._putus()
                return None
            if not potongan:              # Peer menutup koneksi
                self._putus()
                return None
            self._buffer.extend(potongan)
            if len(self._buffer) > 8192:  # Pengaman dari banjir data
                self._buffer.clear()

        # 2. Petik satu baris dari buffer
        if b"\n" not in self._buffer:
            return None
        indeks = self._buffer.index(b"\n")
        baris = bytes(self._buffer[:indeks])
        del self._buffer[:indeks + 1]
        teks = baris.decode("utf-8", errors="ignore").strip()
        return teks or None


# ============================================================
# BAGIAN 2c: MANAJER OTOMATIS (pilih jalur sendiri)
# ============================================================
class ManajerOtomatis:
    """Satu API untuk dua jalur: USB/serial dulu, lalu jaringan (Wi-Fi).

    Menyamarkan detail jalur agar pemakai (connector_app) tidak perlu tahu
    ESP tersambung lewat kabel atau Wi-Fi. Kebijakan pemilihan:
      1. Serial diprioritaskan — paling andal dan tanpa risiko broadcast.
      2. Bila serial gagal (kabel dicabut), otomatis jatuh ke jaringan.
      3. Saat jalur aktif putus, coba ulang jalur yang sama dulu, baru
         jalur lain — agar tidak berpindah-pindah saat koneksi goyang.
    """

    def __init__(self, port_target=PORT_TARGET, baud=BAUD_RATE,
                 host_target="", port_pc=PORT_TCP_PC):
        self.serial_mgr = ManajerSerial(port_target, baud)
        self.jaringan_mgr = ManajerTcp(host_target, port_pc)
        self.jalur = None                  # "serial" | "jaringan" | None

    # --- Atribut serupa ManajerSerial, agar connector_app tetap polos ---
    @property
    def koneksi(self):
        """Mengarah ke koneksi milik jalur yang sedang aktif."""
        if self.jalur == "jaringan":
            return self.jaringan_mgr.koneksi
        return self.serial_mgr.koneksi

    @property
    def status_tersambung(self):
        if self.jalur == "jaringan":
            return self.jaringan_mgr.status_tersambung
        if self.jalur == "serial":
            return self.serial_mgr.status_tersambung
        return False

    @property
    def jalur_terpakai(self):
        """Keterangan singkat jalur untuk ditampilkan di UI/log."""
        if self.jalur == "jaringan" and self.jaringan_mgr.host_aktif:
            return f"Wi-Fi {self.jaringan_mgr.host_aktif}:{PORT_TCP_PC}"
        if self.jalur == "serial":
            return f"USB {self.serial_mgr.port_target}"
        return "belum tersambung"

    def coba_sambung(self):
        """Coba sambung: serial dulu, baru jaringan. Berhasil -> True."""
        if self.jalur == "serial" and self.serial_mgr.coba_sambung():
            return True
        if self.jaringan_mgr.coba_sambung():
            self.jalur = "jaringan"
            return True
        # Coba serial sekali lagi (kabel mungkin baru saja dipasang)
        if self.jalur != "serial" and self.serial_mgr.coba_sambung():
            self.jalur = "serial"
            return True
        self.jalur = None
        return False

    def pastikan_sambungan(self):
        """Cek jalur aktif; kalau mati, coba jalur lain."""
        if self.jalur == "jaringan":
            if self.jaringan_mgr.pastikan_sambungan():
                return True
            return self._pindah_jalur_ke_serial()
        if self.jalur == "serial":
            if self.serial_mgr.pastikan_sambungan():
                return True
            return self._pindah_jalur_ke_jaringan()
        return self.coba_sambung()

    def _pindah_jalur_ke_serial(self):
        self.jaringan_mgr._putus()
        if self.serial_mgr.coba_sambung():
            self.jalur = "serial"
            catat_jalur(f"[JALUR] Pindah ke USB ({self.jalur_terpakai})")
            return True
        self.jalur = None
        return False

    def _pindah_jalur_ke_jaringan(self):
        if self.serial_mgr.koneksi:
            try:
                self.serial_mgr.koneksi.close()
            except Exception:
                pass
        if self.jaringan_mgr.coba_sambung():
            self.jalur = "jaringan"
            catat_jalur(f"[JALUR] Pindah ke Wi-Fi ({self.jalur_terpakai})")
            return True
        self.jalur = None
        return False

    def kirim(self, perintah):
        """Kirim perintah ke ESP8266 lewat jalur yang sedang aktif."""
        if not self.pastikan_sambungan():
            return False
        if self.jalur == "jaringan":
            return self.jaringan_mgr.kirim(perintah)
        return self.serial_mgr.kirim(perintah)

    def putus(self):
        """Tutup koneksi aktif tanpa mencoba sambung ulang."""
        try:
            self.jaringan_mgr._putus()
        except Exception:
            pass
        try:
            if self.serial_mgr.koneksi:
                self.serial_mgr.koneksi.close()
        except Exception:
            pass
        self.serial_mgr.status_tersambung = False
        self.jalur = None

    def baca_balasan(self):
        """Baca satu baris balasan dari jalur yang sedang aktif."""
        if not self.status_tersambung:
            return None
        if self.jalur == "jaringan":
            return self.jaringan_mgr.baca_balasan()
        return self.serial_mgr.baca_balasan()


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
