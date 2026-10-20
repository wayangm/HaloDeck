# ============================================================
# HALODECK - Konektor Windows (Aplikasi Tray)
# File: connector_app.py
# Tugas : Berjalan otomatis bersama Windows, tanpa konsol.
#         - Tray icon di system tray (hijau = tersambung)
#         - Bridge PC: deteksi active window + eksekusi aksi BTN
#         - Reconnect otomatis bila ESP8266/COM hilang
#         - Bisa dijalankan ulang / dimatikan lewat menu tray
# Jalankan: pythonw connector_app.py   (pythonw = tanpa jendela konsol)
# Komentar dalam Bahasa Indonesia
# ============================================================

import ctypes
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

# --- Pastikan folder pc_bridge ada di path impor ---
FOLDER_INI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, FOLDER_INI)

from bridge_fase2a import DetektorJendela, ManajerSerial, PEMETA_PROFIL, PROFIL_DEFAULT
from aksi import eksekusi_perintah
from versi import VERSI
import updater

import pystray
from PIL import Image, ImageDraw

# ---------- KONFIGURASI ----------
PORT_TARGET   = "COM4"
BAUD_RATE     = 115200
INTERVAL_POLL = 0.5
INTERVAL_PING = 5.0
BERKAS_LOG    = os.path.join(FOLDER_INI, "konektor.log")
BERKAS_KUNCI  = os.path.join(FOLDER_INI, "konektor.lock")   # Anti 2 instance
NAMA_RUN      = "HaloDeck Konektor"                         # Nama di startup Windows
NAMA_RUN_LAMA = "WGMediaDECK Konektor"                      # Nama lama (sebelum rebrand)

# ---------- STATUS BERSAMA (dibaca thread tray & thread bridge) ----------
status_lock = threading.Lock()
state = {
    "tersambung": False,
    "profil": "-",
    "pesan": "Memulai...",
    "jumlah_aksi": 0,
}


# ============================================================
# PENULIS LOG (beri stempel waktu)
# ============================================================
def catat(pesan):
    baris = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {pesan}\n"
    try:
        with open(BERKAS_LOG, "a", encoding="utf-8") as f:
            f.write(baris)
    except Exception:
        pass
    # Saat dijalankan pythonw (tanpa konsol) sys.stdout bernilai None,
    # maka print() akan membuat crash -> periksa dulu.
    try:
        if sys.stdout is not None:
            print(baris, end="", flush=True)
    except Exception:
        pass


# ============================================================
# SINGLETON: cegah aplikasi berjalan dua kali
# ============================================================
def kunci_instance():
    """Kembalikan handle berkas kunci, atau None bila sudah berjalan.

    Dicoba berulang (±5 detik) supaya proses baru hasil 'jalankan ulang
    otomatis' setelah pembaruan tidak langsung keluar hanya karena kunci
    dari proses lama belum sempat dilepas.
    """
    for _ in range(10):
        f = None
        try:
            f = open(BERKAS_KUNCI, "w")
            # Kunci eksklusif: gagal = ada instance lain yang sedang jalan
            msvcrt = __import__("msvcrt")
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            f.write(str(os.getpid()))
            f.flush()
            return f
        except Exception:
            if f is not None:
                try:
                    f.close()
                except Exception:
                    pass
            time.sleep(0.5)
    return None


# ============================================================
# AUTO-START BERSAMA WINDOWS (Registry Run - HKCU)
# ============================================================
HKCU_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"


def auto_start_aktif():
    try:
        import winreg
        kunci = winreg.OpenKey(winreg.HKEY_CURRENT_USER, HKCU_RUN, 0,
                               winreg.KEY_READ)
        try:
            winreg.QueryValueEx(kunci, NAMA_RUN)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(kunci)
    except Exception:
        return False


def set_auto_start(aktif):
    try:
        import winreg
        if aktif:
            pythonw = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(pythonw):
                pythonw = sys.executable
            nilai = f'"{pythonw}" "{os.path.abspath(__file__)}"'
            kunci = winreg.CreateKey(winreg.HKEY_CURRENT_USER, HKCU_RUN)
            winreg.SetValueEx(kunci, NAMA_RUN, 0, winreg.REG_SZ, nilai)
            winreg.CloseKey(kunci)
            catat(f"Auto-start Windows: AKTIF -> {nilai}")
        else:
            try:
                kunci = winreg.OpenKey(winreg.HKEY_CURRENT_USER, HKCU_RUN, 0,
                                       winreg.KEY_SET_VALUE)
                winreg.DeleteValue(kunci, NAMA_RUN)
                winreg.CloseKey(kunci)
            except FileNotFoundError:
                pass
            catat("Auto-start Windows: NONAKTIF")
        return True
    except Exception as galat:
        catat(f"Gagal atur auto-start: {galat}")
        return False


def migrasi_nama_startup():
    """Pindahkan entri auto-start dari nama LAMA (WGMediaDECK) ke HaloDeck.

    Aplikasi versi lama terdaftar di Registry dgn nama "WGMediaDECK Konektor".
    Bila itu masih ada, salin nilainya ke nama baru lalu hapus yang lama,
    supaya pengguna TIDAK kehilangan pengaturan auto-start saat pembaruan.
    """
    try:
        import winreg
        kunci = winreg.OpenKey(winreg.HKEY_CURRENT_USER, HKCU_RUN, 0,
                               winreg.KEY_READ | winreg.KEY_SET_VALUE)
    except OSError:
        return
    try:
        try:
            nilai_lama, _ = winreg.QueryValueEx(kunci, NAMA_RUN_LAMA)
        except FileNotFoundError:
            return                      # Tidak ada entri lama -> tidak perlu apa-apa
        sudah_ada = True
        try:
            winreg.QueryValueEx(kunci, NAMA_RUN)
        except FileNotFoundError:
            sudah_ada = False
        if not sudah_ada:
            winreg.SetValueEx(kunci, NAMA_RUN, 0, winreg.REG_SZ, nilai_lama)
        winreg.DeleteValue(kunci, NAMA_RUN_LAMA)
        catat(f"Auto-start Windows: entri '{NAMA_RUN_LAMA}' -> '{NAMA_RUN}'")
    except Exception as galat:
        catat(f"Galat migrasi auto-start: {galat}")
    finally:
        winreg.CloseKey(kunci)


# ============================================================
# IKON TRAY (digambar dengan Pillow, tanpa file gambar)
# ============================================================
def buat_ikon(hijau=True):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    latar = (30, 30, 46, 255)
    d.rounded_rectangle([2, 2, 62, 62], radius=14, fill=latar)
    warna = [(79, 195, 247), (102, 187, 106), (255, 183, 77), (239, 83, 80)]
    kotak = [(12, 12, 28, 28), (36, 12, 52, 28), (12, 36, 28, 52), (36, 36, 52, 52)]
    for w, k in zip(warna, kotak):
        d.rectangle(k, fill=w)
    if hijau:   # Titik status hijau di pojok kanan bawah
        d.ellipse([44, 44, 60, 60], fill=(102, 187, 106), outline=(30, 30, 46), width=3)
    else:       # Titik merah = belum tersambung
        d.ellipse([44, 44, 60, 60], fill=(239, 83, 80), outline=(30, 30, 46), width=3)
    return img


# ============================================================
# LOOP BRIDGE (berjalan di thread terpisah)
# ============================================================
class KonektorBridge:
    def __init__(self):
        self.detektor = DetektorJendela()
        self.serial_mgr = ManajerSerial(PORT_TARGET, BAUD_RATE)
        self.berhenti = threading.Event()
        self.thread = None
        self.profil_terakhir = None

    def mulai(self):
        if self.thread and self.thread.is_alive():
            return
        self.berhenti.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True,
                                       name="BridgeLoop")
        self.thread.start()
        catat("Loop bridge dimulai.")

    def hentikan(self):
        self.berhenti.set()
        try:
            if self.serial_mgr.koneksi:
                self.serial_mgr.koneksi.close()
        except Exception:
            pass
        state["tersambung"] = False
        catat("Loop bridge dihentikan.")

    def _loop(self):
        waktu_ping = 0.0
        while not self.berhenti.is_set():
            try:
                # --- Heartbeat PING berkala ---
                if time.time() - waktu_ping >= INTERVAL_PING:
                    waktu_ping = time.time()
                    self.serial_mgr.kirim("PING")

                status_baru = self.serial_mgr.status_tersambung
                if status_baru != state["tersambung"]:
                    state["tersambung"] = status_baru
                    catat("ESP8266 TERSAMBUNG." if status_baru
                          else "ESP8266 TERPUTUS — mencoba ulang...")

                # --- Baca semua balasan/perintah masuk ---
                while True:
                    balasan = self.serial_mgr.baca_balasan()
                    if balasan is None:
                        break
                    self._proses_balasan(balasan)

                # --- Deteksi jendela aktif -> kirim profil bila berubah ---
                if self.serial_mgr.status_tersambung:
                    _, nama_proses = self.detektor.ambil_jendela_aktif()
                    profil = (PEMETA_PROFIL.get(nama_proses.lower(), PROFIL_DEFAULT)
                              if nama_proses else PROFIL_DEFAULT)
                    if profil != self.profil_terakhir:
                        if self.serial_mgr.kirim(f"PROF:{profil}"):
                            catat(f"Profil -> {profil}  (aplikasi: {nama_proses})")
                            self.profil_terakhir = profil
                            state["profil"] = profil

            except Exception as galat:
                catat(f"Galat loop bridge: {galat}")
                time.sleep(1)

            self.berhenti.wait(INTERVAL_POLL)

    def _proses_balasan(self, balasan):
        if balasan.startswith("BTN:"):
            catat(f"Perintah aksi: {balasan}")
            sukses = eksekusi_perintah(balasan)
            with status_lock:
                if sukses:
                    state["jumlah_aksi"] += 1
            self.serial_mgr.kirim(f"ACK:{balasan}")
        elif balasan == "PONG":
            pass   # Heartbeat rutin -> JANGAN dicatat (hemat log)
        elif balasan.startswith(("ACK:", "OK:", "ERR:")):
            catat(f"ESP: {balasan}")
        else:
            # Noise boot (mis. titik log Wi-Fi) -> abaikan
            pass


# ============================================================
# APLIKASI TRAY
# ============================================================
class KonektorTray:
    def __init__(self):
        self.bridge = KonektorBridge()
        self.lock_instance = kunci_instance()
        self.tray = None
        # Pengelola pembaruan dari GitHub Releases (lihat updater.py)
        self.updater = updater.PengelolaUpdate(
            pencatat=catat,
            on_selesai=self._setelah_pasang,
        )

    def jalankan(self):
        if self.lock_instance is None:
            # Sudah berjalan -> keluar diam-diam
            sys.exit(0)

        catat("=== KONEKTOR HALODECK DIMULAIKAN ===")
        catat(f"Versi aplikasi: {VERSI}")
        catat(f"Port: {PORT_TARGET} @ {BAUD_RATE}")
        migrasi_nama_startup()
        self.bridge.mulai()
        self.updater.mulai()

        menu = pystray.Menu(
            pystray.MenuItem(self._teks_status, None, enabled=False),
            pystray.MenuItem(self._teks_profil, None, enabled=False),
            pystray.MenuItem(self._teks_aksi, None, enabled=False),
            pystray.MenuItem(None, None, enabled=False),   # Pemisah
            pystray.MenuItem("Jalankan Ulang Koneksi", self._ulang,
                             default=True),
            pystray.MenuItem("Mulai Otomatis Bersama Windows",
                             self._toggle_autostart,
                             checked=lambda item: auto_start_aktif()),
            pystray.MenuItem("Buka Berkas Log", self._buka_log),
            pystray.MenuItem(None, None, enabled=False),
            pystray.MenuItem(self._teks_versi, None, enabled=False),
            pystray.MenuItem("Periksa Pembaruan", self._cek_update,
                             enabled=lambda item: not self.updater.status["sibuk"]),
            pystray.MenuItem(self._teks_pasang, self._pasang_update,
                             visible=lambda item: bool(self.updater.status["ada"]),
                             enabled=lambda item: not self.updater.status["sibuk"]),
            pystray.MenuItem(None, None, enabled=False),
            pystray.MenuItem("Keluar", self._keluar),
        )

        self.tray = pystray.Icon("HaloDeck", buat_ikon(False),
                                 "HaloDeck Konektor", menu)
        # Perbarui ikon/teks berkala sesuai status
        threading.Thread(target=self._pantau_ui, daemon=True).start()
        self.tray.run()

    # --- Pembaruan UI tray (periodik) ---
    def _pantau_ui(self):
        while True:
            try:
                hijau = state["tersambung"]
                self.tray.icon = buat_ikon(hijau)
                self.tray.title = ("HaloDeck — Tersambung" if hijau
                                   else "HaloDeck — Mencari ESP...")
                self.tray.update_menu()
            except Exception:
                pass
            time.sleep(2)

    # --- Teks menu dinamis ---
    def _teks_status(self, item):
        return ("Status: Tersambung ESP8266" if state["tersambung"]
                else "Status: Mencari ESP8266...")

    def _teks_profil(self, item):
        return f"Profil aktif di PC: {state['profil']}"

    def _teks_aksi(self, item):
        return f"Aksi dieksekusi: {state['jumlah_aksi']}"

    # --- Aksi menu ---
    def _ulang(self, icon, item):
        catat("Jalankan ulang diminta dari menu tray.")
        self.bridge.hentikan()
        time.sleep(1)
        self.bridge.mulai()

    def _toggle_autostart(self, icon, item):
        set_auto_start(not auto_start_aktif())

    def _buka_log(self, icon, item):
        try:
            if not os.path.exists(BERKAS_LOG):
                open(BERKAS_LOG, "w").close()
            os.startfile(BERKAS_LOG)
        except Exception as galat:
            catat(f"Gagal buka log: {galat}")

    # --- Pembaruan aplikasi (GitHub Releases, lihat updater.py) ---
    def _teks_versi(self, item):
        s = self.updater.status
        if s.get("ada"):
            return f"Versi {VERSI}  ->  {s['versi']} TERSEDIA"
        return f"Versi {VERSI} — {s['pesan']}"

    def _teks_pasang(self, item):
        return f"Pasang Pembaruan {self.updater.status.get('versi') or ''}"

    def _cek_update(self, icon, item):
        catat("Pemeriksaan pembaruan diminta manual dari menu tray.")
        self.updater.cek_async()

    def _pasang_update(self, icon, item):
        s = self.updater.status
        if not s.get("ada") or s.get("sibuk"):
            return
        # Konfirmasi memakai jendela bawaan Windows (aman dari pythonw)
        jawab = ctypes.windll.user32.MessageBoxW(
            0,
            f"Pembaruan {s['versi']} tersedia (sekarang {VERSI}).\n\n"
            "Aplikasi akan menutup diri, memasang paket,\n"
            "lalu membuka kembali otomatis.\n\nLanjutkan?",
            "Pembaruan HaloDeck",
            0x04 | 0x20 | 0x100000)     # MB_YESNO | MB_ICONQUESTION | MB_SYSTEMMODAL
        if jawab != 6:                  # IDYES
            catat("Pemasangan pembaruan dibatalkan pengguna.")
            return
        catat(f"Pemasangan pembaruan {s['versi']} dimulai dari menu tray.")
        self.updater.pasang_async()

    def _setelah_pasang(self, jumlah, versi_baru):
        """Dipanggil updater setelah paket terpasang -> jalankan ulang app."""
        catat(f"Pasang selesai ({jumlah} berkas) -> jalankan ulang ke "
              f"versi {versi_baru}.")
        self.bridge.hentikan()
        # Lepas kunci instance dulu supaya proses baru boleh berjalan
        try:
            self.lock_instance.close()
            os.remove(BERKAS_KUNCI)
        except Exception:
            pass
        try:
            pythonw = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(pythonw):
                pythonw = sys.executable
            subprocess.Popen([pythonw, os.path.abspath(__file__)])
            catat("Proses baru diluncurkan.")
        except Exception as galat:
            catat(f"Gagal meluncurkan ulang otomatis: {galat}")
            catat('Jalankan manual: pythonw "%s"' % os.path.abspath(__file__))
        try:
            if self.tray is not None:
                self.tray.stop()
        except Exception:
            pass
        time.sleep(1)
        os._exit(0)

    def _keluar(self, icon, item):
        catat("Keluar dari menu tray.")
        self.bridge.hentikan()
        try:
            self.lock_instance.close()
            os.remove(BERKAS_KUNCI)
        except Exception:
            pass
        icon.stop()


if __name__ == "__main__":
    KonektorTray().jalankan()
