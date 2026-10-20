// ============================================================
// HALODECK - FASE 3 (Android Native - FINAL)
// MainActivity.kt (Bahasa Kotlin, tanpa library eksternal)
// Fitur:
//  1. TEMUKAN OTOMATIS: UDP discovery -> IP ESP diisi sendiri,
//     auto-connect TCP tanpa ketik IP apa pun
//  2. AUTO-RECONNECT: koneksi putus / jaringan siap lagi ->
//     aplikasi langsung mencari & menyambung sendiri
//  3. ATUR WI-FI VIA HP: kirim SSID+password ke ESP tanpa kabel
//     (ESP simpan di flash, restart, langsung join jaringan)
//  4. Grid tombol MENYESUAIKAN PROFIL aktif di PC (context-switching)
// Komentar dalam Bahasa Indonesia
// ============================================================

package com.halodeck.macropad

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiNetworkSpecifier
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.text.InputType
import android.util.Log
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.GridLayout
import android.widget.LinearLayout
import android.widget.ListView
import android.widget.ArrayAdapter
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
// ============================================================
data class Makro(val label: String, val perintah: String)

val PROFIL_MAKRO: Map<String, List<Makro>> = mapOf(
    "DEFAULT" to listOf(
        Makro("Kunci PC",     "BTN:LOCK"),
        Makro("Mute",         "BTN:MUTE"),
        Makro("Browser",      "BTN:BROWSER"),
        Makro("Task Manager", "BTN:TASKMGR")
    ),
    "NOTEPAD" to listOf(
        Makro("Simpan (Ctrl+S)", "BTN:SIMPAN"),
        Makro("Baru (Ctrl+N)",   "BTN:BARU"),
        Makro("Undo (Ctrl+Z)",   "BTN:UNDO"),
        Makro("Redo (Ctrl+Y)",   "BTN:REDO")
    ),
    "VSCODE" to listOf(
        Makro("Simpan (Ctrl+S)", "BTN:SIMPAN"),
        Makro("Undo (Ctrl+Z)",   "BTN:UNDO"),
        Makro("Redo (Ctrl+Y)",   "BTN:REDO"),
        Makro("Kunci PC",        "BTN:LOCK")
    ),
    "PHOTOSHOP" to listOf(
        Makro("Zoom In",       "BTN:PS_ZOOMIN"),
        Makro("Zoom Out",      "BTN:PS_ZOOMOUT"),
        Makro("Fit Layar",     "BTN:PS_FIT"),
        Makro("Layer Baru",    "BTN:PS_LAYER"),
        Makro("Flatten Image", "BTN:PS_FLATTEN"),
        Makro("Mute",          "BTN:MUTE")
    ),
    "PREMIERE" to listOf(
        Makro("Undo",         "BTN:PR_UNDO"),
        Makro("Cut (Ctrl+K)", "BTN:PR_CUT"),
        Makro("Mark In",      "BTN:PR_IN"),
        Makro("Mark Out",     "BTN:PR_OUT"),
        Makro("Export Frame", "BTN:PR_EXPORT"),
        Makro("Mute",         "BTN:MUTE")
    ),
    "AFTEREFFECTS" to listOf(
        Makro("Undo",     "BTN:UNDO"),
        Makro("Redo",     "BTN:REDO"),
        Makro("Mute",     "BTN:MUTE"),
        Makro("Kunci PC", "BTN:LOCK")
    ),
    "ILLUSTRATOR" to listOf(
        Makro("Simpan", "BTN:SIMPAN"),
        Makro("Baru",   "BTN:BARU"),
        Makro("Undo",   "BTN:UNDO"),
        Makro("Mute",   "BTN:MUTE")
    ),
    "BROWSER" to listOf(
        // --- Tab ---
        Makro("Tab Baru (Ctrl+T)",     "BTN:TABBARU"),
        Makro("Tutup Tab (Ctrl+W)",    "BTN:TUTUPTAB"),
        Makro("Buka Lagi Tab",         "BTN:BUKALAGI"),   // Undo close
        Makro("Tab Berikutnya",        "BTN:TABLANJUT"),
        Makro("Tab Sebelumnya",        "BTN:TABSEBELUM"),
        // --- Navigasi ---
        Makro("Reload (F5)",           "BTN:RELOAD"),
        Makro("Mundur",                "BTN:MUNDUR"),
        Makro("Maju",                  "BTN:MAJU"),
        // --- Utilitas ---
        Makro("Cari di Halaman",       "BTN:CARI"),
        Makro("Kolom Alamat",          "BTN:ALAMAT"),
        Makro("Bookmark (Ctrl+D)",     "BTN:BOOKMARK"),
        Makro("Riwayat (Ctrl+H)",      "BTN:RIWAYAT"),
        Makro("Unduhan (Ctrl+J)",      "BTN:UNDUHAN"),
        Makro("Incognito",             "BTN:INCOGNITO"),
        Makro("DevTools",              "BTN:DEVTOOLS"),
        // --- Umum ---
        Makro("Simpan (Ctrl+S)",       "BTN:SIMPAN"),
        Makro("Kunci PC",              "BTN:LOCK")
    )
)

// Nama hotspot fallback ESP (mode setup)
const val NAMA_HOTSPOT_ESP = "HALODECK-SETUP"
const val IP_MODE_AP       = "192.168.4.1"

// Kode permintaan izin lokasi (dipakai untuk pindai Wi-Fi)
const val IZIN_LOKASI = 101

class MainActivity : Activity() {

    // --- Elemen UI ---
    private lateinit var inputIp: EditText
    private lateinit var tombolHubungkan: Button
    private lateinit var tombolAturWifi: Button
    private lateinit var teksStatus: TextView
    private lateinit var teksProfil: TextView
    private lateinit var gridMakro: GridLayout

    // --- Status koneksi ---
    @Volatile private var socket: Socket? = null
    @Volatile private var penulis: OutputStreamWriter? = null
    @Volatile private var terhubung = false
    @Volatile private var pencarianAktif = false
    private var profilSekarang = "DEFAULT"
    private var ipTersimpan = ""          // IP hasil temuan otomatis

    private lateinit var cm: ConnectivityManager
    val uiHandler = Handler(Looper.getMainLooper())

    // ============================================================
    // LIFECYCLE
    // ============================================================
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        inputIp = findViewById(R.id.inputIp)
        tombolHubungkan = findViewById(R.id.tombolHubungkan)
        tombolAturWifi = findViewById(R.id.tombolAturWifi)
        teksStatus = findViewById(R.id.teksStatus)
        teksProfil = findViewById(R.id.teksProfil)
        gridMakro = findViewById(R.id.gridMakro)

        cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager

        bangunGridMakro(profilSekarang)

        // --- MULAI PENCARIAN OTOMATIS saat aplikasi dibuka ---
        mulaiPencarian()

        // --- Tombol hubungkan/putus (manual override) ---
        tombolHubungkan.setOnClickListener {
            if (terhubung) {
                putusKoneksiManual()
            } else {
                mulaiPencarian()
            }
        }

        // --- Tombol atur Wi-Fi ESP via HP ---
        tombolAturWifi.setOnClickListener { tampilkanDialogAturWifi() }

        // --- Pantau jaringan: Wi-Fi siap -> langsung cari & sambung ---
        pantauJaringan()
    }

    override fun onDestroy() {
        super.onDestroy()
        putusKoneksi()
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
                    // Jaringan Wi-Fi tersedia -> kalau belum tersambung, cari ESP
                    if (!terhubung) {
                        uiHandler.post {
                            teksStatus.text = "Jaringan siap — mencari ESP8266..."
                        }
                        mulaiPencarian()
                    }
                }
            })
        } catch (e: SecurityException) {
            // Izin ACCESS_NETWORK_STATE tidak ada -> fitur auto-reconnect
            // nonaktif, tapi aplikasi TETAP jalan normal
            Log.w("HaloDeck", "Pantau jaringan nonaktif: ${e.message}")
        }
    }

    // ============================================================
    // TEMUKAN OTOMATIS: UDP discovery -> auto-connect TCP
    // ============================================================
    private fun mulaiPencarian() {
        if (pencarianAktif || terhubung) return
        pencarianAktif = true

        // Penting: fungsi ini bisa dipanggil dari thread jaringan
        // (NetworkCallback), jadi akses View HARUS lewat uiHandler
        uiHandler.post { tombolHubungkan.text = "Mencari..." }

        Thread {
            try {
                while (!terhubung) {
                    val ip = temukanIpEsp()
                    if (ip != null && !terhubung) {
                        uiHandler.post {
                            inputIp.setText(ip)
                            teksStatus.text = "ESP ditemukan ($ip) — menyambung..."
                            teksStatus.setTextColor(getColor(R.color.aksen_biru))
                        }
                        if (sambungTcp(ip)) break
                    }
                    // Coba lagi 2 detik kemudian (terus mencari otomatis)
                    Thread.sleep(2000)
                }
            } catch (_: InterruptedException) {
                // Thread dihentikan, abaikan
            } catch (e: Exception) {
                // Error tak terduga jangan sampai bikin crash
                Log.e("HaloDeck", "Gagal saat mencari ESP", e)
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
                        // Format: HALODECK:<MODE>:<IP>
                        if (isi.startsWith("HALODECK:")) {
                            val bagian = isi.split(":")
                            if (bagian.size == 3 && bagian[1] == "STA") {
                                // PENTING: pakai ALAMAT PENGIRIM paket,
                                // bukan teks di isi paket — jauh lebih andal
                                // karena IP asli ESP pasti benar.
                                jawaban = paket.address.hostAddress
                            } else if (bagian.size == 3 && bagian[1] == "AP") {
                                uiHandler.post {
                                    teksStatus.text =
                                        "ESP mode hotspot — tekan 'Atur Wi-Fi ESP'"
                                    teksStatus.setTextColor(getColor(R.color.aksen_biru))
                                }
                            }
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
    private fun sambungTcp(ip: String): Boolean {
        return try {
            val s = Socket()
            s.connect(InetSocketAddress(ip, 8080), 4000)
            s.tcpNoDelay = true
            socket = s
            penulis = OutputStreamWriter(s.getOutputStream(), "UTF-8")
            terhubung = true
            ipTersimpan = ip
            mulaiPembaca(s)

            uiHandler.post {
                teksStatus.text = "Terhubung otomatis ($ip)"
                teksStatus.setTextColor(getColor(R.color.aksen_hijau))
                tombolHubungkan.text = "Putuskan"
                kirimPerintah("STAT")
            }
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun mulaiPembaca(s: Socket) {
        Thread {
            try {
                val pembaca = BufferedReader(InputStreamReader(s.getInputStream(), "UTF-8"))
                while (terhubung) {
                    val baris = pembaca.readLine() ?: break
                    prosesBalasan(baris.trim())
                }
            } catch (_: InterruptedException) {
                // Thread dihentikan
            } catch (e: Exception) {
                // Koneksi terputus / error jaringan — wajar, tidak perlu crash
                Log.d("HaloDeck", "Pembaca berhenti: ${e.message}")
            }
            // Koneksi mati -> AUTO-CARI & SAMBUNG ULANG
            if (terhubung) {
                terhubung = false
                uiHandler.post {
                    teksStatus.text = "Terputus — mencari ulang otomatis..."
                    teksStatus.setTextColor(getColor(R.color.aksen_merah))
                    tombolHubungkan.text = "Mencari..."
                    // Coba sambung lagi ke IP terakhir dulu (cepat)
                    Thread {
                        Thread.sleep(1500)
                        if (!terhubung && ipTersimpan.isNotEmpty()) {
                            if (!sambungTcp(ipTersimpan)) mulaiPencarian()
                        } else if (!terhubung) {
                            mulaiPencarian()
                        }
                    }.start()
                }
            }
        }.start()
    }

    private fun putusKoneksiManual() {
        putusKoneksi()
        uiHandler.post {
            teksStatus.text = "Diputus manual (tekan Hubungkan utk cari lagi)"
        }
    }

    private fun putusKoneksi() {
        terhubung = false
        pencarianAktif = false
        try { socket?.close() } catch (_: Exception) {}
        socket = null
        penulis = null
        // Akses View dibungkus uiHandler agar aman dipanggil dari thread mana pun
        uiHandler.post {
            try {
                tombolHubungkan.text = getString(R.string.tombol_hubungkan)
            } catch (_: Exception) {}
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
            // Balasan lain (PONG, ACK, OK, ERR) — cukup abaikan
        }
    }

    // ============================================================
    // CONTEXT-SWITCHING: ganti grid tombol sesuai profil PC
    // ============================================================
    private fun terapkanProfil(profil: String) {
        profilSekarang = profil
        teksProfil.text = "Profil: $profil"
        bangunGridMakro(profil)
    }

    private fun bangunGridMakro(profil: String) {
        gridMakro.removeAllViews()
        val daftarMakro = PROFIL_MAKRO[profil] ?: PROFIL_MAKRO.getValue("DEFAULT")

        for (makro in daftarMakro) {
            val tombol = Button(this).apply {
                text = makro.label
                textSize = 15f
                isAllCaps = false
                setBackgroundColor(getColor(R.color.aksen_biru))
                setTextColor(getColor(R.color.latar_gelap))
                val lp = GridLayout.LayoutParams().apply {
                    width = 0
                    height = GridLayout.LayoutParams.WRAP_CONTENT
                    columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f)
                    setMargins(8, 8, 8, 8)
                    gravity = Gravity.CENTER
                }
                layoutParams = lp
                setPadding(8, 24, 8, 24)
                setOnClickListener { kirimPerintah(makro.perintah) }
            }
            gridMakro.addView(tombol)
        }
    }

    // ============================================================
    // KIRIM PERINTAH KE ESP8266
    // ============================================================
    private fun kirimPerintah(perintah: String) {
        if (!terhubung) {
            Toast.makeText(this, "Belum menemukan ESP8266!", Toast.LENGTH_SHORT).show()
            return
        }
        Thread {
            try {
                penulis?.write(perintah + "\n")
                penulis?.flush()
            } catch (_: Exception) {
                uiHandler.post { /* Koneksi mati, pembaca yang menangani */ }
            }
        }.start()
    }

    // ============================================================
    // ATUR WI-FI ESP8266 LEWAT HP (tanpa kabel, tanpa PC)
    // SSID diisi lewat HASIL PINDAI, bukan ketik manual
    // ============================================================
    private fun tampilkanDialogAturWifi() {
        val etSsid = EditText(this).apply {
            hint = "SSID (pindai dulu atau ketik manual)"
            inputType = InputType.TYPE_CLASS_TEXT
        }
        val etPass = EditText(this).apply {
            hint = "Password Wi-Fi"
            inputType = InputType.TYPE_CLASS_TEXT or
                    InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        val daftarHasil = ListView(this).apply {
            visibility = android.view.View.GONE
            minimumHeight = 120
        }
        val teksPindai = TextView(this).apply {
            text = "Memindai jaringan di sekitar..."
            setTextColor(getColor(R.color.aksen_biru))
        }

        val isi = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val lp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
            lp.marginStart = 48; lp.marginEnd = 48; lp.topMargin = 16
            layoutParams = lp
            addView(etSsid)
            addView(teksPindai)
            addView(daftarHasil)
            addView(etPass)
        }

        val dialog = AlertDialog.Builder(this)
            .setTitle("Atur Wi-Fi ESP8266")
            .setMessage(
                "Pilih jaringan Wi-Fi rumah dari hasil pindai. " +
                "ESP8266 menyimpannya lalu otomatis menyambung.\n\n" +
                "HP sejenak pindah ke hotspot '$NAMA_HOTSPOT_ESP' — " +
                "internet HP tetap jalan via data seluler."
            )
            .setView(isi)
            .setPositiveButton("Kirim & Sambungkan") { _, _ ->
                val ssid = etSsid.text.toString().trim()
                val sandi = etPass.text.toString()
                if (ssid.isEmpty()) {
                    Toast.makeText(this, "SSID belum dipilih!", Toast.LENGTH_SHORT).show()
                } else {
                    kirimKredensialWifi(ssid, sandi)
                }
            }
            .setNegativeButton("Batal", null)
            .create()

        dialog.setOnShowListener {
            pindaiJaringan(etSsid, daftarHasil, teksPindai)
        }
        dialog.show()
    }

    // Pindai jaringan Wi-Fi di sekitar via WifiManager (butuh izin lokasi)
    private fun pindaiJaringan(
        etSsid: EditText,
        daftarHasil: ListView,
        teksPindai: TextView
    ) {
        // Cek izin lokasi (wajib Android 8+ untuk hasil scan Wi-Fi)
        if (checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION)
            != android.content.pm.PackageManager.PERMISSION_GRANTED
        ) {
            teksPindai.text = "Butuh izin lokasi untuk memindai — izinkan dulu ya"
            requestPermissions(
                arrayOf(android.Manifest.permission.ACCESS_FINE_LOCATION),
                IZIN_LOKASI
            )
            return
        }

        val wifiManager = applicationContext
            .getSystemService(Context.WIFI_SERVICE) as android.net.wifi.WifiManager

        @Suppress("DEPRECATION")
        val berhasil = wifiManager.startScan()
        teksPindai.text =
            if (berhasil) "Memindai sekitar 5 detik..." else "Pindai dimulai, tunggu sebentar..."

        // Ambil hasil pindai (sedikit delay agar scan sempat selesai)
        daftarHasil.postDelayed({
            @Suppress("DEPRECATION")
            val hasil = wifiManager.scanResults
                .mapNotNull { r -> r.SSID?.takeIf { it.isNotEmpty() } }
                .distinct()
                .sortedBy { it.lowercase() }

            if (hasil.isEmpty()) {
                teksPindai.text =
                    "Tidak ada jaringan (GPS mungkin perlu aktif). Ketik manual saja:"
                return@postDelayed
            }

            teksPindai.text = "Klik jaringan untuk memilih (${hasil.size} ditemukan):"
            daftarHasil.visibility = android.view.View.VISIBLE
            daftarHasil.adapter = ArrayAdapter(
                this@MainActivity,
                android.R.layout.simple_list_item_1,
                hasil
            )
            daftarHasil.setOnItemClickListener { _, _, posisi, _ ->
                etSsid.setText(hasil[posisi])
                daftarHasil.visibility = android.view.View.GONE
                teksPindai.text = "Terpilih: ${hasil[posisi]}"
            }
        }, 5000)
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == IZIN_LOKASI) {
            Toast.makeText(
                this,
                if (grantResults.isNotEmpty() &&
                    grantResults[0] == android.content.pm.PackageManager.PERMISSION_GRANTED
                ) "Izin diberikan — buka lagi dialog Atur Wi-Fi"
                else "Tanpa izin lokasi, pindai Wi-Fi tidak bisa",
                Toast.LENGTH_LONG
            ).show()
        }
    }

    private fun kirimKredensialWifi(ssid: String, sandi: String) {
        teksStatus.text = "Menyambung ke hotspot ESP untuk setup..."
        teksStatus.setTextColor(getColor(R.color.aksen_biru))

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            // Android 10+: sambung hotspot ESP TANPA kehilangan internet
            // (WifiNetworkSpecifier — koneksi lokal khusus, data seluler tetap jalan)
            val specifier = WifiNetworkSpecifier.Builder()
                .setSsid(NAMA_HOTSPOT_ESP)
                .build()
            val permintaan = NetworkRequest.Builder()
                .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                .setNetworkSpecifier(specifier)
                .build()

            cm.requestNetwork(permintaan, object : ConnectivityManager.NetworkCallback() {
                override fun onAvailable(network: Network) {
                    // Terhubung hotspot ESP -> kirim kredensial
                    Thread {
                        try {
                            cm.bindProcessToNetwork(network)   // Paksa lewat hotspot ESP
                            Socket(IP_MODE_AP, 8080).use { s ->
                                val w = OutputStreamWriter(s.getOutputStream(), "UTF-8")
                                w.write("WIFI:$ssid:$sandi\n")
                                w.flush()
                                val r = BufferedReader(InputStreamReader(s.getInputStream()))
                                val balas = r.readLine()   // ACK:WIFI:MENYIMPAN
                                uiHandler.post {
                                    Toast.makeText(
                                        this@MainActivity,
                                        "ESP: ${balas ?: "OK"} — menyimpan & restart. " +
                                        "Tunggu ~30 detik, aplikasi mencari otomatis.",
                                        Toast.LENGTH_LONG
                                    ).show()
                                    teksStatus.text = "Kredensial terkirim — ESP restart..."
                                }
                            }
                        } catch (e: Exception) {
                            uiHandler.post {
                                Toast.makeText(
                                    this@MainActivity,
                                    "Gagal kirim: ${e.message}",
                                    Toast.LENGTH_LONG
                                ).show()
                            }
                        } finally {
                            cm.bindProcessToNetwork(null)
                            cm.unregisterNetworkCallback(this)
                            // Setelah ESP restart & join router, mulai cari lagi
                            uiHandler.postDelayed({
                                terhubung = false
                                mulaiPencarian()
                            }, 15000)
                        }
                    }.start()
                }

                override fun onUnavailable() {
                    uiHandler.post {
                        Toast.makeText(
                            this@MainActivity,
                            "Hotspot '$NAMA_HOTSPOT_ESP' tidak ditemukan. " +
                            "Pastikan ESP menyala (LED mati 3x = mode hotspot).",
                            Toast.LENGTH_LONG
                        ).show()
                        teksStatus.text = "Hotspot ESP tidak ditemukan"
                    }
                }
            }, 20000)   // Timeout 20 detik
        } else {
            // Android 9 ke bawah: arahkan ke Pengaturan Wi-Fi
            Toast.makeText(
                this,
                "Sambung manual ke hotspot '$NAMA_HOTSPOT_ESP' di " +
                "Pengaturan Wi-Fi, lalu tekan tombol ini lagi.",
                Toast.LENGTH_LONG
            ).show()
            startActivity(Intent(Settings.ACTION_WIFI_SETTINGS))
        }
    }
}
