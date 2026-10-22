# ============================================================
# HALODECK - Generator ikon tombol makro (Android)
# File: tools/buat_ikon.py
# Tugas : Menarik SVG dari Google Material Symbols (lisensi Apache-2.0)
#         lalu mengubahnya menjadi Android VectorDrawable.
#         Hasilnya berkas drawableXML biasa -- TIDAK ada dependensi
#         runtime yang ditambahkan, sesuai prinsip "tanpa library
#         eksternal" di android_app/app/build.gradle.kts.
# Pakai : C:\Python310\python.exe tools\buat_ikon.py
# Catatan:
#         - Ikon memakai gaya "outlined", viewport 960 (asli Material).
#         - Warna dasar putih; diberi warna lewat setColorFilter() di
#           MainActivity agar bisa berbeda per status (normal/tekan/bahaya).
#         - Bila nama simbol tidak ada di repo, kandidat cadangan berikutnya
#           dicoba otomatis.
# Komentar dalam Bahasa Indonesia
# ============================================================

import os
import re
import urllib.request

# Berkas drawable tujuan (relatif terhadap akar repositori)
FOLDER_TUJUAN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "android_app", "app", "src", "main", "res", "drawable")

URL_SVG = ("https://raw.githubusercontent.com/google/material-design-icons/"
           "master/symbols/web/{n}/materialsymbolsoutlined/{n}_24px.svg")

# Kunci: nama berkas hasil (ic_m_<kunci>.xml)
# Nilai: daftar nama simbol Material, dicoba berurutan sampai berhasil
PETA = {
    "lock":         ["lock"],                      # Kunci PC
    "mute":         ["volume_off"],                # Bisukan
    "volume":       ["volume_up"],                 # Slider volume
    "browser":      ["language"],                  # Browser
    "taskmgr":      ["monitoring", "query_stats"], # Manajer Tugas
    "notepad":      ["description"],               # Notepad
    "vscode":       ["code"],                      # VS Code
    "simpan":       ["save"],                      # Simpan (Ctrl+S)
    "baru":         ["note_add"],                  # Dokumen baru (Ctrl+N)
    "tabbaru":      ["tab", "add_box"],            # Tab baru (Ctrl+T)
    "tutuptab":     ["tab_close", "close"],        # Tutup tab (Ctrl+W)
    # Catatan: "restore" dan "keyboard_tab_back" TIDAK ada di repo Material
    # Symbols (sudah diperiksa). Pakai "replay" (panah melingkar = buka lagi)
    # dan pas simetris navigate_next/navigate_before untuk pindah tab, supaya
    # tidak kembar dengan tombol Mundur/Maju (arrow_back/arrow_forward).
    "bukalagi":     ["replay"],                    # Buka lagi (Ctrl+Shift+T)
    "tablanjut":    ["navigate_next"],
    "tabsebelum":   ["navigate_before"],
    "reload":       ["refresh"],                   # Muat ulang (F5)
    "mundur":       ["arrow_back"],                # Alt+Left
    "maju":         ["arrow_forward"],             # Alt+Right
    "cari":         ["search"],                    # Cari (Ctrl+F)
    "alamat":       ["link"],                      # Kolom alamat (Ctrl+L)
    "bookmark":     ["bookmark"],                  # Markah (Ctrl+D)
    "riwayat":      ["history"],                   # Riwayat (Ctrl+H)
    "unduhan":      ["download"],                  # Unduhan (Ctrl+J)
    "incognito":    ["visibility_off", "person_off"],  # Jendela privat
    "devtools":     ["terminal", "code"],          # DevTools (Ctrl+Shift+I)
    "undo":         ["undo"],                      # Urungkan (Ctrl+Z)
    "redo":         ["redo"],                      # Ulangi (Ctrl+Y)
    "ps_zoomin":    ["zoom_in"],                   # Photoshop: perbesar
    "ps_zoomout":   ["zoom_out"],                  # Photoshop: perkecil
    "ps_fit":       ["fit_screen", "aspect_ratio", "fullscreen"],
    "ps_layer":     ["layers"],                    # Photoshop: lapisan baru
    "ps_flatten":   ["unfold_less", "compress"],   # Photoshop: ratakan
    "pr_cut":       ["content_cut"],               # Premiere: pangkas (Ctrl+K)
    "pr_in":        ["login"],                     # Premiere: mark in (I)
    "pr_out":       ["logout"],                    # Premiere: mark out (O)
    "pr_export":    ["save_alt", "photo"],         # Premiere: ekspor frame
}

BERKAS_TEMPLAT = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<!-- Ikon tombol makro "{kode}".\n'
    '     Sumber: Google Material Symbols (lisensi Apache-2.0), diubah dari\n'
    '     SVG menjadi VectorDrawable oleh tools/buat_ikon.py sehingga tidak\n'
    '     ada dependensi runtime yang ditambahkan.\n'
    '     Warna dasar putih; diberi warna lewat setColorFilter() di\n'
    '     MainActivity agar bisa berbeda per keadaan (normal/tekan/bahaya). -->\n'
    '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
    '    android:width="24dp"\n'
    '    android:height="24dp"\n'
    '    android:viewportWidth="{vw}"\n'
    '    android:viewportHeight="{vh}">\n'
    # viewBox Material Symbols adalah "0 -960 960 960": semua koordinat Y
    # berada di rentang negatif. Tanpa geseran ini seluruh path digambar
    # DI LUAR bidang pandang dan ikon tidak terlihat sama sekali.
    '    <group\n'
    '        android:translateX="{geser_x}"\n'
    '        android:translateY="{geser_y}">\n'
    '{paths}\n'
    '    </group>\n'
    '</vector>\n'
)

TEMPLAT_PATH = ('    <path\n'
                '        android:fillColor="#FFFFFFFF"\n'
                '        android:pathData="{d}"/>')


def ambil_svg(nama):
    """Unduh SVG satu simbol. Mengembalikan None bila tidak ada."""
    url = URL_SVG.format(n=nama)
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            return r.read().decode("utf-8")
    except Exception:
        return None


def konversi(svg):
    """Ambil ukuran viewport dan semua <path d="..."> dari isi SVG.

    CATATAN PENTING: viewBox Material Symbols berbentuk "0 -960 960 960".
    Artinya titik awal bidang pandang ada di Y negatif, sehingga seluruh
    koordinat path berada di rentang -960..0. Bila nilai min-Y ini diabaikan,
    seluruh path digambar DI LUAR bidang pandang dan ikon tidak terlihat
    sama sekali (cacat yang pernah terjadi di HaloDeck 1.1.0). Nilai
    geseran dikembalikan agar berkas hasil bisa digeser masuk lebih dulu.
    """
    m = re.search(r'viewBox="([\d.\-\s]+)"', svg)
    if not m:
        return None
    vb = m.group(1).split()
    if len(vb) != 4:
        return None
    daftar_d = re.findall(r'<path[^>]*\sd="([^"]+)"', svg)
    if not daftar_d:
        return None
    return {
        "vw": vb[2],
        "vh": vb[3],
        # Geseran yang diperlukan agar isi viewBox (yang berawal di Y negatif)
        # jatuh ke rentang 0..viewportHeight
        "geser_x": str(int(-float(vb[0]))) if float(vb[0]) else "0",
        "geser_y": str(int(-float(vb[1]))) if float(vb[1]) else "0",
        "daftar_d": daftar_d,
    }


def utama():
    if not os.path.isdir(FOLDER_TUJUAN):
        print("Folder tujuan tidak ada:", FOLDER_TUJUAN)
        return 1

    gagal = []
    for kode, kandidat in PETA.items():
        svg, dipakai = None, None
        for nama in kandidat:
            svg = ambil_svg(nama)
            if svg:
                dipakai = nama
                break

        if not svg:
            gagal.append(kode)
            print("GAGAL  %-12s -> %s" % (kode, " / ".join(kandidat)))
            continue

        hasil = konversi(svg)
        if not hasil:
            gagal.append(kode)
            print("GAGAL  %-12s (tidak ada path di SVG)" % kode)
            continue

        berkas = BERKAS_TEMPLAT.format(
            kode=kode,
            vw=hasil["vw"],
            vh=hasil["vh"],
            geser_x=hasil["geser_x"],
            geser_y=hasil["geser_y"],
            paths="\n".join(
                TEMPLAT_PATH.format(d=d.replace('"', "&quot;"))
                for d in hasil["daftar_d"]),
        )
        daftar_d = hasil["daftar_d"]
        tujuan = os.path.join(FOLDER_TUJUAN, "ic_m_%s.xml" % kode)
        with open(tujuan, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(berkas)
        print("OK     %-12s <- %-16s (%d path)" % (kode, dipakai, len(daftar_d)))

    print("\nIkon jadi : %d" % (len(PETA) - len(gagal)))
    print("Gagal     : %d" % len(gagal))
    if gagal:
        print("Perlu nama pengganti manual:", ", ".join(gagal))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(utama())
