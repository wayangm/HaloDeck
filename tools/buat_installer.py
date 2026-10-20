# ============================================================
# PEMBUAT INSTALLER WINDOWS (Inno Setup)
# File: tools/buat_installer.py
# Tugas : Merakit installer HaloDeck-Win-Setup-<versi>.exe yang
#         berisi: Python portable + dependensi + kode .py HaloDeck.
#         Hasilnya APLIKASI .PY ASLI yang bisa dibaca & dimodifikasi
#         pengguna — python.exe di dalamnya hanya "mesin".
# Pemakaian:
#         python tools/buat_installer.py
# Syarat :
#         - Python 3.10 di mesin build (untuk mengambil dependensi)
#         - Inno Setup 6 (ISCC.exe)
# Komentar dalam Bahasa Indonesia
# ============================================================

import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

FOLDER_TOOL = os.path.dirname(os.path.abspath(__file__))
FOLDER_PROYEK = os.path.dirname(FOLDER_TOOL)
FOLDER_PC = os.path.join(FOLDER_PROYEK, "pc_bridge")
FOLDER_BUILD = os.path.join(FOLDER_PROYEK, "build")
FOLDER_RUNTIME = os.path.join(FOLDER_BUILD, "runtime")
FOLDER_KELUARAN = os.path.join(FOLDER_PROYEK, "dist")

sys.path.insert(0, FOLDER_PC)
from versi import VERSI  # noqa: E402

# Python portable resmi (hanya "mesin", bukan bagian dari kode kita)
PYTHON_EMBED = ("https://www.python.org/ftp/python/3.10.11/"
                "python-3.10.11-embed-amd64.zip")
PERINTAH_PIP = ["pyserial", "pystray", "pillow"]

ISCC_KANDIDAT = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
]


def catat(pesan):
    print(f"[installer] {pesan}", flush=True)


def cari_iscc():
    dari_path = shutil.which("ISCC") or shutil.which("iscc")
    if dari_path:
        return dari_path
    for kandidat in ISCC_KANDIDAT:
        if os.path.exists(kandidat):
            return kandidat
    return None


def unduh_python_embed():
    tujuan = os.path.join(FOLDER_BUILD, "python-embed.zip")
    if os.path.isfile(tujuan) and os.path.getsize(tujuan) > 1_000_000:
        catat("Python portable sudah ada (pakai cache).")
        return tujuan
    catat(f"Mengunduh Python portable: {PYTHON_EMBED}")
    urllib.request.urlretrieve(PYTHON_EMBED, tujuan)
    return tujuan


def siapkan_runtime(zip_python):
    if os.path.isdir(FOLDER_RUNTIME):
        shutil.rmtree(FOLDER_RUNTIME, ignore_errors=True)
    os.makedirs(FOLDER_RUNTIME, exist_ok=True)
    catat("Ekstrak Python portable...")
    with zipfile.ZipFile(zip_python) as z:
        z.extractall(FOLDER_RUNTIME)

    # Aktifkan site-packages pada file ._pth (embeddable mematikan site by default)
    pth = os.path.join(FOLDER_RUNTIME, "python310._pth")
    baris = ["python310.zip", ".", "Lib\\site-packages", "app", "import site", ""]
    with open(pth, "w", encoding="utf-8") as f:
        f.write("\n".join(baris))

    # Ambil dependensi pakai Python build (lebih sederhana daripada get-pip)
    target = os.path.join(FOLDER_RUNTIME, "Lib", "site-packages")
    os.makedirs(target, exist_ok=True)
    catat("Mengambil dependensi: " + ", ".join(PERINTAH_PIP) + " ...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--target", target,
         "--quiet", "--no-warn-script-location"] + PERINTAH_PIP,
        check=True,
    )

    # Salin kode HaloDeck (.py asli — TIDAK dikompilasi)
    tujuan_app = os.path.join(FOLDER_RUNTIME, "app")
    os.makedirs(tujuan_app, exist_ok=True)
    jumlah = 0
    for nama in sorted(os.listdir(FOLDER_PC)):
        if not nama.endswith(".py"):
            continue
        if nama == "__pycache__":
            continue
        shutil.copy2(os.path.join(FOLDER_PC, nama), os.path.join(tujuan_app, nama))
        jumlah += 1
    if jumlah < 5:
        raise SystemExit("GAGAL: berkas pc_bridge tidak lengkap.")
    # Konfigurasi pembaruan ikut dibawa agar instalasi baru langsung bisa
    # memeriksa rilis (updater TIDAK pernah menimpa berkas ini saat update)
    cfg = os.path.join(FOLDER_PC, "update_config.json")
    if os.path.isfile(cfg):
        shutil.copy2(cfg, os.path.join(tujuan_app, "update_config.json"))
        jumlah += 1
    catat(f"{jumlah} berkas HaloDeck disalin ke runtime.")
    return jumlah


def tulis_skrip_iss():
    """Tulis berkas Inno Setup script (hasilnya di build/halodeck.iss).

    Pakai token @VERSI@ (bukan f-string) supaya semua kurung kurawal
    milik Inno Setup ditulis apa adanya tanpa perlu di-escape.
    """
    iss = os.path.join(FOLDER_BUILD, "halodeck.iss")
    isi = r"""; ============================================================
; Skrip installer HaloDeck (dihasilkan tools/buat_installer.py)
; Isi: Python portable + kode .py asli HaloDeck (bisa dibaca pengguna)
; ============================================================
#define AppName "HaloDeck"
#define AppVersion "@VERSI@"
#define AppPublisher "wayangm"
#define AppURL "https://github.com/wayangm/HaloDeck"

[Setup]
AppId={{8B4E1C52-7A19-4E0B-9F3D-2C6A5D8E1F70}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=HaloDeck-Win-Setup-{#AppVersion}
UninstallDisplayName={#AppName} {#AppVersion}
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
; Instal per-user (tanpa admin) - aplikasi juga meng-update dirinya sendiri
PrivilegesRequired=lowest
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Buat ikon di desktop"; GroupDescription: "Pintasan tambahan:"; Flags: unchecked

[Files]
Source: "runtime\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName} Konektor"; Filename: "{app}\pythonw.exe"; Parameters: @PARAM@; Comment: "Konektor HaloDeck (tray Windows)"
Name: "{group}\Buka Berkas Log"; Filename: "{app}\app\konektor.log"
Name: "{autodesktop}\{#AppName} Konektor"; Filename: "{app}\pythonw.exe"; Parameters: @PARAM@; Tasks: desktopicon

[Run]
Filename: "{app}\pythonw.exe"; Parameters: @PARAM@; Description: "Jalankan {#AppName} sekarang"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\app\_cadangan"
Type: files; Name: "{app}\app\konektor.log"
Type: files; Name: "{app}\app\konektor.lock"
"""
    isi = isi.replace("@VERSI@", VERSI)
    # @PARAM@ -> """{app}\app\connector_app.py"""  (escaped quote khas Inno;
    # ditulis via token supaya tanda kutip ganda tidak memutus string Python)
    isi = isi.replace("@PARAM@", chr(34) * 3 + r"{app}\app\connector_app.py" + chr(34) * 3)
    with open(iss, "w", encoding="utf-8") as f:
        f.write(isi)
    return iss


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blok in iter(lambda: f.read(64 * 1024), b""):
            h.update(blok)
    return h.hexdigest()


def utama():
    iscc = cari_iscc()
    if not iscc:
        raise SystemExit("GAGAL: ISCC.exe (Inno Setup 6) tidak ditemukan. "
                         "Install dulu: winget install JRSoftware.InnoSetup")

    zip_python = unduh_python_embed()
    siapkan_runtime(zip_python)

    iss = tulis_skrip_iss()
    os.makedirs(FOLDER_KELUARAN, exist_ok=True)
    keluaran = os.path.join(FOLDER_KELUARAN, f"HaloDeck-Win-Setup-{VERSI}.exe")

    catat(f"Kompilasi installer -> {keluaran}")
    subprocess.run([iscc, iss], check=True)

    if not os.path.isfile(keluaran):
        raise SystemExit("GAGAL: berkas installer tidak dihasilkan.")

    berkas_sh = keluaran + ".sha256"
    with open(berkas_sh, "w", encoding="utf-8") as f:
        f.write(f"{sha256(keluaran)}  {os.path.basename(keluaran)}\n")

    catat(f"Installer : {keluaran}")
    catat(f"Ukuran    : {os.path.getsize(keluaran) / (1024 * 1024):.1f} MB")
    catat(f"SHA-256   : {sha256(keluaran)}")
    catat("Selesai — unggah exe + .sha256 sebagai asset rilis.")


if __name__ == "__main__":
    utama()
