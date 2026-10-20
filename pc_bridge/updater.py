# ============================================================
# HALODECK - Pembaruan Otomatis (PC)
# File: updater.py
# Tugas : Memeriksa, mengunduh, dan memasang pembaruan aplikasi PC
#         dari GitHub Releases.
#         - Repo rilis DIISI DI update_config.json (bisa beda dgn
#           repo sumber, dan TERPISAH dari repo update ESP).
#         - Hanya pustaka bawaan Python (urllib, zipfile, hashlib)
#           -> tidak perlu pip install apa pun.
#         - Aman: cadangan .py lama dulu, verifikasi checksum,
#           tolak paket yang tidak lebih baru / struktur aneh.
# Komentar dalam Bahasa Indonesia
# ============================================================

import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
import time
import zipfile
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from versi import VERSI as VERSI_LOKAL

# ---------- LOKASI & BATAS ----------
FOLDER_INI = os.path.dirname(os.path.abspath(__file__))
BERKAS_CONFIG = os.path.join(FOLDER_INI, "update_config.json")
FOLDER_CADANGAN = os.path.join(FOLDER_INI, "_cadangan")
BERKAS_VERSI = "versi.py"

GITHUB_API = "https://api.github.com"
USER_AGENT = "HaloDeck-Updater"
TUNDA_CEK_PERTAMA = 20        # detik: cek pertama setelah aplikasi menyala
INTERVAL_CEK_OTOMATIS = 24 * 3600   # detik: 24 jam sekali
BATAS_CADANGAN = 5            # jumlah cadangan .py yang disimpan
UKURAN_BLOK = 64 * 1024

# Berkas lokal yang TIDAK BOLEH ditimpa paket update
BERKAS_TERLARANG = {"update_config.json", "konektor.log", "konektor.lock"}

# Konfigurasi bawaan (dibaca dari update_config.json bila ada)
CONFIG_BAWAAN = {
    "repo": "",                     # contoh: "namapengguna/HaloDeck"
    "prefiks_aset": "halodeck-win",  # aset rilis yg dipakai, mis. "HaloDeck-Win-1.1.0.zip"
    "cek_otomatis": True,           # cek rilis tiap 24 jam
    "pasang_otomatis": False,       # True = langsung pasang tanpa konfirmasi
}

# Sambungan ke pencatat log & pemberitahuan aplikasi induk
PENGIKAT = {"pencatat": None}


class GalatUpdate(Exception):
    """Galat pembaruan yang pesannya aman ditampilkan ke pengguna."""


# ============================================================
# LOG (memakai catat() milik connector_app bila sudah tersambung)
# ============================================================
def _log(pesan):
    fn = PENGIKAT.get("pencatat")
    if fn is not None:
        try:
            fn(f"[update] {pesan}")
            return
        except Exception:
            pass
    try:
        baris = f"{datetime.now():%Y-%m-%d %H:%M:%S}  [update] {pesan}\n"
        with open(os.path.join(FOLDER_INI, "konektor.log"), "a", encoding="utf-8") as f:
            f.write(baris)
    except Exception:
        pass


def sambungkan_log(fn):
    PENGIKAT["pencatat"] = fn


# ============================================================
# KONFIGURASI (update_config.json)
# ============================================================
def muat_config():
    """Baca update_config.json; bila belum ada, tulis versi bawaan."""
    cfg = dict(CONFIG_BAWAAN)
    try:
        with open(BERKAS_CONFIG, "r", encoding="utf-8") as f:
            isi = json.load(f)
        if isinstance(isi, dict):
            for kunci in CONFIG_BAWAAN:
                if kunci in isi:
                    cfg[kunci] = isi[kunci]
    except FileNotFoundError:
        simpan_config(cfg)
    except Exception as galat:
        _log(f"update_config.json tidak terbaca ({galat}) -> memakai bawaan")
    return cfg


def simpan_config(cfg):
    try:
        with open(BERKAS_CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except Exception as galat:
        _log(f"Gagal menyimpan update_config.json: {galat}")


# ============================================================
# BANDINGKAN VERSI (MAJU.MINOR.PATCH, awalan "v" boleh)
# Catatan: sufiks pratinjau (1.1.0-beta) dianggap 1.1.0.
# ============================================================
def ke_tupel(teks):
    teks = str(teks or "").strip().lstrip("vV")
    teks = teks.split("+", 1)[0].split("-", 1)[0].split("/", 1)[-1]
    angka = []
    for bagian in teks.split("."):
        try:
            angka.append(int(re.sub(r"\D", "", bagian) or 0))
        except ValueError:
            angka.append(0)
    while len(angka) < 3:
        angka.append(0)
    return tuple(angka[:3])


def versi_lebih_baru(a, b):
    """True bila versi a lebih baru dari versi b."""
    return ke_tupel(a) > ke_tupel(b)


def baca_versi_lokal():
    return _baca_versi(FOLDER_INI) or VERSI_LOKAL


def _baca_versi(folder):
    """Ambil nilai VERSI dari folder.py hasil ekstrak paket (atau lokal)."""
    try:
        with open(os.path.join(folder, BERKAS_VERSI), "r", encoding="utf-8") as f:
            isi = f.read()
        cocok = re.search(r'^\s*VERSI\s*=\s*[\'"]([^\'"]+)[\'"]', isi, re.M)
        return cocok.group(1) if cocok else None
    except Exception:
        return None


# ============================================================
# HTTP (GitHub API)
# ============================================================
def _minta_json(url, timeout=20):
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            mentah = resp.read()
    except HTTPError as galat:
        if galat.code == 403:
            raise GalatUpdate("GitHub menolak permintaan (kemungkinan batas "
                              "60 permintaan/jam tanpa token). Coba lagi nanti.")
        if galat.code == 404:
            raise GalatUpdate("Repo rilis tidak ditemukan (404) — periksa "
                              "nilai 'repo' di update_config.json.")
        raise GalatUpdate(f"Galat HTTP {galat.code} saat menghubungi GitHub.")
    except URLError:
        raise GalatUpdate("Tidak bisa menghubungi GitHub (internet mati / "
                          "sedang offline).")
    try:
        return json.loads(mentah.decode("utf-8"))
    except Exception:
        raise GalatUpdate("Balasan GitHub bukan JSON yang sah.")


def _pilih_aset(daftar_zip, prefiks):
    if not daftar_zip:
        raise GalatUpdate("Rilis terbaru tidak memiliki asset .zip.")
    if prefiks:
        kunci = str(prefiks).lower()
        for aset in daftar_zip:
            if kunci in aset["nama"].lower():
                return aset
    return daftar_zip[0]


def cek_rilis(cfg=None):
    """Ambil rilis terbaru. Mengembalikan dict, atau melempar GalatUpdate."""
    cfg = cfg or muat_config()
    repo = str(cfg.get("repo") or "").strip().strip("/")
    if not repo:
        raise GalatUpdate("Repo rilis belum dikonfigurasi — isi kolom 'repo' "
                          "di update_config.json (contoh: user/HaloDeck).")

    rilis = _minta_json(f"{GITHUB_API}/repos/{repo}/releases/latest")
    tag = str(rilis.get("tag_name") or rilis.get("name") or "").strip()
    if not tag:
        raise GalatUpdate("Rilis terbaru tidak memiliki tag versi.")

    daftar = []
    for aset in rilis.get("assets") or []:
        nama = aset.get("name") or ""
        if not nama.lower().endswith(".zip"):
            continue
        daftar.append({
            "nama": nama,
            "url": aset.get("browser_download_url"),
            "ukuran": int(aset.get("size") or 0),
            "digest": aset.get("digest"),
        })
    if not daftar:
        raise GalatUpdate("Rilis terbaru belum menyertakan paket .zip PC.")

    aset = _pilih_aset(daftar, cfg.get("prefiks_aset", ""))
    if not aset["url"]:
        raise GalatUpdate("Asset rilis tidak punya URL unduhan.")

    return {
        "repo": repo,
        "versi": tag,
        "nama": rilis.get("name") or tag,
        "catatan": rilis.get("body") or "",
        "tanggal": rilis.get("published_at") or "",
        "url_rilis": rilis.get("html_url") or "",
        "aset": aset,
        "daftar_aset": daftar,
    }


# ============================================================
# UNDUH + VERIFIKASI CHECKSUM
# ============================================================
def unduh_aset(aset, tujuan, on_progres=None):
    req = Request(aset["url"], headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=120) as resp, open(tujuan, "wb") as f:
            total = int(aset.get("ukuran") or 0)
            jumlah = 0
            terakhir = 0.0
            while True:
                blok = resp.read(UKURAN_BLOK)
                if not blok:
                    break
                f.write(blok)
                jumlah += len(blok)
                if on_progres and time.time() - terakhir >= 1.0:
                    terakhir = time.time()
                    on_progres(jumlah, total)
            if on_progres:
                on_progres(jumlah, total)
    except (HTTPError, URLError, OSError) as galat:
        try:
            os.remove(tujuan)
        except OSError:
            pass
        raise GalatUpdate(f"Gagal mengunduh paket: {galat}")

    if aset.get("ukuran") and os.path.getsize(tujuan) != aset["ukuran"]:
        raise GalatUpdate("Ukuran paket terunduh tidak cocok — unduhan "
                          "kemungkinan terpotong, coba lagi.")
    return tujuan


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            blok = f.read(UKURAN_BLOK)
            if not blok:
                break
            h.update(blok)
    return h.hexdigest()


def _hash_dari_teks(teks):
    cocok = re.search(r"\b([0-9a-fA-F]{64})\b", teks or "")
    return cocok.group(1).lower() if cocok else None


def periksa_integritas(path, aset, rilis):
    """Cocokkan SHA-256 paket dgn 'digest' GitHub atau asset .sha256.

    Mengembalikan (True, pesan) bila cocok / tidak ada checksum,
    melempar GalatUpdate bila checksum ADA tapi TIDAK cocok.
    """
    harap = None
    digest = aset.get("digest")
    if isinstance(digest, str) and digest.lower().startswith("sha256:"):
        harap = digest.split(":", 1)[1].strip().lower()

    if not harap:
        # Cari asset pendamping "...zip.sha256"
        nama = aset["nama"].lower()
        for kandidat in rilis.get("daftar_aset", []):
            if kandidat["nama"].lower().endswith(".sha256") and \
               nama in kandidat["nama"].lower():
                req = Request(kandidat["url"], headers={"User-Agent": USER_AGENT})
                try:
                    with urlopen(req, timeout=30) as resp:
                        harap = _hash_dari_teks(resp.read().decode("utf-8", "replace"))
                except Exception:
                    harap = None
                break

    if not harap:
        return True, "Rilis tidak menyertakan checksum — verifikasi dilewati."

    nyata = _sha256(path)
    if nyata != harap:
        raise GalatUpdate("Checksum (SHA-256) tidak cocok — paket ditolak "
                          "karena rusak atau tidak sesuai rilis.")
    return True, "Checksum SHA-256 cocok."


# ============================================================
# CADANGAN BERKAS LAMA
# ============================================================
def _bersihkan_nama(teks):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(teks)).strip("-") or "tanpa-versi"


def cadangkan():
    """Zip seluruh .py lokal ke _cadangan/, sisakan BATAS_CADANGAN terbaru."""
    os.makedirs(FOLDER_CADANGAN, exist_ok=True)
    nama = f"cadangan-{_bersihkan_nama(baca_versi_lokal())}-{datetime.now():%Y%m%d-%H%M%S}.zip"
    tujuan = os.path.join(FOLDER_CADANGAN, nama)
    with zipfile.ZipFile(tujuan, "w", zipfile.ZIP_DEFLATED) as z:
        for akar, folder, berkas in os.walk(FOLDER_INI):
            folder[:] = [d for d in folder if d not in ("__pycache__", "_cadangan")]
            for b in berkas:
                if b.endswith(".py"):
                    penuh = os.path.join(akar, b)
                    z.write(penuh, os.path.relpath(penuh, FOLDER_INI))

    isi = sorted(
        (os.path.join(FOLDER_CADANGAN, n) for n in os.listdir(FOLDER_CADANGAN)
         if n.endswith(".zip")),
        key=os.path.getmtime,
    )
    for lama in isi[:-BATAS_CADANGAN]:
        try:
            os.remove(lama)
        except OSError:
            pass
    return tujuan


# ============================================================
# PASANG PAKET (ekstrak -> timpa .py)
# ============================================================
def _cari_payload(akar):
    """Cari folder di dalam zip yang berisi connector_app.py."""
    for akar2, _, berkas in os.walk(akar):
        if "connector_app.py" in berkas:
            return akar2
    return None


def pasang_paket(zip_path, versi_lokal):
    """Ekstrak zip dan timpa berkas .py. Mengembalikan jumlah berkas ditimpa."""
    with tempfile.TemporaryDirectory(prefix="wgmd_ekstrak_") as tmp:
        try:
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(tmp)
        except zipfile.BadZipFile:
            raise GalatUpdate("File paket rusak / bukan zip yang sah.")

        payload = _cari_payload(tmp)
        if payload is None:
            raise GalatUpdate("Struktur paket tidak dikenal (connector_app.py "
                              "tidak ada di dalam zip) — pemasangan dibatalkan.")

        v_paket = _baca_versi(payload)
        if not v_paket:
            raise GalatUpdate(f"Paket tidak memuat {BERKAS_VERSI} — struktur "
                              "tidak dikenal, pemasangan dibatalkan.")
        if not versi_lebih_baru(v_paket, versi_lokal):
            raise GalatUpdate(f"Paket {v_paket} tidak lebih baru dari {versi_lokal} "
                              "— pemasangan dibatalkan.")

        jumlah = 0
        for akar, folder, berkas in os.walk(payload):
            folder[:] = [d for d in folder if d != "__pycache__"]
            for b in berkas:
                if b in BERKAS_TERLARANG or b.endswith((".pyc", ".log", ".lock")):
                    continue
                sumber = os.path.join(akar, b)
                relatif = os.path.relpath(sumber, payload)
                tujuan = os.path.join(FOLDER_INI, relatif)
                os.makedirs(os.path.dirname(tujuan) or FOLDER_INI, exist_ok=True)
                shutil.copy2(sumber, tujuan)
                jumlah += 1
        return jumlah, v_paket


# ============================================================
# PENGELOLA UPDATE (dipakai aplikasi tray)
# ============================================================
class PengelolaUpdate:
    def __init__(self, pencatat=None, on_status=None, on_selesai=None):
        if pencatat is not None:
            PENGIKAT["pencatat"] = pencatat
        self.on_status = on_status          # fn(dict status) -> dipanggil tiap perubahan
        self.on_selesai = on_selesai        # fn(jumlah_berkas) -> setelah pasang sukses
        self.status = {
            "ada": False,                   # ada pembaruan lebih baru?
            "versi": None,                  # versi di GitHub (bila ada)
            "pesan": "Belum diperiksa",
            "sibuk": False,                 # sedang cek/unduh/pasang
            "lokasi": "",                   # "C:\\...\\connector_app.py"
        }
        self._rilis = None
        self._kunci = threading.Lock()
        self._berhenti = threading.Event()
        self._thread = None
        self._pct_terakhir = -5

    # --- perbarui status + beritahu aplikasi induk ---
    def _set(self, **kunci):
        self.status.update(kunci)
        if self.on_status is not None:
            try:
                self.on_status(dict(self.status))
            except Exception:
                pass

    # --- mulai pengecekan berkala (thread daemon) ---
    def mulai(self):
        cfg = muat_config()
        self._set(lokasi=os.path.abspath(__file__))
        if not cfg.get("cek_otomatis", True):
            _log("Pengecekan pembaruan otomatis NONAKTIF (cek_otomatis=false).")
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="UpdateLoop")
        self._thread.start()

    def berhenti(self):
        self._berhenti.set()

    def _loop(self):
        while not self._berhenti.is_set():
            if self._berhenti.wait(TUNDA_CEK_PERTAMA):
                break
            try:
                self.cek()
                cfg = muat_config()
                if cfg.get("pasang_otomatis") and self.status.get("ada"):
                    _log("Pasang otomatis aktif -> memasang tanpa konfirmasi.")
                    self.pasang()
            except Exception as galat:
                self._set(sibuk=False, pesan=f"Gagal: {galat}")
                _log(f"Galat pengecekan berkala: {galat}")
            if self._berhenti.wait(INTERVAL_CEK_OTOMATIS):
                break

    # --- pengecekan (sinkron) ---
    def cek(self):
        with self._kunci:
            if self.status.get("sibuk"):
                return self.status
            self._set(sibuk=True, pesan="Memeriksa pembaruan...")
        try:
            cfg = muat_config()
            if not str(cfg.get("repo") or "").strip():
                pesan = "Repo rilis belum diisi (update_config.json)"
                self._set(ada=False, versi=None, pesan=pesan)
                _log(f"Pemeriksaan dilewati: {pesan}.")
                return self.status

            rilis = cek_rilis(cfg)
            self._rilis = rilis
            lokal = baca_versi_lokal()
            if versi_lebih_baru(rilis["versi"], lokal):
                self._set(ada=True, versi=rilis["versi"],
                          pesan=f"{rilis['versi']} tersedia")
                _log(f"Pembaruan TERSEDIA: {lokal} -> {rilis['versi']} "
                     f"(asset: {rilis['aset']['nama']}, "
                     f"{rilis['aset']['ukuran'] // 1024} KB).")
            else:
                self._set(ada=False, versi=rilis["versi"], pesan="Sudah terbaru")
                _log(f"Sudah versi terbaru ({lokal}).")
            return self.status
        finally:
            self._set(sibuk=False)

    def cek_async(self):
        def _jalan():
            try:
                self.cek()
            except GalatUpdate as galat:
                self._set(sibuk=False, pesan=str(galat))
                _log(f"Pemeriksaan gagal: {galat}")
            except Exception as galat:
                self._set(sibuk=False, pesan=f"Galat: {galat}")
                _log(f"Pemeriksaan gagal: {galat}")
        threading.Thread(target=_jalan, daemon=True, name="UpdateCek").start()

    # --- pemasangan (sinkron; jalankan lewat pasang_async) ---
    def pasang(self):
        folder_tmp = None
        with self._kunci:
            if self.status.get("sibuk"):
                return 0
            self._set(sibuk=True, pesan="Menyiapkan pembaruan...")
        try:
            cfg = muat_config()
            rilis = self._rilis or cek_rilis(cfg)
            self._rilis = rilis
            lokal = baca_versi_lokal()
            if not versi_lebih_baru(rilis["versi"], lokal):
                raise GalatUpdate(f"Sudah versi {lokal} — tidak ada yang dipasang.")

            folder_tmp = tempfile.mkdtemp(prefix="wgmd_update_")
            zip_path = os.path.join(folder_tmp, rilis["aset"]["nama"])

            self._pct_terakhir = -5
            self._set(pesan=f"Mengunduh {rilis['aset']['nama']}...")
            unduh_aset(rilis["aset"], zip_path, on_progres=self._progres_unduh)

            self._set(pesan="Memverifikasi checksum...")
            _, pesan_kode = periksa_integritas(zip_path, rilis["aset"], rilis)
            _log(pesan_kode)

            self._set(pesan="Membuat cadangan berkas lama...")
            cadangan = cadangkan()
            _log(f"Cadangan tersimpan: {os.path.relpath(cadangan, FOLDER_INI)}")

            self._set(pesan="Memasang paket...")
            jumlah, v_paket = pasang_paket(zip_path, lokal)
            _log(f"Pemasangan SELESAI: {lokal} -> {v_paket} "
                 f"({jumlah} berkas ditimpa).")
            self._set(ada=False, versi=None, sibuk=False,
                      pesan=f"Terpasang {v_paket}")
            if self.on_selesai is not None:
                try:
                    self.on_selesai(jumlah, v_paket)
                except Exception as galat:
                    _log(f"Galat setelah pemasangan: {galat}")
            return jumlah
        except GalatUpdate as galat:
            self._set(sibuk=False, pesan=f"Gagal: {galat}")
            _log(f"Pemasangan GAGAL: {galat}")
            raise
        except Exception as galat:
            self._set(sibuk=False, pesan=f"Gagal: {galat}")
            _log(f"Pemasangan GAGAL: {galat}")
            raise GalatUpdate(str(galat))
        finally:
            if folder_tmp:
                shutil.rmtree(folder_tmp, ignore_errors=True)

    def _progres_unduh(self, jumlah, total):
        if not total:
            return
        pct = int(jumlah * 100 / total)
        if pct - self._pct_terakhir >= 5 or pct >= 100:
            self._pct_terakhir = pct
            self._set(pesan=f"Mengunduh {pct}%  ({jumlah // 1024} KB / "
                            f"{total // 1024} KB)")

    def pasang_async(self, on_selesai=None):
        if on_selesai is not None:
            self.on_selesai = on_selesai

        def _jalan():
            try:
                self.pasang()
            except Exception:
                pass   # galat sudah dicatat & dipajang di status

        threading.Thread(target=_jalan, daemon=True, name="UpdatePasang").start()


# ============================================================
# UJI CEPAT:  python updater.py
# ============================================================
if __name__ == "__main__":
    sambungkan_log(print)
    print(f"Versi lokal : {baca_versi_lokal()}")
    print(f"Config      : {muat_config()}")
    try:
        r = cek_rilis()
        print(f"Rilis       : {r['versi']}  ({r['aset']['nama']})")
        print(f"Lebih baru ? {versi_lebih_baru(r['versi'], baca_versi_lokal())}")
    except GalatUpdate as g:
        print(f"Hasil cek   : {g}")
