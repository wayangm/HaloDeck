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

# ---------- GRUP TOMBOL MAKRO (kunci = kode aksi di aksi.py) ----------
GRUP_AKSI = [
    ("Umum", [
        ("LOCK", "Kunci PC"), ("MUTE", "Mute"),
        ("BROWSER", "Browser"), ("TASKMGR", "Task Manager"),
    ]),
    ("Produktivitas", [
        ("SIMPAN", "Simpan"), ("BARU", "Baru"), ("UNDO", "Undo"),
        ("REDO", "Redo"), ("TABBARU", "Tab Baru"), ("TUTUPTAB", "Tutup Tab"),
        ("BUKALAGI", "Buka Lagi"), ("RELOAD", "Reload"), ("CARI", "Cari"),
    ]),
    ("Photoshop", [
        ("PS_ZOOMIN", "Zoom +"), ("PS_ZOOMOUT", "Zoom -"), ("PS_FIT", "Fit Layar"),
        ("PS_LAYER", "Layer Baru"), ("PS_FLATTEN", "Flatten"),
    ]),
    ("Premiere Pro", [
        ("PR_UNDO", "Undo"), ("PR_CUT", "Cut"), ("PR_IN", "Mark In"),
        ("PR_OUT", "Mark Out"), ("PR_EXPORT", "Export Frame"),
    ]),
]

JENDELA_W, JENDELA_H = 720, 600
BARIS_LOG_MAKS = 200
POLL_UI_MS = 400


class JendelaKonektor:
    """Jendela utama HaloDeck. Dibuat lewat siapkan() di connector_app."""

    def __init__(self, app, state, catat, berkas_log,
                 auto_start_aktif, set_auto_start):
        from aksi import PEMETA_AKSI          # impor di sini: hindari siklus
        self.app = app                        # objek KonektorTray
        self.state = state                    # dict status bersama
        self.catat = catat
        self.berkas_log = berkas_log
        self.auto_start_aktif = auto_start_aktif
        self.set_auto_start = set_auto_start
        self.pemeta_aksi = PEMETA_AKSI
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
        self.win.title("HaloDeck Konektor")
        self.win.geometry(f"{JENDELA_W}x{JENDELA_H}")
        self.win.minsize(640, 520)
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

        # --- 2. Tombol makro (klik = langsung dieksekusi di PC) ---
        makro = ttk.LabelFrame(pokok, text=" Tombol Makro (klik = jalankan aksi di PC) ",
                               padding=10)
        makro.pack(fill=tk.X, pady=(10, 0))
        for i, (nama_grup, daftar) in enumerate(GRUP_AKSI):
            bingkai = ttk.LabelFrame(makro, text=f" {nama_grup} ", padding=6)
            bingkai.grid(row=i // 2, column=i % 2, sticky="nsew",
                         padx=(0, 6), pady=(0, 6))
            makro.columnconfigure(0, weight=1)
            makro.columnconfigure(1, weight=1)
            for j, (kode, label) in enumerate(daftar):
                if kode not in self.pemeta_aksi:
                    continue                      # aksi belum ada -> lewati
                ttk.Button(bingkai, text=label, width=14,
                           command=lambda k=kode: self._jalankan_aksi(k)
                           ).grid(row=j // 3, column=j % 3, padx=2, pady=2)

        # --- 3. Pembaruan & pengaturan ---
        perbarui = ttk.LabelFrame(pokok, text=" Pembaruan & Pengaturan ", padding=10)
        perbarui.pack(fill=tk.X, pady=(0, 10))
        self.lbl_versi = ttk.Label(perbarui, text="Versi ...")
        self.lbl_versi.grid(row=0, column=0, sticky="w")
        self.btn_cek = ttk.Button(perbarui, text="Periksa Pembaruan",
                                  command=self._cek_update)
        self.btn_cek.grid(row=0, column=1, padx=6)
        self.btn_pasang = ttk.Button(perbarui, text="Pasang Pembaruan",
                                     command=self._pasang_update,
                                     state=tk.DISABLED)
        self.btn_pasang.grid(row=0, column=2, padx=6)
        self.cek_autostart = tk.BooleanVar(
            value=bool(self.auto_start_aktif()))
        ttk.Checkbutton(perbarui, text="Mulai otomatis bersama Windows",
                        variable=self.cek_autostart,
                        command=self._toggle_autostart).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))
        perbarui.columnconfigure(0, weight=1)

        # --- 4. Log langsung ---
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
        self.kanvas_dot.itemconfigure(self.dot,
                                      fill="#2ecc71" if hijau else "#e74c3c")
        self.lbl_status.configure(
            text=f"TERSAMBUNG — {s.get('jalur', '-')}" if hijau
                 else "Mencari ESP8266...")
        self.lbl_profil.configure(text=f"Profil: {s.get('profil', '-')}")
        self.lbl_aksi.configure(text=f"Aksi: {s.get('jumlah_aksi', 0)}")
        jalur = s.get("jalur", "-")
        self.lbl_port.configure(
            text=f"Jalur {jalur}  ·  "
                 f"Log: {os.path.basename(self.berkas_log)}")

        u = self.app.updater.status
        if u.get("ada"):
            self.lbl_versi.configure(
                text=f"Versi {VERSI}  ->  {u['versi']} TERSEDIA",
                foreground="#2ecc71")
            self.btn_pasang.configure(state=tk.NORMAL,
                                      text=f"Pasang {u['versi']}")
        else:
            self.lbl_versi.configure(text=f"Versi {VERSI} — {u.get('pesan', '')}",
                                     foreground="#666")
            self.btn_pasang.configure(state=tk.DISABLED, text="Pasang Pembaruan")
        self.btn_cek.configure(state=tk.DISABLED if u.get("sibuk") else tk.NORMAL)

    # ----------------------------------------------------------
    # AKSI TOMBOL
    # ----------------------------------------------------------
    def _jalankan_aksi(self, kode):
        from aksi import eksekusi_perintah
        sukses = eksekusi_perintah(f"BTN:{kode}")
        self.catat(f"Aksi dari jendela UI: {kode} "
                   f"({'OK' if sukses else 'GAGAL'})")
        try:
            if sukses:
                self.state["jumlah_aksi"] += 1
        except Exception:
            pass

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


def siapkan(app, state, catat, berkas_log, auto_start_aktif, set_auto_start):
    """Buat jendela; kembalikan None bila tkinter tidak tersedia."""
    try:
        return JendelaKonektor(app, state, catat, berkas_log,
                               auto_start_aktif, set_auto_start)
    except Exception as galat:
        catat(f"Jendela UI tidak tersedia ({galat}) -> mode tray saja.")
        return None
