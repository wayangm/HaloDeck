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
# Daftar pustaka pihak ketiga. SATU-SATUNYA SUMBER KEBENARAN ada di
# pc_bridge/requirements.txt — README merujuk berkas yang sama, sehingga
# daftar tidak lagi disimpan di dua tempat. Perpisahan itulah yang membuat
# pyautogui tertinggal selama tiga rilis (1.0.0-1.0.2) dan menggagalkan
# seluruh installer di mesin pengguna yang tidak punya Python.
BERKAS_REQUIREMENTS = os.path.join(FOLDER_PC, "requirements.txt")
# Berkas & folder Tcl/Tk (untuk jendela UI tkinter) yang disalin dari
# instalasi Python Lengkap yang SUDAH ada di mesin.
BERKAS_TK = ["tcl86t.dll", "tk86t.dll"]
PYD_TK = "_tkinter.pyd"
FOLDER_TK_DATA = "tcl"          # berisi tcl8.6, tk8.6, dde1.4, reg1.3
# Kandidat instalasi Python Lengkap. Hanya DICARI — tidak pernah dipasang.
KANDIDAT_PYTHON_LENGKAP = [
    r"C:\Python310",
    r"C:\Program Files\Python310",
]

ISCC_KANDIDAT = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
]


def catat(pesan):
    print(f"[installer] {pesan}", flush=True)


def baca_requirements():
    """Baca daftar pustaka dari pc_bridge/requirements.txt.

    Berkas itu satu-satunya sumber kebenaran agar daftar tidak lagi
    disimpan di dua tempat (dulu: skrip build dan README) lalu menyimpang.
    Komentar diawali '#' dan boleh menempel di belakang nama pustaka.
    """
    if not os.path.isfile(BERKAS_REQUIREMENTS):
        raise SystemExit(f"GAGAL: {BERKAS_REQUIREMENTS} tidak ditemukan.")
    daftar = []
    with open(BERKAS_REQUIREMENTS, "r", encoding="utf-8") as f:
        for baris in f:
            baris = baris.split("#", 1)[0].strip()
            if baris:
                daftar.append(baris)
    if not daftar:
        raise SystemExit(
            f"GAGAL: {BERKAS_REQUIREMENTS} tidak memuat pustaka apa pun.")
    return daftar


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


def siapkan_tcltk():
    """Tentukan SUMBER Tcl/Tk 8.6 untuk runtime portabel.

    Python portable TIDAK menyertakan tkinter, maka berkasnya diambil
    dari instalasi Python Lengkap yang sudah terpasang di mesin.

    PENTING (janji keamanan): fungsi ini HANYA mencari lokasi berkas.
    Tidak ada unduhan installer, tidak ada `msiexec`, tidak ada pemasangan
    senyap apa pun. Rilis awal memasang Python diam-diam demi Tcl/Tk dan
    itu merusak instalasi Python pengguna — cara itu dihapus permanen.
    """
    return cari_python_lengkap()


def cari_python_lengkap():
    """Cari instalasi Python Lengkap (bertcltk) yang sudah ada di mesin."""
    kandidat = []
    for akar in (sys.base_prefix, sys.prefix, *KANDIDAT_PYTHON_LENGKAP):
        if not akar or not os.path.isdir(akar):
            continue
        if os.path.normcase(akar) not in {os.path.normcase(k) for k in kandidat}:
            kandidat.append(akar)

    for akar in kandidat:
        if _lengkap_bertcltk(akar):
            return akar

    raise SystemExit(
        "GAGAL: Tcl/Tk 8.6 tidak ditemukan.\n"
        "Build membutuhkan instalasi Python Lengkap (dari python.org, "
        "komponen tcltk ikut terpasang) yang SUDAH ada di mesin, misalnya "
        "C:\\Python310 — atau jalankan build dengan Python lengkap.\n"
        "Skrip ini TIDAK akan memasang atau mengunduh pemasang apa pun."
    )


def _lengkap_bertcltk(akar):
    """True bila `akar` berisi Python Lengkap lengkap dengan Tcl/Tk."""
    data_tk = os.path.join(akar, FOLDER_TK_DATA)
    if not (os.path.isdir(os.path.join(data_tk, "tcl8.6")) and
            os.path.isdir(os.path.join(data_tk, "tk8.6"))):
        return False
    if not os.path.isfile(os.path.join(akar, "DLLs", PYD_TK)):
        return False
    return all(_cari_berkas(akar, nama) for nama in BERKAS_TK)


def _cari_berkas(akar, nama):
    """Cari berkas di folder akar atau di subfolder DLLs (layout tiap versi)."""
    for p in (os.path.join(akar, "DLLs", nama), os.path.join(akar, nama)):
        if os.path.isfile(p):
            return p
    return None


def salin_tcltk(sumber):
    """Salin Tcl/Tk dari instalasi Python lengkap ke runtime portabel.

    Sumber boleh berupa layout akar (tcl86t.dll di root) atau layout
    DLLs\\ (Python 3.10.11) — keduanya dicari otomatis oleh _cari_berkas().
    """
    for nama in BERKAS_TK:
        asal = _cari_berkas(sumber, nama)
        if not asal:
            raise SystemExit(f"GAGAL: {nama} tidak ditemukan di {sumber}.")
        shutil.copy2(asal, os.path.join(FOLDER_RUNTIME, nama))

    asal_pyd = _cari_berkas(sumber, PYD_TK)
    if not asal_pyd:
        raise SystemExit(f"GAGAL: {PYD_TK} tidak ditemukan di {sumber}.")
    shutil.copy2(asal_pyd, os.path.join(FOLDER_RUNTIME, PYD_TK))

    sumber_data = os.path.join(sumber, FOLDER_TK_DATA)
    for nama in os.listdir(sumber_data):
        asal = os.path.join(sumber_data, nama)
        tujuan = os.path.join(FOLDER_RUNTIME, nama)
        if os.path.isdir(asal):
            shutil.copytree(asal, tujuan, dirs_exist_ok=True)
        else:
            shutil.copy2(asal, tujuan)

    # Paket Python-nya (Lib\tkinter) — Python portable TIDAK menyertakannya,
    # padahal tanpa ini `import tkinter` tetap gagal walau DLL sudah ada.
    sumber_pkg = os.path.join(sumber, "Lib", "tkinter")
    if not os.path.isdir(sumber_pkg):
        raise SystemExit(f"GAGAL: Lib\\tkinter tidak ditemukan di {sumber}.")
    shutil.copytree(sumber_pkg, os.path.join(FOLDER_RUNTIME, "Lib", "tkinter"),
                    dirs_exist_ok=True)
    catat("Tcl/Tk 8.6 + paket Lib\\tkinter disalin -> jendela UI siap dipakai.")


def uji_tkinter():
    """Uji bahwa tkinter benar-benar bisa membangun jendela di runtime.

    Tcl di Windows tidak menelusuri folder python.exe, maka lokasi data
    tcl8.6/tk8.6 diberitahukan lewat env TCL_LIBRARY/TK_LIBRARY — sama
    persis dengan yang dilakukan connector_app._buat_jendela() saat aplikasi
    berjalan pada akhirnya.
    """
    env = dict(os.environ)
    for kunci, folder in (("TCL_LIBRARY", "tcl8.6"), ("TK_LIBRARY", "tk8.6")):
        jalur = os.path.join(FOLDER_RUNTIME, folder)
        if os.path.isdir(jalur):
            env[kunci] = jalur
    keluar = subprocess.run(
        [os.path.join(FOLDER_RUNTIME, "python.exe"), "-c",
         "import tkinter; r = tkinter.Tk(); r.withdraw(); "
         "print('TK', tkinter.TkVersion); r.destroy()"],
        capture_output=True, text=True, env=env)
    if keluar.returncode != 0 or "TK" not in (keluar.stdout or ""):
        raise SystemExit("GAGAL: tkinter tidak berfungsi di runtime portabel.\n"
                         + (keluar.stderr or ""))
    catat(f"Uji tkinter lulus ({keluar.stdout.strip()}).")


# ---- Uji paket terhadap kondisi MESIN PENGGUNA (bukan mesin build) ----
BERKAS_UJI_MODUL = "uji_modul_bersih.py"
DAFTAR_MODUL_UJI = [
    # Pustaka pihak ketiga yang wajib ikut terkemas
    "serial", "pystray", "PIL", "tkinter",
    "pyautogui", "pycaw", "comtypes",
    # Modul aplikasi. Kegagalan `aksi` = konektor tak bisa start sama sekali
    # karena connector_app.py melakukan `from aksi import ...` di tingkat modul.
    "versi", "bridge_fase2a", "aksi", "ui_jendela", "updater",
]


def uji_modul_mesin_bersih():
    """Uji SEMUA modul dalam mode mesin pengguna BERSIH.

    PYTHONNOUSERSITE=1 mematikan site-packages milik pengguna, sehingga
    runtime hanya boleh mengandalkan isinya sendiri. TANPA flag ini uji
    bisa LOLOS PALSU: `import site` pada python310._pth membuat runtime
    portabel ikut membaca instalasi Python milik mesin build (terbukti
    mengambil comtypes dari %APPDATA%\\Roaming\\Python), padahal di mesin
    pengguna yang tidak punya Python pustaka itu tidak ada.

    Kondisi persis inilah yang menyembunyikan hilangnya pyautogui sampai
    tiga rilis penuh (1.0.0, 1.0.1, 1.0.2) gagal start. Tanpa uji ini
    kesalahan yang sama akan terulang dan baru ketahuan saat sudah sampai
    ke tangan pengguna.
    """
    os.makedirs(FOLDER_BUILD, exist_ok=True)
    berkas = os.path.join(FOLDER_BUILD, BERKAS_UJI_MODUL)
    kode = (
        "import importlib, sys\n"
        f"sys.path.insert(0, {os.path.join(FOLDER_RUNTIME, 'app')!r})\n"
        "gagal = []\n"
        f"for nama in {DAFTAR_MODUL_UJI!r}:\n"
        "    try:\n"
        "        importlib.import_module(nama)\n"
        "    except Exception as e:\n"
        "        gagal.append('%s -> %s: %s' % (nama, type(e).__name__, e))\n"
        "if gagal:\n"
        "    print('\\n'.join(gagal))\n"
        "    raise SystemExit(1)\n"
        f"print('OK: {len(DAFTAR_MODUL_UJI)} modul terimpor')\n"
    )
    with open(berkas, "w", encoding="utf-8") as f:
        f.write(kode)

    env = dict(os.environ)
    env["PYTHONNOUSERSITE"] = "1"
    for kunci, folder in (("TCL_LIBRARY", "tcl8.6"), ("TK_LIBRARY", "tk8.6")):
        jalur = os.path.join(FOLDER_RUNTIME, folder)
        if os.path.isdir(jalur):
            env[kunci] = jalur

    keluar = subprocess.run([os.path.join(FOLDER_RUNTIME, "python.exe"), berkas],
                            capture_output=True, text=True, env=env)
    if keluar.returncode != 0:
        raise SystemExit(
            "GAGAL: paket belum siap untuk mesin pengguna TANPA Python.\n"
            "Modul yang tidak tersedia pada runtime:\n"
            + (keluar.stdout or "") + (keluar.stderr or ""))
    catat(f"Uji mesin bersih lulus ({keluar.stdout.strip()}).")


def siapkan_runtime(zip_python):
    if os.path.isdir(FOLDER_RUNTIME):
        shutil.rmtree(FOLDER_RUNTIME, ignore_errors=True)
    os.makedirs(FOLDER_RUNTIME, exist_ok=True)
    catat("Ekstrak Python portable...")
    with zipfile.ZipFile(zip_python) as z:
        z.extractall(FOLDER_RUNTIME)

    # Aktifkan site-packages pada file ._pth (embeddable mematikan site by default)
    # "Lib" ditambahkan agar paket Lib\tkinter (jendela UI) bisa diimpor.
    pth = os.path.join(FOLDER_RUNTIME, "python310._pth")
    baris = ["python310.zip", ".", "Lib", "Lib\\site-packages", "app",
             "import site", ""]
    with open(pth, "w", encoding="utf-8") as f:
        f.write("\n".join(baris))

    # Ambil dependensi pakai Python build (lebih sederhana daripada get-pip).
    # `--target` menaruh pustaka ke folder runtime, TIDAK ke instalasi Python
    # mesin build — instalasi Python pengguna tidak pernah disentuh.
    target = os.path.join(FOLDER_RUNTIME, "Lib", "site-packages")
    os.makedirs(target, exist_ok=True)
    pustaka = baca_requirements()
    catat("Mengambil dependensi: " + ", ".join(pustaka) + " ...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--target", target,
         "--quiet", "--no-warn-script-location", "-r", BERKAS_REQUIREMENTS],
        check=True,
    )

    # Tcl/Tk supaya jendela UI (tkinter) bisa jalan di Python portabel
    salin_tcltk(siapkan_tcltk())

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
    uji_tkinter()                      # pastikan jendela UI bisa dibangun
    # WAJIB terakhir: pastikan paket lengkap untuk mesin TANPA Python.
    # Tanpa langkah ini paket yang kurang pustaka tetap lolos build dan
    # baru ketahuan saat pengguna mencoba menjalankannya.
    uji_modul_mesin_bersih()

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
