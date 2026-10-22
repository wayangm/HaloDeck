# ============================================================
# HALODECK - FASE 2b (Modul Eksekusi Aksi PC)
# Tugas : Mengeksekusi aksi nyata Windows dari perintah BTN:<AKSI>
# Platform: Windows 10/11, Python 3.10
# Dependensi: pycaw + comtypes (untuk kontrol audio Windows)
# Komentar dalam Bahasa Indonesia
# ============================================================

import ctypes
import os
import subprocess
import time
import webbrowser
import pyautogui  # Untuk makro keyboard (Tahap 2 & 3)

# Matikan jeda pyautogui agar makro terasa instan
pyautogui.PAUSE = 0.05

# ---------- Objek volume global (diinisialisasi sekali) ----------
_volume_interface = None


def _inisialisasi_audio():
    """Ambil antarmuka speaker (Windows Audio) sekali di awal."""
    global _volume_interface
    if _volume_interface is not None:
        return True
    try:
        from pycaw.pycaw import AudioUtilities

        # PyCaw versi baru: EndpointVolume sudah berupa pointer
        # IAudioEndpointVolume (GetMute/SetMute siap pakai).
        perangkat = AudioUtilities.GetSpeakers()
        _volume_interface = perangkat.EndpointVolume
        return True
    except Exception as galat:
        print(f"[AKSI] Gagal inisialisasi audio: {galat}")
        return False


# ============================================================
# DAFTAR AKSI (panggil lewat eksekusi_perintah("BTN:<AKSI>"))
# ============================================================

def aksi_lock_pc():
    """Kunci layar PC (aman, sama seperti Win+L)."""
    hasil = ctypes.windll.user32.LockWorkStation()
    return hasil != 0  # 0 = gagal


def aksi_toggle_mute():
    """Nyalakan/matikan (toggle) mute speaker."""
    if not _inisialisasi_audio():
        return False
    status_sekarang = _volume_interface.GetMute()  # 1=mute, 0=suara
    status_baru = 0 if status_sekarang else 1
    _volume_interface.SetMute(status_baru, None)
    print(f"[AKSI] Volume {'DI-BISUKAN' if status_baru else 'DIBUKA KEMBALI'}")
    return True


# ============================================================
# VOLUME (dipakai SLIDER di aplikasi Android)
# Berbeda dari tombol makro yang hanya "toggle", slider butuh nilai
# kontinu 0-100. Karena itu volumenya memakai awalan "VOL:" sendiri,
# bukan "BTN:", dan ditangani terpisah di eksekusi_perintah().
# ============================================================
def set_volume(persen):
    """Atur volume master speaker ke 0-100.

    Nilai dijepit (clamp) dulu supaya kiriman dari HP yang tidak wajar
    (mis. "150" atau "-5" karena bug slider) tetap aman.
    """
    if not _inisialisasi_audio():
        return False
    try:
        batas = max(0, min(100, int(persen)))
        # PyCaw memakai skala 0.0-1.0, sedangkan protokol memakai 0-100
        _volume_interface.SetMasterVolumeLevelScalar(batas / 100.0, None)
        print(f"[AKSI] Volume diatur ke {batas}%")
        return True
    except Exception as galat:
        print(f"[AKSI] Gagal atur volume: {galat}")
        return False


def baca_volume():
    """Baca volume master speaker sekarang (0-100), atau None bila gagal.

    Dipakai bridge untuk mendorong volume PC ke HP, sehingga posisi slider
    di HP selalu mencerminkan keadaan PC yang sebenarnya.
    """
    if not _inisialisasi_audio():
        return None
    try:
        return round(_volume_interface.GetMasterVolumeLevelScalar() * 100)
    except Exception as galat:
        print(f"[AKSI] Gagal baca volume: {galat}")
        return None


def aksi_buka_browser():
    """Buka browser default Windows."""
    return webbrowser.open_new("https://www.google.com")


def aksi_buka_taskmgr():
    """Buka Windows Task Manager.
    Catatan: taskmgr.exe di Windows 10/11 minta hak admin (elevation),
    jadi subprocess.Popen biasa akan gagal WinError 740.
    os.startfile() memakai ShellExecute sehingga UAC terpicu dengan benar.
    """
    os.startfile("taskmgr.exe")
    return True


# ============================================================
# TAHAP 2: AKSI PRODUKTIVITAS (Notepad & VS Code)
# ============================================================

def aksi_buka_notepad():
    """Buka Notepad (aplikasi produktivitas dasar)."""
    subprocess.Popen("notepad.exe")
    return True


def aksi_buka_vscode():
    """Buka VS Code bila ada di PATH, jika tidak tampilkan pesan jelas."""
    import shutil
    if shutil.which("code"):
        subprocess.Popen(["code", "."])   # Buka folder kerja saat ini
        return True
    print("[AKSI] VS Code tidak ditemukan di PATH")
    return False


def aksi_simpan():
    """Ctrl+S — simpan dokumen (Notepad/VS Code/editor umum)."""
    pyautogui.hotkey("ctrl", "s")
    return True


def aksi_buat_baru():
    """Ctrl+N — dokumen/tab baru (Notepad, VS Code, editor umum)."""
    pyautogui.hotkey("ctrl", "n")
    return True


def aksi_tab_baru():
    """Ctrl+T — TAB baru di browser (Chrome/Firefox/Edge).
    Catatan: Ctrl+N di browser membuka JENDELA baru, bukan tab,
    jadi browser butuh aksi terpisah ini."""
    pyautogui.hotkey("ctrl", "t")
    return True


# ============================================================
# TAHAP 2b: AKSI KHUSUS BROWSER (Chrome / Firefox / Edge)
# Semua shortcut di bawah seragam di ketiga browser utama.
# ============================================================

def aksi_tab_tutup():
    """Ctrl+W — tutup tab aktif."""
    pyautogui.hotkey("ctrl", "w")
    return True


def aksi_tab_buka_lagi():
    """Ctrl+Shift+T — buka KEMBALI tab yang baru ditutup (undo close).
    Sangat berguna kalau tidak sengaja menutup tab."""
    pyautogui.hotkey("ctrl", "shift", "t")
    return True


def aksi_reload():
    """F5 — muat ulang halaman."""
    pyautogui.press("f5")
    return True


def aksi_cari_halaman():
    """Ctrl+F — cari teks di halaman (find in page)."""
    pyautogui.hotkey("ctrl", "f")
    return True


def aksi_mundur():
    """Alt+Left — kembali ke halaman sebelumnya."""
    pyautogui.hotkey("alt", "left")
    return True


def aksi_maju():
    """Alt+Right — maju ke halaman berikutnya."""
    pyautogui.hotkey("alt", "right")
    return True


def aksi_baris_alamat():
    """Ctrl+L — fokus ke kolom alamat (untuk langsung ketik URL)."""
    pyautogui.hotkey("ctrl", "l")
    return True


def aksi_incognito():
    """Ctrl+Shift+N — jendela incognito / private (Chrome & Edge).
    Firefox memakai Ctrl+Shift+P, jadi Incognito dikhususkan Chrome/Edge."""
    pyautogui.hotkey("ctrl", "shift", "n")
    return True


def aksi_riwayat():
    """Ctrl+H — buka halaman riwayat (history)."""
    pyautogui.hotkey("ctrl", "h")
    return True


def aksi_unduhan():
    """Ctrl+J — buka daftar unduhan (downloads)."""
    pyautogui.hotkey("ctrl", "j")
    return True


def aksi_bookmark():
    """Ctrl+D — tandai halaman sebagai bookmark."""
    pyautogui.hotkey("ctrl", "d")
    return True


def aksi_tab_berikutnya():
    """Ctrl+Tab — pindah ke tab berikutnya."""
    pyautogui.hotkey("ctrl", "tab")
    return True


def aksi_tab_sebelumnya():
    """Ctrl+Shift+Tab — pindah ke tab sebelumnya."""
    pyautogui.hotkey("ctrl", "shift", "tab")
    return True


def aksi_devtools():
    """Ctrl+Shift+I — buka Developer Tools (untuk web developer)."""
    pyautogui.hotkey("ctrl", "shift", "i")
    return True


def aksi_unduh():
    """Ctrl+Z — undo (umum di semua editor)."""
    pyautogui.hotkey("ctrl", "z")
    return True


def aksi_ulang():
    """Ctrl+Y — redo."""
    pyautogui.hotkey("ctrl", "y")
    return True


# ============================================================
# TAHAP 3: MAKRO APLIKASI KREATIF (Photoshop & Premiere Pro)
# Catatan: pyautogui mengirim keyboard ke jendela AKTIF.
# Bridge otomatis sinkron via context-switching (PROF), jadi
# makro hanya dikirim saat aplikasi kreatif memang sedang aktif.
# ============================================================

def aksi_ps_zoom_in():
    """Photoshop: Ctrl+= (zoom in)."""
    pyautogui.hotkey("ctrl", "=")
    return True


def aksi_ps_zoom_out():
    """Photoshop: Ctrl+- (zoom out)."""
    pyautogui.hotkey("ctrl", "-")
    return True


def aksi_ps_fit_screen():
    """Photoshop: Ctrl+0 (fit canvas ke layar)."""
    pyautogui.hotkey("ctrl", "0")
    return True


def aksi_ps_layer_baru():
    """Photoshop: Ctrl+Shift+N (layer baru)."""
    pyautogui.hotkey("ctrl", "shift", "n")
    return True


def aksi_ps_flatten():
    """Photoshop: flatten image via menu (Alt+F, L)."""
    pyautogui.hotkey("alt", "f")
    time.sleep(0.15)
    pyautogui.press("l")
    return True


def aksi_pr_undo():
    """Premiere: Ctrl+Z (undo)."""
    pyautogui.hotkey("ctrl", "z")
    return True


def aksi_pr_cut():
    """Premiere: Ctrl+K (cut/blade di playhead)."""
    pyautogui.hotkey("ctrl", "k")
    return True


def aksi_pr_export_frame():
    """Premiere: Ctrl+Shift+E (export frame)."""
    pyautogui.hotkey("ctrl", "shift", "e")
    return True


def aksi_pr_mark_in():
    """Premiere: I (mark in)."""
    pyautogui.press("i")
    return True


def aksi_pr_mark_out():
    """Premiere: O (mark out)."""
    pyautogui.press("o")
    return True


# ---------- PEMETA PERINTAH -> FUNGSI ----------
PEMETA_AKSI = {
    # --- Tahap 1: Universal ---
    "LOCK":     aksi_lock_pc,
    "MUTE":     aksi_toggle_mute,
    "BROWSER":  aksi_buka_browser,
    "TASKMGR":  aksi_buka_taskmgr,
    # --- Tahap 2: Produktivitas ---
    "NOTEPAD":  aksi_buka_notepad,
    "VSCODE":   aksi_buka_vscode,
    "SIMPAN":   aksi_simpan,        # Ctrl+S
    "BARU":     aksi_buat_baru,     # Ctrl+N (dokumen baru)
    "TABBARU":  aksi_tab_baru,      # Ctrl+T (tab baru di browser)
    "UNDO":     aksi_unduh,         # Ctrl+Z
    "REDO":     aksi_ulang,         # Ctrl+Y
    # --- Tahap 2b: Browser (Chrome/Firefox/Edge) ---
    "TABBARU":    aksi_tab_baru,        # Ctrl+T
    "TUTUPTAB":   aksi_tab_tutup,       # Ctrl+W
    "BUKALAGI":   aksi_tab_buka_lagi,   # Ctrl+Shift+T (undo close tab)
    "RELOAD":     aksi_reload,          # F5
    "CARI":       aksi_cari_halaman,    # Ctrl+F
    "MUNDUR":     aksi_mundur,          # Alt+Left
    "MAJU":       aksi_maju,            # Alt+Right
    "ALAMAT":     aksi_baris_alamat,    # Ctrl+L
    "INCOGNITO":  aksi_incognito,       # Ctrl+Shift+N
    "RIWAYAT":    aksi_riwayat,         # Ctrl+H
    "UNDUHAN":    aksi_unduhan,         # Ctrl+J
    "BOOKMARK":   aksi_bookmark,        # Ctrl+D
    "TABLANJUT":  aksi_tab_berikutnya,  # Ctrl+Tab
    "TABSEBELUM": aksi_tab_sebelumnya,  # Ctrl+Shift+Tab
    "DEVTOOLS":   aksi_devtools,        # Ctrl+Shift+I
    # --- Tahap 3: Photoshop ---
    "PS_ZOOMIN":    aksi_ps_zoom_in,
    "PS_ZOOMOUT":   aksi_ps_zoom_out,
    "PS_FIT":       aksi_ps_fit_screen,
    "PS_LAYER":     aksi_ps_layer_baru,
    "PS_FLATTEN":   aksi_ps_flatten,
    # --- Tahap 3: Premiere Pro ---
    "PR_UNDO":      aksi_pr_undo,
    "PR_CUT":       aksi_pr_cut,
    "PR_EXPORT":    aksi_pr_export_frame,
    "PR_IN":        aksi_pr_mark_in,
    "PR_OUT":       aksi_pr_mark_out,
}


def eksekusi_perintah(perintah):
    """
    Menerima string perintah dan mengeksekusinya.
    Dua bentuk protokol yang dikenali:
      "BTN:<AKSI>" -> tombol makro (nilai tunggal, tanpa argumen)
      "VOL:<0-100>" -> setel volume master (dipakai slider di Android)
    Mengembalikan True bila dikenali & dijalankan.
    """
    # --- Jalur slider volume (awalan VOL:, bukan BTN:) ---
    if perintah.startswith("VOL:"):
        nilai = perintah[4:].strip()
        if not nilai.isdigit():
            # Bukan angka -> jangan lempar error, hanya tolak dengan sopan.
            # HP bisa mengirim nilai tak terduga saat slider digeser cepat.
            print(f"[AKSI] Nilai volume tidak sah: {nilai!r}")
            return False
        sukses = set_volume(nilai)
        print(f"[AKSI] Eksekusi VOL:{nilai}: {'BERHASIL' if sukses else 'GAGAL'}")
        return sukses

    if not perintah.startswith("BTN:"):
        return False

    nama_aksi = perintah[4:].upper()  # Potong "BTN:" -> sisa nama aksi
    fungsi = PEMETA_AKSI.get(nama_aksi)

    if fungsi is None:
        print(f"[AKSI] Aksi tidak dikenal: {nama_aksi}")
        return False

    try:
        sukses = fungsi()
        print(f"[AKSI] Eksekusi {nama_aksi}: {'BERHASIL' if sukses else 'GAGAL'}")
        return sukses
    except Exception as galat:
        print(f"[AKSI] Galat saat eksekusi {nama_aksi}: {galat}")
        return False


# ============================================================
# UJI COBA LANGSUNG (tanpa ESP8266): python aksi.py
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print(" UJI COBA MODUL AKSI - FASE 2b")
    print(" Pilih aksi (LOCK sengaja TIDAK diuji otomatis):")
    print("   1 = MUTE toggle")
    print("   2 = Buka browser")
    print("   3 = Buka Task Manager")
    print("   q = keluar")
    print("=" * 50)
    pilihan = input("Pilihan: ").strip().lower()
    if pilihan == "1":
        eksekusi_perintah("BTN:MUTE")
    elif pilihan == "2":
        eksekusi_perintah("BTN:BROWSER")
    elif pilihan == "3":
        eksekusi_perintah("BTN:TASKMGR")
    elif pilihan == "lock":
        # Hanya jika diminta eksplisit (akan mengunci layar Anda!)
        eksekusi_perintah("BTN:LOCK")
    else:
        print("Tidak ada aksi dijalankan.")
