# ============================================================
# HALODECK - Jendela UI Konektor (tkinter)
# File: ui_jendela.py
# Tugas : Memberi konektor wajah yang bisa dilihat & diklik:
#         status koneksi, profil aktif, tombol makro, pembaruan,
#         pengaturan auto-start, dan log langsung.
# Catatan:
#         - Jendela ini TIDAK menutup aplikasi; menutup jendela =
#           menyembunyikan ke tray (konektor tetap jalan).
#         - tkinter harus dijalankan di thread utama, sedangkan tray
#           pystray berjalan detached (lihat connector_app.jalankan()).
#         - Semua perintah dari thread lain (tray) dikirim lewat
#           antrean queue -> aman dari race condition.
# Komentar dalam Bahasa Indonesia
# ============================================================

import os
import queue
import tkinter as tk
from tkinter import ttk

JENDELA_W, JENDELA_H = 680, 500
BARIS_LOG_MAKS = 200
POLL_UI_MS = 400


class JendelaKonektor:
    """Jendela utama HaloDeck. Dibuat lewat siapkan() di connector_app."""

    def __init__(self, app, state, catat, berkas_log,
                 auto_start_aktif, set_auto_start,
                 sembunyi_tray_aktif, set_sembunyi_tray):
        self.app = app                        # objek KonektorTray
        self.state = state                    # dict status bersama
        self.catat = catat
        self.berkas_log = berkas_log
        self.auto_start_aktif = auto_start_aktif
        self.set_auto_start = set_auto_start
        self.sembunyi_tray_aktif = sembunyi_tray_aktif
        self.set_sembunyi_tray = set_sembunyi_tray
        self.antrean = queue.Queue()          # perintah dari thread lain
        self._ukuran_log_terakhir = 0
        self._jumlah_baris_log = 0
        self._keluar_dipanggil = False

        self._bangun_jendela()

    # ----------------------------------------------------------
    # BANGUN TAMPILAN
    # ----------------------------------------------------------
    def _bangun_jendela(self):
        self.win = tk.Tk()
        self.win.withdraw()                   # Awalnya tersembunyi; tampilkan() jika diminta
        self.win.title("HaloDeck Konektor")
        self.win.geometry(f"{JENDELA_W}x{JENDELA_H}")
        self.win.minsize(580, 380)
        self.win.protocol("WM_DELETE_WINDOW", self.sembunyikan)
        try:
            ttk.Style().theme_use("vista")
        except Exception:
            pass

        pokok = ttk.Frame(self.win, padding=12)
        pokok.pack(fill=tk.BOTH, expand=True)

        # --- 1. Kartu status ---
        kartu = ttk.LabelFrame(pokok, text=" Status ", padding=10)
        kartu.pack(fill=tk.X)
        self.kanvas_dot = tk.Canvas(kartu, width=18, height=18,
                                    highlightthickness=0, bd=0)
        self.kanvas_dot.grid(row=0, column=0, sticky="w")
        self.dot = self.kanvas_dot.create_oval(2, 2, 16, 16, fill="#7f8c8d")
        self.lbl_status = ttk.Label(kartu, text="Memulai...", font=("", 11, "bold"))
        self.lbl_status.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.lbl_profil = ttk.Label(kartu, text="Profil: -")
        self.lbl_profil.grid(row=0, column=2, sticky="e", padx=(16, 0))
        self.lbl_aksi = ttk.Label(kartu, text="Aksi: 0")
        self.lbl_aksi.grid(row=0, column=3, sticky="e", padx=(16, 0))
        self.lbl_port = ttk.Label(kartu, text="", foreground="#666")
        self.lbl_port.grid(row=1, column=0, columnspan=4, sticky="w",
                           pady=(6, 0))
        kartu.columnconfigure(1, weight=1)

        # --- 2. Pembaruan & pengaturan ---
        perbarui = ttk.LabelFrame(pokok, text=" Pembaruan & Pengaturan ", padding=10)
        perbarui.pack(fill=tk.X, pady=(10, 10))
        self.lbl_versi = ttk.Label(perbarui, text="Versi ...")
        self.lbl_versi.grid(row=0, column=0, sticky="w")
        self.btn_cek = ttk.Button(perbarui, text="Periksa Pembaruan",
                                  command=self._cek_update)
        self.btn_cek.grid(row=0, column=1, padx=6)
        self.btn_pasang = ttk.Button(perbarui, text="Pasang Pembaruan",
                                     command=self._pasang_update,
                                     state=tk.DISABLED)
        self.btn_pasang.grid(row=0, column=2, padx=6)

        # Opsi auto-start bersama Windows & sembunyi di tray
        bingkai_opsi = ttk.Frame(perbarui)
        bingkai_opsi.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.cek_autostart = tk.BooleanVar(
            value=bool(self.auto_start_aktif()))
        self.chk_autostart = ttk.Checkbutton(
            bingkai_opsi, text="Mulai otomatis bersama Windows",
            variable=self.cek_autostart,
            command=self._toggle_autostart)
        self.chk_autostart.pack(anchor="w")

        self.cek_sembunyi = tk.BooleanVar(
            value=bool(self.sembunyi_tray_aktif()))
        self.chk_sembunyi = ttk.Checkbutton(
            bingkai_opsi, text="Sembunyi di tray saat start otomatis",
            variable=self.cek_sembunyi,
            command=self._toggle_sembunyi)
        self.chk_sembunyi.pack(anchor="w", padx=(20, 0), pady=(4, 0))

        self._perbarui_status_opsi()
        perbarui.columnconfigure(0, weight=1)

        # --- 3. Log langsung ---
        log = ttk.LabelFrame(pokok, text=" Log ", padding=6)
        log.pack(fill=tk.BOTH, expand=True)
        self.txt_log = tk.Text(log, height=8, wrap=tk.WORD, state=tk.DISABLED,
                               background="#1e1e2e", foreground="#cdd6f4",
                               insertbackground="#cdd6f4", font=("Consolas", 9))
        geser = ttk.Scrollbar(log, orient=tk.VERTICAL, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=geser.set)
        geser.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        # --- 5. Tombol bawah ---
        bawah = ttk.Frame(pokok)
        bawah.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(bawah, text="Jalankan Ulang Koneksi",
                   command=self._ulang_koneksi).pack(side=tk.LEFT)
        ttk.Button(bawah, text="Buka Berkas Log",
                   command=self._buka_log).pack(side=tk.LEFT, padx=6)
        ttk.Button(bawah, text="Sembunyikan",
                   command=self.sembunyikan).pack(side=tk.RIGHT)
        ttk.Button(bawah, text="Keluar", command=self.keluar).pack(
            side=tk.RIGHT, padx=6)

        # Judul & pemuatan awal
        try:
            from versi import VERSI
            self.win.title(f"HaloDeck Konektor  v{VERSI}")
        except Exception:
            pass
        self._muat_log_awal()
        self._segar()

    # ----------------------------------------------------------
    # PERINTAH THREAD-SAFE (dipanggil dari thread tray / updater)
    # ----------------------------------------------------------
    def perintah(self, nama, muatan=None):
        self.antrean.put((nama, muatan))

    def tampilkan(self):
        self.win.deiconify()
        self.win.lift()
        try:
            self.win.focus_force()
        except Exception:
            pass

    def sembunyikan(self):
        self.win.withdraw()

    def keluar(self):
        """Tutup jendela & beri tahu aplikasi untuk benar-benar keluar."""
        self._keluar_dipanggil = True
        self.win.destroy()

    def jalankan(self):
        """Loop utama tkinter (menghalangi sampai jendela ditutup total)."""
        self._detak()
        self.win.mainloop()

    # ----------------------------------------------------------
    # DETAK JANTUNG: perbarui tampilan tiap POLL_UI_MS
    # ----------------------------------------------------------
    def _detak(self):
        # 1) Perintah dari thread lain
        try:
            while True:
                nama, muatan = self.antrean.get_nowait()
                if nama == "buka":
                    self.tampilkan()
                elif nama == "log" and muatan:
                    self._tulis_log(muatan)
                elif nama == "keluar":
                    self.keluar()
                    return
        except queue.Empty:
            pass

        # 2) Perbarui label dari state
        self._segar()

        # 3) Ekor log (bila berkas bertambah)
        self._muat_log_tambahan()

        if not self._keluar_dipanggil:
            self.win.after(POLL_UI_MS, self._detak)

    def _segar(self):
        from versi import VERSI
        s = self.state
        hijau = bool(s.get("tersambung"))
        jalur = s.get("jalur", "-")
        profil = s.get("profil", "-")
        aksi = s.get("jumlah_aksi", 0)

        teks_status = f"TERSAMBUNG — {jalur}" if hijau else "Mencari ESP8266..."
        teks_profil = f"Profil: {profil}"
        teks_aksi = f"Aksi: {aksi}"
        teks_port = f"Jalur {jalur}  ·  Log: {os.path.basename(self.berkas_log)}"

        u = self.app.updater.status
        if u.get("ada"):
            teks_versi = f"Versi {VERSI}  ->  {u['versi']} TERSEDIA"
            fg_versi = "#2ecc71"
            teks_pasang = f"Pasang {u['versi']}"
            state_pasang = tk.NORMAL if not u.get("sibuk") else tk.DISABLED
        else:
            teks_versi = f"Versi {VERSI} — {u.get('pesan', '')}"
            fg_versi = "#666"
            teks_pasang = "Pasang Pembaruan"
            state_pasang = tk.DISABLED

        state_cek = tk.DISABLED if u.get("sibuk") else tk.NORMAL

        state_sekarang = (hijau, teks_status, teks_profil, teks_aksi, teks_port,
                          teks_versi, fg_versi, teks_pasang, state_pasang, state_cek)

        # Hindari configure widget bila tidak ada perubahan agar efek hover mouse stabil
        if getattr(self, "_state_cache", None) == state_sekarang:
            return
        self._state_cache = state_sekarang

        warna_dot = "#2ecc71" if hijau else "#e74c3c"
        self.kanvas_dot.itemconfigure(self.dot, fill=warna_dot)
        self.lbl_status.configure(text=teks_status)
        self.lbl_profil.configure(text=teks_profil)
        self.lbl_aksi.configure(text=teks_aksi)
        self.lbl_port.configure(text=teks_port)
        self.lbl_versi.configure(text=teks_versi, foreground=fg_versi)
        self.btn_pasang.configure(text=teks_pasang, state=state_pasang)
        self.btn_cek.configure(state=state_cek)

    # ----------------------------------------------------------
    # PENGATURAN & AKSI
    # ----------------------------------------------------------
    def _cek_update(self):
        self.catat("Pemeriksaan pembaruan diminta dari jendela UI.")
        self.app.updater.cek_async()

    def _pasang_update(self):
        s = self.app.updater.status
        if not s.get("ada") or s.get("sibuk"):
            return
        from tkinter import messagebox
        if not messagebox.askyesno(
                "Pembaruan HaloDeck",
                f"Pembaruan {s['versi']} tersedia (sekarang "
                f"{self.app.versi_app}).\n\n"
                "Aplikasi akan menutup diri, memasang paket,\n"
                "lalu membuka kembali otomatis.\n\nLanjutkan?",
                parent=self.win):
            self.catat("Pemasangan pembaruan dibatalkan pengguna (UI).")
            return
        self.catat(f"Pemasangan pembaruan {s['versi']} dimulai dari jendela UI.")
        self.app.updater.pasang_async()

    def _toggle_autostart(self):
        self.set_auto_start(bool(self.cek_autostart.get()))
        self.cek_autostart.set(bool(self.auto_start_aktif()))
        self._perbarui_status_opsi()

    def _toggle_sembunyi(self):
        self.set_sembunyi_tray(bool(self.cek_sembunyi.get()))
        self.cek_sembunyi.set(bool(self.sembunyi_tray_aktif()))

    def _perbarui_status_opsi(self):
        if self.cek_autostart.get():
            self.chk_sembunyi.configure(state=tk.NORMAL)
        else:
            self.chk_sembunyi.configure(state=tk.DISABLED)

    def _ulang_koneksi(self):
        self.catat("Jalankan ulang koneksi diminta dari jendela UI.")
        self.app.bridge.hentikan()
        self.app.bridge.mulai()

    def _buka_log(self):
        import webbrowser
        try:
            if not os.path.exists(self.berkas_log):
                open(self.berkas_log, "w").close()
            os.startfile(self.berkas_log)
        except Exception as galat:
            self.catat(f"Gagal buka log: {galat}")

    # ----------------------------------------------------------
    # LOG (baca ekor berkas)
    # ----------------------------------------------------------
    def _muat_log_awal(self):
        try:
            self._ukuran_log_terakhir = os.path.getsize(self.berkas_log)
        except OSError:
            self._ukuran_log_terakhir = 0
        self._muat_log_tambahan(paksa=True)

    def _muat_log_tambahan(self, paksa=False):
        try:
            ukuran = os.path.getsize(self.berkas_log)
        except OSError:
            return
        if paksa:
            # Muat awal -> 128 KB terakhir saja supaya jendela ringan
            if ukuran <= 0:
                return
            offset = max(0, ukuran - 128 * 1024)
        else:
            if ukuran < self._ukuran_log_terakhir:
                # Log dirotasi/dipangkas -> mulai dari awal lagi
                offset = 0
            elif ukuran > self._ukuran_log_terakhir:
                # Bertambah -> baca HANYA bagian yang belum pernah dibaca
                offset = self._ukuran_log_terakhir
            else:
                return                      # tidak berubah -> lewati
        try:
            with open(self.berkas_log, "r", encoding="utf-8",
                      errors="replace") as f:
                f.seek(offset)
                teks = f.read()
        except OSError:
            return
        self._ukuran_log_terakhir = ukuran
        self._tulis_log(teks)

    def _tulis_log(self, teks):
        baris = [b for b in teks.splitlines() if b.strip()]
        if not baris:
            return
        self.txt_log.configure(state=tk.NORMAL)
        for b in baris:
            self.txt_log.insert(tk.END, b + "\n")
            self._jumlah_baris_log += 1
        # Batasi agar memori ringan
        while self._jumlah_baris_log > BARIS_LOG_MAKS:
            self.txt_log.delete("1.0", "2.0")
            self._jumlah_baris_log -= 1
        self.txt_log.see(tk.END)
        self.txt_log.configure(state=tk.DISABLED)


def siapkan(app, state, catat, berkas_log,
            auto_start_aktif, set_auto_start,
            sembunyi_tray_aktif, set_sembunyi_tray):
    """Buat jendela; kembalikan None bila tkinter tidak tersedia."""
    try:
        return JendelaKonektor(app, state, catat, berkas_log,
                               auto_start_aktif, set_auto_start,
                               sembunyi_tray_aktif, set_sembunyi_tray)
    except Exception as galat:
        catat(f"Jendela UI tidak tersedia ({galat}) -> mode tray saja.")
        return None
