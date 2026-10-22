// ============================================================
// HALODECK - MainActivity.kt (Bahasa Kotlin, tanpa library eksternal)
// Fitur:
//  1. TEMUKAN OTOMATIS: UDP discovery -> IP ESP diketahui sendiri,
//     auto-connect TCP tanpa ketik IP apa pun
//  2. AUTO-RECONNECT: koneksi putus / jaringan siap lagi ->
//     aplikasi langsung mencari & menyambung sendiri
//  3. Grid tombol MENYESUAIKAN PROFIL aktif di PC (context-switching)
//  4. Tampilan: baris status koneksi ringkas (tanpa IP), grid 3 kolom
//     ikon + nama fungsi yang dikelompokkan per fungsi
// Komentar dalam Bahasa Indonesia
// ============================================================

package com.halodeck.macropad

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.SharedPreferences
import android.graphics.PorterDuff
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import android.view.Gravity
import android.view.View
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.GridLayout
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetSocketAddress
import java.net.Socket
import java.net.SocketTimeoutException

// ============================================================
// DATA PROFIL + MAKRO (meniru pemeta di bridge PC)
// ikon  = nama berkas drawable tanpa prefiks "ic_m_"
// kelompok = judul bagian yang tampil di atas grid
// bahaya = true -> tombol diberi nuansa merah (Kunci PC, Bisukan)
// ============================================================
data class Makro(
    val kelompok: String,
    val label: String,
    val perintah: String,
    val ikon: String,
    val bahaya: Boolean = false
)

val PROFIL_MAKRO: Map<String, List<Makro>> = mapOf(
    "DEFAULT" to listOf(
        Makro("Umum", "Kunci PC",       "BTN:LOCK",     "lock",   bahaya = true),
        Makro("Umum", "Bisukan",        "BTN:MUTE",     "mute",   bahaya = true),
        Makro("Umum", "Browser",        "BTN:BROWSER",  "browser"),
        Makro("Umum", "Manajer Tugas",  "BTN:TASKMGR",  "taskmgr"),
        Makro("Umum", "Notepad",        "BTN:NOTEPAD",  "notepad"),
        Makro("Umum", "VS Code",        "BTN:VSCODE",   "vscode")
    ),
    "NOTEPAD" to listOf(
        Makro("Dokumen", "Simpan",       "BTN:SIMPAN",   "simpan"),
        Makro("Dokumen", "Dokumen Baru", "BTN:BARU",     "baru"),
        Makro("Dokumen", "Urungkan",     "BTN:UNDO",     "undo"),
        Makro("Dokumen", "Ulangi",       "BTN:REDO",     "redo"),
        Makro("Umum",    "Kunci PC",     "BTN:LOCK",     "lock",  bahaya = true),
        Makro("Umum",    "Bisukan",      "BTN:MUTE",     "mute",  bahaya = true)
    ),
    "VSCODE" to listOf(
        Makro("Dokumen", "Simpan",   "BTN:SIMPAN", "simpan"),
        Makro("Dokumen", "Urungkan", "BTN:UNDO",   "undo"),
        Makro("Dokumen", "Ulangi",   "BTN:REDO",   "redo"),
        Makro("Umum",    "Kunci PC", "BTN:LOCK",   "lock", bahaya = true),
        Makro("Umum",    "Bisukan",  "BTN:MUTE",   "mute", bahaya = true)
    ),
    "AFTEREFFECTS" to listOf(
        Makro("Dokumen", "Urungkan", "BTN:UNDO", "undo"),
        Makro("Dokumen", "Ulangi",   "BTN:REDO", "redo"),
        Makro("Umum",    "Kunci PC", "BTN:LOCK", "lock", bahaya = true),
        Makro("Umum",    "Bisukan",  "BTN:MUTE", "mute", bahaya = true)
    ),
    "ILLUSTRATOR" to listOf(
        Makro("Gambar",   "Perbesar",      "BTN:PS_ZOOMIN",  "ps_zoomin"),
        Makro("Gambar",   "Perkecil",      "BTN:PS_ZOOMOUT", "ps_zoomout"),
        Makro("Gambar",   "Pas Layar",     "BTN:PS_FIT",     "ps_fit"),
        Makro("Gambar",   "Lapisan Baru",  "BTN:PS_LAYER",   "ps_layer"),
        Makro("Dokumen",  "Simpan",        "BTN:SIMPAN",     "simpan"),
        Makro("Dokumen",  "Dokumen Baru",  "BTN:BARU",       "baru"),
        Makro("Dokumen",  "Urungkan",      "BTN:UNDO",       "undo"),
        Makro("Dokumen",  "Ulangi",        "BTN:REDO",       "redo"),
        Makro("Umum",     "Bisukan",       "BTN:MUTE",       "mute", bahaya = true)
    ),
    "PHOTOSHOP" to listOf(
        Makro("Gambar",   "Perbesar",     "BTN:PS_ZOOMIN",  "ps_zoomin"),
        Makro("Gambar",   "Perkecil",     "BTN:PS_ZOOMOUT", "ps_zoomout"),
        Makro("Gambar",   "Pas Layar",    "BTN:PS_FIT",     "ps_fit"),
        Makro("Gambar",   "Lapisan Baru", "BTN:PS_LAYER",   "ps_layer"),
        Makro("Gambar",   "Ratakan",      "BTN:PS_FLATTEN", "ps_flatten"),
        Makro("Dokumen",  "Urungkan",     "BTN:UNDO",       "undo"),
        Makro("Dokumen",  "Ulangi",       "BTN:REDO",       "redo"),
        Makro("Umum",     "Bisukan",      "BTN:MUTE",       "mute", bahaya = true)
    ),
    "PREMIERE" to listOf(
        Makro("Timeline", "Urungkan",     "BTN:PR_UNDO",    "undo"),
        Makro("Timeline", "Pangkas",      "BTN:PR_CUT",     "pr_cut"),
        Makro("Timeline", "Tandai Masuk", "BTN:PR_IN",      "pr_in"),
        Makro("Timeline", "Tandai Keluar","BTN:PR_OUT",     "pr_out"),
        Makro("Timeline", "Ekspor Frame", "BTN:PR_EXPORT",  "pr_export"),
        Makro("Dokumen",  "Simpan",       "BTN:SIMPAN",     "simpan"),
        Makro("Umum",     "Bisukan",      "BTN:MUTE",       "mute", bahaya = true),
        Makro("Umum",     "Kunci PC",     "BTN:LOCK",       "lock", bahaya = true)
    ),
    "BROWSER" to listOf(
        Makro("Tab",      "Tab Baru",       "BTN:TABBARU",    "tabbaru"),
        Makro("Tab",      "Tutup Tab",      "BTN:TUTUPTAB",   "tutuptab"),
        Makro("Tab",      "Buka Lagi",      "BTN:BUKALAGI",   "bukalagi"),
        Makro("Tab",      "Tab Berikutnya", "BTN:TABLANJUT",  "tablanjut"),
        Makro("Tab",      "Tab Sebelumnya", "BTN:TABSEBELUM", "tabsebelum"),
        Makro("Navigasi", "Muat Ulang",     "BTN:RELOAD",     "reload"),
        Makro("Navigasi", "Mundur",         "BTN:MUNDUR",     "mundur"),
        Makro("Navigasi", "Maju",           "BTN:MAJU",       "maju"),
        Makro("Utilitas", "Cari di Halaman","BTN:CARI",       "cari"),
        Makro("Utilitas", "Kolom Alamat",   "BTN:ALAMAT",     "alamat"),
        Makro("Utilitas", "Markah",         "BTN:BOOKMARK",   "bookmark"),
        Makro("Utilitas", "Riwayat",        "BTN:RIWAYAT",    "riwayat"),
        Makro("Utilitas", "Unduhan",        "BTN:UNDUHAN",    "unduhan"),
        Makro("Utilitas", "Jendela Privat", "BTN:INCOGNITO",  "incognito"),
        Makro("Utilitas", "DevTools",       "BTN:DEVTOOLS",   "devtools"),
        Makro("Umum",     "Kunci PC",       "BTN:LOCK",       "lock", bahaya = true)
    )
)


class MainActivity : Activity() {

    // --- Elemen UI ---
    private lateinit var titikStatus: View
    private lateinit var teksStatus: TextView
    private lateinit var teksProfil: TextView
    private lateinit var tombolMenu: ImageButton
    private lateinit var gridMakro: GridLayout

    // --- Penyimpanan preferensi (sambung otomatis / IP manual) ---
    private lateinit var prefs: SharedPreferences

    // --- Multicast lock untuk temuan UDP ---
    // MulticastLock WAJIB: banyak router membuang paket broadcast/multicast
    // (termasuk balasan DISCOVER dari ESP) untuk perangkat Android yang tidak
    // memegang kunci ini. Tanpa ini ESP tidak akan pernah ditemukan.
    private lateinit var wifiManager: WifiManager
    private lateinit var multicastLock: WifiManager.MulticastLock

    // --- Status koneksi ---
    @Volatile private var socket: Socket? = null
    @Volatile private var penulis: OutputStreamWriter? = null
    @Volatile private var terhubung = false
    @Volatile private var pencarianAktif = false
    // Nomor generasi koneksi. Setiap socket baru bernomor naik. Pembaca dari
    // socket LAMA tak boleh menyentuh status/connect lagi — kalau tidak,
    // ia menutup koneksi baru (lihat sambungTcp) dan memicu loop konek-putus.
    @Volatile private var generasi = 0
    // Cegat agar hanya ADA SATU reconnect berjalan pada satu waktu
    @Volatile private var sedangReconnect = false
    // Waktu (elapsedRealtime) saat TERAKHIR menerima data dari ESP.
    // Patokan hidup-matinya koneksi. Penting: bila jalur putus diam-diam
    // (daya ESP hilang, AP restart), tidak ada FIN/RST yang sampai sehingga
    // readLine() memblokir selamanya TANPA exception. Tanpa patokan waktu ini
    // aplikasi akan buta selamanya terhadap koneksi yang sudah mati.
    @Volatile private var terakhirBalasan = 0L
    // Nomor generasi PENCARIAN (berbeda dari generasi koneksi).
    // Thread pencarian berhenti otomatis bila nomornya berubah, sehingga
    // "Cari ulang sekarang" tidak membuat dua thread pencarian berjalan
    // bersamaan (yang lama masih berputar di while (!terhubung)).
    @Volatile private var generasiPencarian = 0
    private var profilSekarang = "DEFAULT"
    private var ipTersimpan = ""          // IP hasil temuan otomatis

    // --- SLIDER VOLUME (satu baris penuh di kelompok "Umum") ---
    // Disimpan sebagai referensi lemah-nullable karena barisnya dibuat ulang
    // tiap kali grid disusun mengikuti profil baru. Bila null, perubahan
    // volume dari PC cukup dicatat ke variabel di bawah dan diterapkan saat
    // barisnya dibuat berikutnya.
    private var sliderVolume: SeekBar? = null
    private var labelVolume: TextView? = null
    // Volume PC yang diketahui terakhir (0-100), atau -1 bila belum pernah
    // menerima apa pun. Nilai awal ini dipakai supaya slider tidak lompat
    // ke posisi 0% saat barisnya baru dibuat.
    @Volatile private var volumeTerkini = -1
    // PENJAGA ANTI-UMPAN-BALIK: saat slider digeser pengguna, nilai dikirim
    // ke PC. PC lalu mendorong balik nilai yang sama (hasil polling volume).
    // Tanpa penanda ini, penerimaan dorongan itu akan mengubah progress,
    // memicu onProgressChanged, dan mengirim VOL: lagi -- terjadilah loop
    // saling memantul yang membanjiri ESP. Cukup satu flag untuk memutusnya.
    @Volatile private var sedangSetVolume = false
    // Nilai terakhir yang benar-benar dikirim pengguna. Dipakai agar geseran
    // ke posisi yang SAMA dengan nilai PC tidak mengirim ulang perintah yang
    // tidak perlu (dan tidak memicu pantulan).
    private var volumeTerkirim = -1
    // Waktu (elapsedRealtime) saat terakhir VOL: benar-benar dikirim. Dasar
    // throttle: geser cepat memicu onProgressChanged puluhan kali per detik,
    // dan tanpa jeda tiap panggilan akan membangun satu thread baru.
    private var waktuKirimVolume = 0L

    private lateinit var cm: ConnectivityManager
    val uiHandler = Handler(Looper.getMainLooper())

    companion object {
        private const val TAG = "HaloDeck"
        // Heartbeat PING ke ESP. Disamakan dengan INTERVAL_PING pada
        // konektor PC (5 detik) agar beban ke ESP seimbang dan konsisten.
        private const val INTERVAL_HEARTBEAT_MS = 5000L
        // soTimeout pembaca: pembaca TERBANGUN tiap 3 detik walau tidak ada
        // data, sehingga tidak bisa memblokir selamanya pada socket mati.
        private const val TIMEOUT_BACA_MS = 3000
        // Bila senyap lebih lama dari ini (2x heartbeat terlewat), koneksi
        // dianggap mati. Memberi toleransi agar tidak salah deteksi saat
        // jaringan sedang sibuk.
        private const val BATAS_SEPI_MS = 12000L

        // --- Tombol menu limpahan ⋮ ---
        private const val MENU_OTOMATIS = 1
        private const val MENU_CARI     = 2
        private const val MENU_IP       = 3
        private const val MENU_PUTUS    = 4

        private const val KUNCI_OTOMATIS = "sambung_otomatis"

        // Jeda minimum antar kirim "VOL:" selama slider digeser. 90 ms cukup
        // membuat volume terasa mengalir mengikuti jari, tanpa membanjiri
        // ESP (yang meneruskan tiap baris ke PC) dengan puluhan perintah tiap
        // detik. Nilai yang terlewat tidak masalah: nilai berikutnya, dan
        // terutama nilai akhir saat jari diangkat, akan menyusul.
        private const val INTERVAL_KIRIM_VOLUME_MS = 90L

        // Nama kelompok tempat slider volume menempel. Harus sama persis
        // dengan teks kelompok pada PROFIL_MAKRO di atas.
        private const val KELOMPOK_UMUM = "Umum"

        // Opasitas tombol saat ESP belum tersambung. Masih cukup terlihat
        // agar jelas ini tombol, tapi cukup redup agar tidak disangka aktif.
        private const val REDUP_GRID = 0.35f
    }

    // ============================================================
    // LIFECYCLE
    // ============================================================
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        titikStatus = findViewById(R.id.titik_status)
        teksStatus = findViewById(R.id.teks_status)
        teksProfil = findViewById(R.id.teks_profil)
        tombolMenu = findViewById(R.id.tombol_menu)
        gridMakro  = findViewById(R.id.grid_makro)

        prefs = getSharedPreferences("halodeck", Context.MODE_PRIVATE)

        cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager

        // --- Siapkan kunci multicast untuk temuan UDP ---
        // Android membuang paket multicast/broadcast dari Wi-Fi saat driver
        // hemat daya, kecuali aplikasi memegang MulticastLock. Tanpa ini
        // balasan DISCOVER dari ESP8266 sering tidak pernah sampai.
        wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        multicastLock = wifiManager.createMulticastLock("HaloDeckDiscovery").apply {
            setReferenceCounted(false)   // acquire() sekali cukup
        }
        try {
            multicastLock.acquire()
        } catch (e: Exception) {
            // Izin CHANGE_WIFI_MULTICAST_STATE tidak ada -> temuan UDP
            // tetap dicoba, hanya peluangnya lebih kecil
            Log.w(TAG, "MulticastLock tidak bisa dipegang: ${e.message}")
        }

        bangunGridMakro(profilSekarang)

        // --- Tombol limpahan ⋮ ---
        tombolMenu.setOnClickListener { tampilkanMenu(it) }

        // --- MULAI PENCARIAN OTOMATIS saat aplikasi dibuka ---
        if (prefs.getBoolean(KUNCI_OTOMATIS, true)) {
            mulaiPencarian()
        } else {
            perbaruiStatus(R.color.teks_redup, getString(R.string.status_terputus))
        }

        // --- Pantau jaringan: Wi-Fi siap -> langsung cari & sambung ---
        pantauJaringan()
    }

    override fun onDestroy() {
        super.onDestroy()
        putusKoneksi()
        // Lepas kunci multicast agar Wi-Fi bisa kembali hemat daya
        try {
            if (multicastLock.isHeld) multicastLock.release()
        } catch (_: Exception) {}
    }

    // ============================================================
    // TAMPILAN ATAS: status koneksi, profil aktif, menu ⋮
    // ============================================================
    // Satu-satunya tempat mengubah baris status. Warna titik dan teks
    // selalu diganti berpasangan supaya tidak pernah tidak sinkron.
    private fun perbaruiStatus(warnaRes: Int, teks: String) {
        uiHandler.post {
            titikStatus.background.setTint(getColor(warnaRes))
            teksStatus.text = teks
        }
    }

    private fun tampilkanMenu(panduan: View) {
        val popup = PopupMenu(this, panduan)
        val menu = popup.menu
        val otomatis = prefs.getBoolean(KUNCI_OTOMATIS, true)

        val itemOtomatis = menu.add(0, MENU_OTOMATIS, 0, getString(R.string.menu_sambung_otomatis))
        itemOtomatis.isCheckable = true
        itemOtomatis.isChecked = otomatis
        menu.add(0, MENU_CARI, 0, getString(R.string.menu_cari_ulang))
        menu.add(0, MENU_IP, 0, getString(R.string.menu_ubah_ip))
        menu.add(0, MENU_PUTUS, 0, getString(R.string.menu_putuskan))

        // Item yang tidak relevan diredupkan, bukan disembunyikan --
        // posisinya tetap supaya menu tidak "melompat" antar keadaan.
        menu.findItem(MENU_PUTUS).isEnabled = terhubung
        menu.findItem(MENU_IP).isEnabled = !terhubung

        popup.setOnMenuItemClickListener { item ->
            when (item.itemId) {
                MENU_OTOMATIS -> {
                    // Menyalakan -> langsung cari; mematikan -> putus.
                    prefs.edit().putBoolean(KUNCI_OTOMATIS, !otomatis).apply()
                    if (otomatis) {
                        putusKoneksiManual()
                    } else {
                        mulaiPencarian()
                    }
                    true
                }
                MENU_CARI -> {
                    putusKoneksi()
                    mulaiPencarian()
                    true
                }
                MENU_IP -> {
                    bukaDialogIp()
                    true
                }
                MENU_PUTUS -> {
                    putusKoneksiManual()
                    true
                }
                else -> false
            }
        }
        popup.show()
    }

    // IP manual hanya untuk kasus jarang: jaringan tempat ESP dan HP
    // dipisah bridge/VPN sehingga siaran broadcast tidak sampai.
    private fun bukaDialogIp() {
        val lapik = FrameLayout(this)
        val masukan = EditText(this).apply {
            hint = getString(R.string.hint_ip)
            setText(ipTersimpan)
            inputType = android.text.InputType.TYPE_CLASS_TEXT
        }
        val lp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { setMargins(48, 16, 48, 0) }
        masukan.layoutParams = lp
        lapik.addView(masukan)

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.judul_dialog_ip))
            .setMessage(getString(R.string.pesan_dialog_ip))
            .setView(lapik)
            .setPositiveButton(getString(R.string.tombol_simpan)) { _, _ ->
                val ip = masukan.text.toString().trim()
                if (ip.isNotEmpty()) {
                    putusKoneksi()
                    prefs.edit().putBoolean(KUNCI_OTOMATIS, true).apply()
                    Thread {
                        if (sambungTcp(ip)) return@Thread
                        perbaruiStatus(
                            R.color.aksen_merah,
                            "Tidak bisa menyambung ke $ip"
                        )
                    }.start()
                } else {
                    prefs.edit().putBoolean(KUNCI_OTOMATIS, true).apply()
                    mulaiPencarian()
                }
            }
            .setNegativeButton(getString(R.string.tombol_batal), null)
            .show()
    }

    // ============================================================
    // PANTAU JARINGAN (auto-reconnect saat Wi-Fi siap kembali)
    // ============================================================
    private fun pantauJaringan() {
        try {
            val permintaan = NetworkRequest.Builder()
                .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                .build()
            cm.registerNetworkCallback(permintaan, object : ConnectivityManager.NetworkCallback() {
                override fun onAvailable(network: Network) {
                    // Jaringan Wi-Fi tersedia -> kalau otomatis aktif dan belum
                    // tersambung, cari ESP
                    if (!terhubung && prefs.getBoolean(KUNCI_OTOMATIS, true)) {
                        mulaiPencarian()
                    }
                }
            })
        } catch (e: SecurityException) {
            // Izin ACCESS_NETWORK_STATE tidak ada -> fitur auto-reconnect
            // nonaktif, tapi aplikasi TETAP jalan normal
            Log.w(TAG, "Pantau jaringan nonaktif: ${e.message}")
        }
    }

    // ============================================================
    // TEMUKAN OTOMATIS: UDP discovery -> auto-connect TCP
    // ============================================================
    private fun mulaiPencarian() {
        if (pencarianAktif || terhubung) return
        pencarianAktif = true
        perbaruiStatus(R.color.aksen_kuning, getString(R.string.status_mencari))
        perbaruiRedupGrid()

        // Catat nomor generasi saat thread ini mulai. Bila nomornya berubah
        // (mis. pengguna menekan "Cari ulang sekarang"), thread ini berhenti
        // dan membiarkan thread pencarian yang baru bekerja.
        val milik = generasiPencarian

        Thread {
            try {
                while (!terhubung && generasiPencarian == milik) {
                    val ip = temukanIpEsp()
                    if (generasiPencarian != milik) break   // sudah digantikan
                    if (ip != null && !terhubung) {
                        if (sambungTcp(ip)) break
                    }
                    // Coba lagi 2 detik kemudian (terus mencari otomatis)
                    Thread.sleep(2000)
                }
            } catch (_: InterruptedException) {
                // Thread dihentikan, abaikan
            } catch (e: Exception) {
                // Error tak terduga jangan sampai bikin crash
                Log.e(TAG, "Gagal saat mencari ESP", e)
            } finally {
                pencarianAktif = false
            }
        }.start()
    }

    // Broadcast "DISCOVER" -> ESP membalas "HALODECK:STA:<IP>"
    private fun temukanIpEsp(): String? {
        var jawaban: String? = null
        try {
            DatagramSocket().use { sock ->
                sock.broadcast = true
                sock.soTimeout = 1500   // Tunggu balasan maksimal 1.5 detik
                val pesan = "DISCOVER".toByteArray()
                val alamat = InetSocketAddress("255.255.255.255", 8081)
                sock.send(DatagramPacket(pesan, pesan.size, alamat))

                val buffer = ByteArray(256)
                // Terus dengarkan sampai timeout — jangan berhenti di paket
                // pertama, karena bisa jadi paket itu dari perangkat lain.
                val batasWaktu = System.currentTimeMillis() + 1500
                while (System.currentTimeMillis() < batasWaktu && jawaban == null) {
                    val paket = DatagramPacket(buffer, buffer.size)
                    try {
                        sock.receive(paket)
                        val isi = String(paket.data, 0, paket.length).trim()
                        // Format: HALODECK:<MODE>:<IP> (firmware v1.0.2+)
                        //      atau MACROPAD:<MODE>:<IP> (firmware lama pre-rebrand)
                        // Keduanya diterima agar ESP yang belum di-flash ulang
                        // tetap bisa ditemukan oleh aplikasi versi baru.
                        if (isi.startsWith("HALODECK:") || isi.startsWith("MACROPAD:")) {
                            val bagian = isi.split(":")
                            if (bagian.size == 3 && bagian[1] == "STA") {
                                // PENTING: pakai ALAMAT PENGIRIM paket,
                                // bukan teks di isi paket — jauh lebih andal
                                // karena IP asli ESP pasti benar.
                                jawaban = paket.address.hostAddress
                            }
                            // Bagian "AP" (mode setup): dibiarkan. Portal
                            // konfigurasi memang lewat browser, bukan aplikasi.
                        }
                        // Bukan balasan HALODECK -> abaikan, dengarkan lagi
                    } catch (_: SocketTimeoutException) {
                        break   // Waktu habis
                    }
                }
            }
        } catch (_: Exception) {
            // Jaringan belum siap, coba lagi nanti
        }
        return jawaban
    }

    // ============================================================
    // KONEKSI TCP (dipakai temuan otomatis maupun manual)
    // ============================================================
    // Gerbang tunggal untuk SEMUA upaya sambung (thread pencarian, reconnect,
    // maupun dialog IP manual). Tanpa gembok ini dua thread bisa membuka dua
    // socket bersamaan; ESP hanya menyimpan SATU client, jadi yang satu
    // menutup yang lain -> pembaca yang terusir mati, reconnect, menutup
    // lagi -> LOOP KONEK-PUTUS tak berujung.
    private fun sambungTcp(ip: String): Boolean {
        synchronized(this) {
            if (terhubung) return true       // sudah tersambung — jangan dobel

            val s = Socket()
            try {
                s.connect(InetSocketAddress(ip, 8080), 4000)
                s.tcpNoDelay = true
                // Tanpa soTimeout ini readLine() bisa memblokir selamanya
                // bila jalur putus diam-diam (lihat keterangan terakhirBalasan)
                s.soTimeout = TIMEOUT_BACA_MS
            } catch (_: Exception) {
                try { s.close() } catch (_: Exception) {}
                return false
            }

            // Socket lama (kalau masih ada) ditutup dulu sebelum mengganti
            val lama = socket
            generasi += 1                    // penanda: ini koneksi terbaru
            socket = s
            penulis = OutputStreamWriter(s.getOutputStream(), "UTF-8")
            terhubung = true
            ipTersimpan = ip
            // Mulai dari nol: koneksi BARU masih segar, jadi jangan langsung
            // dianggap senyap oleh pembaca.
            terakhirBalasan = SystemClock.elapsedRealtime()
            mulaiPembaca(s, generasi)
            mulaiHeartbeat(generasi)
            try { lama?.close() } catch (_: Exception) {}

            perbaruiStatus(R.color.aksen_hijau, getString(R.string.status_tersambung))
            perbaruiRedupGrid()
            kirimPerintah("STAT")
            return true
        }
    }

    private fun mulaiPembaca(s: Socket, milik: Int) {
        Thread {
            try {
                val pembaca = BufferedReader(InputStreamReader(s.getInputStream(), "UTF-8"))
                while (terhubung && generasi == milik) {
                    // readLine() akan melempar SocketTimeoutException tiap
                    // TIMEOUT_BACA_MS bila senyap. Bukan kesalahan -- justru
                    // itulah yang membuat pembaca bisa memeriksa kesehatan
                    // koneksi dan tidak terkunci selamanya.
                    val baris: String? = try {
                        pembaca.readLine()
                    } catch (e: SocketTimeoutException) {
                        if (SystemClock.elapsedRealtime() - terakhirBalasan
                            > BATAS_SEPI_MS) {
                            // Senyap terlalu lama walau heartbeat terkirim ->
                            // jalur mati DIAM-DIAM (tak ada FIN/RST yang sampai)
                            Log.d(TAG, "Pembaca senyap > ${BATAS_SEPI_MS}ms — " +
                                       "menganggap koneksi mati")
                            null
                        } else {
                            continue          // masih hidup, giliran berikutnya
                        }
                    }
                    if (baris == null) break
                    terakhirBalasan = SystemClock.elapsedRealtime()
                    prosesBalasan(baris.trim())
                }
            } catch (_: InterruptedException) {
                // Thread dihentikan
            } catch (e: Exception) {
                // Koneksi terputus / error jaringan — wajar, tidak perlu crash
                Log.d(TAG, "Pembaca berhenti: ${e.message}")
            }

            // PEMBACA BASI: socket ini sudah digantikan koneksi lebih baru
            // (generasi berubah) atau sudah ditutup lewat putusKoneksi().
            // DIAM saja — jangan sentuh status, jangan sambung ulang.
            // Tanpa cek ini, socket lama yang di-close akan memicu reconnect
            // yang menutup koneksi baru -> loop konek-putus.
            if (generasi != milik) {
                Log.d(TAG, "Pembaca basi (gen $milik vs $generasi) — diabaikan")
                return@Thread
            }

            picuReconnect(milik)
        }.start()
    }

    // ============================================================
    // HEARTBEAT: kirim PING berkala ke ESP (dia membalas PONG).
    // Tanpa ini, koneksi yang mati diam-diam tak pernah terdeteksi: tidak
    // ada data masuk, jadi pembaca tidak pernah bangun dari blokirnya.
    // ============================================================
    private fun mulaiHeartbeat(milik: Int) {
        Thread {
            while (terhubung && generasi == milik) {
                try {
                    Thread.sleep(INTERVAL_HEARTBEAT_MS)
                } catch (_: InterruptedException) {
                    return@Thread              // activity ditutup
                }
                if (generasi != milik || !terhubung) return@Thread
                try {
                    penulis?.write("PING\n")
                    penulis?.flush()
                } catch (e: Exception) {
                    // Gagal menulis berarti koneksi sudah mati. Pembaca tetap
                    // yang menutup jalur (dia paling tahu keadaan socket-nya),
                    // tapi di sini kita percepat agar tak menunggu penuh.
                    Log.d(TAG, "Heartbeat gagal tulis: ${e.message}")
                    picuReconnect(milik)
                    return@Thread
                }
            }
        }.start()
    }

    // ============================================================
    // SATU-SATUNYA JALUR KELUAR saat koneksi dianggap mati.
    // Dipanggil dari: pembaca keluar, pembaca senyap, heartbeat gagal tulis,
    // dan kirimPerintah gagal tulis. Semua lewat satu tempat agar gembok
    // sedangReconnect dan penjaga generasi berlaku KONSISTEN -- tanpa ini
    // bisa ada dua jalur balapan menyambung dan memicu loop konek-putus.
    // milik = nomor generasi pemanggil; bila sudah basi, DIAM.
    // ============================================================
    private fun picuReconnect(milik: Int) {
        if (generasi != milik) return          // pemanggil basi, biarkan yang baru

        synchronized(this) {
            // Sudah ditangani orang lain ATAU sudah tersambung lagi -> jangan
            // sentuh, supaya koneksi sehat tidak dibatalkan oleh pemanggil lama.
            if (generasi != milik || !terhubung) return
            terhubung = false
        }

        perbaruiStatus(R.color.aksen_merah, getString(R.string.status_terputus))
        perbaruiRedupGrid()

        // Coba sambung lagi ke IP terakhir dulu (cepat). Gembok
        // sedangReconnect menjamin hanya SATU thread reconnect berjalan.
        if (!sedangReconnect && ipTersimpan.isNotEmpty()) {
            sedangReconnect = true
            Thread {
                try {
                    Thread.sleep(1500)
                    val oke = !terhubung && sedangReconnect &&
                              sambungTcp(ipTersimpan)
                    if (!oke && !terhubung) mulaiPencarian()
                } catch (_: InterruptedException) {
                    // dilepas saat activity ditutup
                } finally {
                    sedangReconnect = false
                }
            }.start()
        } else if (!sedangReconnect) {
            mulaiPencarian()
        }
    }

    private fun putusKoneksiManual() {
        putusKoneksi()
        perbaruiStatus(R.color.teks_redup, getString(R.string.status_manual))
    }

    private fun putusKoneksi() {
        terhubung = false
        pencarianAktif = false
        sedangReconnect = false
        // Naikkan generasi -> pembaca lama tahu socketnya sudah basi dan
        // tidak akan memicu auto-reconnect (menutup loop konek-putus)
        generasi += 1
        // Naikkan juga generasi pencarian -> thread pencarian yang sedang
        // berputar berhenti, sehingga pencarian berikutnya tidak dobel
        generasiPencarian += 1
        try { socket?.close() } catch (_: Exception) {}
        socket = null
        penulis = null
        perbaruiRedupGrid()
    }

    // Saat tidak tersambung, semua tombol diredupkan agar jelas tombol belum
    // aktif. TETAP bisa disentuh — pengguna masih boleh membuka menu ⋮.
    // Catatan: yang diredupkan adalah TIAP TOMBOL, bukan wadah grid. Mengatur
    // alpha pada wadah tidak berpengaruh pada anak yang sudah dibuat, sehingga
    // pernah terjadi grid tetap redup walau sudah tersambung.
    private fun perbaruiRedupGrid() {
        val alpha = if (terhubung) 1f else REDUP_GRID
        uiHandler.post {
            for (i in 0 until gridMakro.childCount) {
                gridMakro.getChildAt(i).alpha = alpha
            }
        }
    }

    // ============================================================
    // PROSES BALASAN DARI ESP
    // ============================================================
    private fun prosesBalasan(baris: String) {
        when {
            baris.startsWith("PROF:") -> {
                val profil = baris.substring(5).uppercase()
                uiHandler.post { terapkanProfil(profil) }
            }
            baris.startsWith("VOL:") -> {
                // Volume PC yang diubah lewat keyboard/tombol fisik. Diproses
                // di thread pembaca, lalu diteruskan ke UI thread karena
                // sentuhan View (progress slider) hanya sah di thread UI.
                val nilai = baris.substring(4).toIntOrNull()
                if (nilai != null) {
                    uiHandler.post { terapkanVolumeDariPC(nilai) }
                }
            }
            // Balasan lain (PONG, ACK, OK, ERR) — cukup abaikan
        }
    }

    // Terima volume PC (hasil polling bridge) lalu gerakkan slider agar
    // posisinya mencerminkan keadaan PC yang sebenarnya.
    //
    // KUNCI ANTI-UMPAN-BALIK: setProgress() memanggil onProgressChanged
    // dengan fromUser = false. Pada bacaan kami di listener, nilai false
    // itu sudah cukup untuk membatalkan pengiriman balik. Flag
    // sedangSetVolume ditambahkan sebagai jaring pengaman kedua, karena
    // beberapa perangkat MIUI dilaporkan meneruskan fromUser = true pada
    // perubahan programatis -- dan jika itu terjadi, PC dan HP akan saling
    // memantul volume tanpa henti.
    private fun terapkanVolumeDariPC(persen: Int) {
        val nilai = persen.coerceIn(0, 100)
        volumeTerkini = nilai

        val slider = sliderVolume ?: return   // Baris belum dibuat -> cukup catat
        val label = labelVolume ?: return

        sedangSetVolume = true
        if (slider.progress != nilai) slider.progress = nilai
        label.text = "$nilai%"
        sedangSetVolume = false

        // Nilai tersinkron = nilai PC. Dicatat sebagai "terkirim" juga, supaya
        // bila pengguna menggeser ke posisi yang persis sama dengan volume PC
        // sekarang, tidak ada perintah VOL: yang dikirim sia-sia.
        volumeTerkirim = nilai
    }

    // ============================================================
    // CONTEXT-SWITCHING: ganti grid tombol sesuai profil PC
    // ============================================================
    private fun terapkanProfil(profil: String) {
        profilSekarang = profil
        teksProfil.text = profil
        bangunGridMakro(profil)
    }

    // Susun ulang grid: judul kelompok di atas, lalu tombol 3 kolom.
    private fun bangunGridMakro(profil: String) {
        gridMakro.removeAllViews()
        // Referensi slider lama tidak berlaku lagi setelah removeAllViews()
        sliderVolume = null
        labelVolume = null
        val daftarMakro = PROFIL_MAKRO[profil] ?: PROFIL_MAKRO.getValue("DEFAULT")

        var kelompokTerakhir = ""
        for (makro in daftarMakro) {
            if (makro.kelompok != kelompokTerakhir) {
                kelompokTerakhir = makro.kelompok
                gridMakro.addView(buatJudulKelompok(makro.kelompok))
                // Slider volume menempel di bawah judul "Umum". Volume PC
                // selalu relevan di setiap aplikasi, jadi cukup satu baris
                // di sini daripada diulang di tiap kelompok lain.
                if (makro.kelompok == KELOMPOK_UMUM) {
                    gridMakro.addView(buatBarisVolume())
                }
            }
            gridMakro.addView(buatTombolMakro(makro))
        }

        // Pastikan opasitas semua tombol mengikuti keadaan koneksi terkini
        perbaruiRedupGrid()
    }

    // Bangun satu baris slider volume yang membentang ke-3 kolom grid.
    // Nilai awalnya volumeTerkini (hasil dorongan PC terakhir), sehingga
    // slider tidak pernah "berbohong" tentang volume PC yang sebenarnya.
    private fun buatBarisVolume(): View {
        val tampilan = layoutInflater.inflate(
            R.layout.baris_volume, gridMakro, false
        )
        val slider = tampilan.findViewById<SeekBar>(R.id.slider_volume)
        val label = tampilan.findViewById<TextView>(R.id.teks_volume)
        sliderVolume = slider
        labelVolume = label

        // Pasang nilai yang sudah diketahui TANPA memicu pengiriman.
        // setValue() memang memanggil onProgressChanged, jadi flag penjaga
        // dinyalakan dulu agar nilai hasil sinkronisasi tidak ikut terkirim
        // balik ke PC (itulah sumber umpan balik tak berujung).
        sedangSetVolume = true
        if (volumeTerkini >= 0) {
            slider.progress = volumeTerkini
            label.text = "$volumeTerkini%"
        }
        sedangSetVolume = false

        slider.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar, progress: Int, fromUser: Boolean) {
                label.text = "$progress%"
                // fromUser = false berarti perubahan datang dari sinkronisasi
                // PC, bukan dari jari pengguna. Jangan dikirim ulang.
                if (!fromUser || sedangSetVolume) return
                if (progress == volumeTerkirim) return   // Nilai sama -> tak perlu kirim

                // THROTTLE: menggeser cepat memicu callback ini puluhan kali
                // tiap detik, dan tiap kali kirimVolume() membangun satu thread
                // serta menulis satu baris ke ESP. Tanpa jeda ini jalur serial
                // bisa tersumbat. Nilai yang terlewat tidak masalah karena nilai
                // berikutnya, dan terutama nilai akhir saat jari diangkat
                // (lihat onStopTrackingTouch), akan menyusul juga.
                val sekarang = SystemClock.elapsedRealtime()
                if (sekarang - waktuKirimVolume < INTERVAL_KIRIM_VOLUME_MS) return
                waktuKirimVolume = sekarang

                volumeTerkirim = progress
                kirimVolume(progress)
            }

            override fun onStartTrackingTouch(sb: SeekBar) {}

            override fun onStopTrackingTouch(sb: SeekBar) {
                // Nilai AKHIR saat jari diangkat: dikirim tanpa syarat, tanpa
                // throttle. Ini nilai yang benar-benar diinginkan pengguna, dan
                // juga menutup kemungkinan nilai terakhirnya sempat terlewat
                // oleh throttle di atas.
                waktuKirimVolume = SystemClock.elapsedRealtime()
                if (sb.progress != volumeTerkirim) {
                    volumeTerkirim = sb.progress
                    kirimVolume(sb.progress)
                }
            }
        })

        tampilan.layoutParams = GridLayout.LayoutParams().apply {
            width = 0
            height = GridLayout.LayoutParams.WRAP_CONTENT
            // Bentang 3 kolom + bobot 1f, sama seperti judul kelompok.
            columnSpec = GridLayout.spec(0, 3, 1f)
            setMargins(4, 2, 4, 4)
        }
        tampilan.alpha = if (terhubung) 1f else REDUP_GRID
        return tampilan
    }

    private fun buatJudulKelompok(teks: String): TextView {
        return TextView(this).apply {
            text = teks
            textSize = 12f
            setTextColor(getColor(R.color.teks_redup))
            gravity = Gravity.CENTER_VERTICAL
            setPadding(4, 20, 4, 8)
            layoutParams = GridLayout.LayoutParams().apply {
                width = 0
                height = GridLayout.LayoutParams.WRAP_CONTENT
                // Bobot 1f WAJIB: tanpa bobot, width = 0 membuat teks judul
                // menyusut jadi nol lebar sehingga tidak pernah terlihat.
                // Dibentangkan ke 3 kolom agar menempati seluruh baris.
                columnSpec = GridLayout.spec(0, 3, 1f)
            }
        }
    }

    private fun buatTombolMakro(makro: Makro): View {
        val tampilan = layoutInflater.inflate(
            R.layout.item_makro, gridMakro, false
        )

        val ikon = tampilan.findViewById<ImageView>(R.id.ikon_makro)
        val label = tampilan.findViewById<TextView>(R.id.label_makro)
        label.text = makro.label

        // Nama berkas ikon -> resource drawable, tanpa daftar when panjang
        val idRes = resources.getIdentifier(
            "ic_m_${makro.ikon}", "drawable", packageName
        )
        if (idRes != 0) {
            ikon.setImageResource(idRes)
            // Warna ikon disamakan dengan label; saat bahaya, dipakai merah
            ikon.setColorFilter(
                getColor(if (makro.bahaya) R.color.aksen_merah else R.color.warna_ikon),
                PorterDuff.Mode.SRC_IN
            )
        }

        // Tombol berbahaya memakai latar ripple merah agar menonjol
        if (makro.bahaya) {
            tampilan.setBackgroundResource(R.drawable.ripple_makro_bahaya)
        }

        tampilan.layoutParams = GridLayout.LayoutParams().apply {
            width = 0
            height = GridLayout.LayoutParams.WRAP_CONTENT
            // Kolom berbobot 1f -> ketiga kolom selalu sama lebar
            columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1, 1f)
            setMargins(5, 5, 5, 5)
        }

        // Tombol baru dibuat sesuai keadaan koneksi saat ini. Alpha final
        // tetap diselaraskan lagi oleh perbaruiRedupGrid() setelah grid jadi.
        tampilan.alpha = if (terhubung) 1f else REDUP_GRID
        tampilan.setOnClickListener { kirimPerintah(makro.perintah) }
        return tampilan
    }

    // Kirim volume ke ESP: "VOL:<0-100>". Berbeda dari kirimPerintah(),
    // fungsi ini SENYAP saat tersambung putus -- menggeser slider bisa
    // memanggilnya puluhan kali per detik, sehingga Toast akan menumpuk
    // dan menutupi layar. Kegagalan diam-diam cukup: pengguna akan melihat
    // sendiri slider tidak berpengaruh, dan auto-reconnect menyusul.
    private fun kirimVolume(persen: Int) {
        if (!terhubung || penulis == null) return
        val nilai = persen.coerceIn(0, 100)
        val teks = "VOL:$nilai"
        val milik = generasi
        Thread {
            try {
                penulis?.write(teks + "\n")
                penulis?.flush()
            } catch (e: Exception) {
                // Sama seperti kirimPerintah(): gagal menulis berarti koneksi
                // sudah mati tanpa terdeteksi. Nyatakan mati agar reconnect
                // berjalan tanpa perlu sentuhan pengguna.
                Log.d(TAG, "Gagal kirim '$teks': ${e.message}")
                picuReconnect(milik)
            }
        }.start()
    }

    // ============================================================
    // KIRIM PERINTAH KE ESP8266
    // ============================================================
    private fun kirimPerintah(perintah: String) {
        if (!terhubung) {
            Toast.makeText(this, "Belum menemukan ESP8266!", Toast.LENGTH_SHORT).show()
            return
        }
        val milik = generasi
        Thread {
            try {
                penulis?.write(perintah + "\n")
                penulis?.flush()
            } catch (e: Exception) {
                // Gagal menulis = koneksi sudah mati. INILAH yang dulu membuat
                // pengguna harus menekan tombol manual untuk "membangunkan"
                // aplikasi: exception-nya ditelan, dan pembaca yang macet di
                // readLine() tak pernah tahu. Sekarang langsung nyatakan mati
                // supaya auto-reconnect berjalan tanpa perlu sentuhan pengguna.
                Log.d(TAG, "Gagal kirim '$perintah': ${e.message}")
                picuReconnect(milik)
            }
        }.start()
    }
}
