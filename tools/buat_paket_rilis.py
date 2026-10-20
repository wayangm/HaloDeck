# ============================================================
# PEMBUAT PAKET RILIS WINDOWS (untuk GitHub Releases)
# File: tools/buat_paket_rilis.py
# Tugas : Mengemas isi pc_bridge/ menjadi 1 file zip siap unggah
#         ke halaman "Releases" repo GitHub.
# Pemakaian:
#         python tools/buat_paket_rilis.py
# Hasil  :
#         dist/HaloDeck-Win-<versi>.zip     (asset yang diunggah)
#         dist/HaloDeck-Win-<versi>.sha256  (checksum, opsional)
#
# Alur rilis:
#   1. Naikkan VERSI di pc_bridge/versi.py
#   2. python tools/buat_paket_rilis.py
#   3. GitHub -> Releases -> New release -> tag v<versi>
#   4. Unggah zip (dan .sha256) sebagai asset
#   5. Aplikasi PC yang jalan akan mendeteksi & memasang sendiri
# Komentar dalam Bahasa Indonesia
# ============================================================

import hashlib
import os
import sys
import zipfile
from datetime import datetime

FOLDER_TOOL = os.path.dirname(os.path.abspath(__file__))
FOLDER_PROYEK = os.path.dirname(FOLDER_TOOL)
FOLDER_PC = os.path.join(FOLDER_PROYEK, "pc_bridge")
FOLDER_KELUARAN = os.path.join(FOLDER_PROYEK, "dist")

sys.path.insert(0, FOLDER_PC)
from versi import VERSI  # noqa: E402

# Tidak ikut dikemas: jejak lokal & konfigurasi mesin ini sendiri
KECUALI_BERKAS = {"update_config.json", "konektor.log", "konektor.lock"}
KECUALI_FOLDER = {"__pycache__", "_cadangan", "dist"}


def daftar_isi():
    hasil = []
    for akar, folder, berkas in os.walk(FOLDER_PC):
        folder[:] = [d for d in folder if d not in KECUALI_FOLDER]
        for b in sorted(berkas):
            if b in KECUALI_BERKAS or b.endswith((".pyc", ".log", ".lock")):
                continue
            hasil.append(os.path.join(akar, b))
    return hasil


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blok in iter(lambda: f.read(64 * 1024), b""):
            h.update(blok)
    return h.hexdigest()


def utama():
    berkas = daftar_isi()
    if "connector_app.py" not in [os.path.basename(p) for p in berkas] or \
       "versi.py" not in [os.path.basename(p) for p in berkas]:
        print("GAGAL: pc_bridge tidak lengkap (butuh connector_app.py & versi.py).")
        return 1

    os.makedirs(FOLDER_KELUARAN, exist_ok=True)
    nama = f"HaloDeck-Win-{VERSI}.zip"
    tujuan = os.path.join(FOLDER_KELUARAN, nama)

    with zipfile.ZipFile(tujuan, "w", zipfile.ZIP_DEFLATED) as z:
        for penuh in berkas:
            # Path di dalam zip: di ROOT zip (agar updater menemukan payload)
            z.write(penuh, os.path.relpath(penuh, FOLDER_PC))

    isi = sha256(tujuan)
    berkas_sh = tujuan + ".sha256"
    with open(berkas_sh, "w", encoding="utf-8") as f:
        f.write(f"{isi}  {nama}\n")

    print(f"Paket rilis Win : {tujuan}")
    print(f"Ukuran           : {os.path.getsize(tujuan):,} bytes")
    print(f"Versi            : {VERSI}")
    print(f"Checksum SHA-256 : {isi}")
    print(f"Checksum file    : {berkas_sh}")
    print(f"Isi ({len(berkas)} berkas):")
    for p in berkas:
        print(f"  - {os.path.relpath(p, FOLDER_PC)}")
    print(f"\nDibuat: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("Langkah berikutnya: unggah zip + .sha256 ke GitHub Releases "
          f"tag v{VERSI}.")
    return 0


if __name__ == "__main__":
    sys.exit(utama())
