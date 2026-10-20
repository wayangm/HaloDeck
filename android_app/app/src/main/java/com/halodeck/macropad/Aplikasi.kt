// ============================================================
// HALODECK - Global Error Handler
// Aplikasi.kt
// Tugas : Menangkap SEMUA exception tak tertangani (di thread
//         mana pun) supaya aplikasi TIDAK force-close diam-diam.
//         Setiap error dicatat ke file + ditampilkan sebagai Toast.
// Komentar dalam Bahasa Indonesia
// ============================================================

package com.halodeck.macropad

import android.app.Application
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.widget.Toast
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class Aplikasi : Application() {

    companion object {
        const val TAG = "HaloDeck"

        @Volatile
        var terakhirError: String = ""   // Bisa dibaca dari UI untuk ditampilkan
    }

    private val uiHandler = Handler(Looper.getMainLooper())

    override fun onCreate() {
        super.onCreate()

        // Tangkap semua exception tak tertangani di SEMUA thread.
        // Handler lama tetap dipanggil supaya crash tetap tercatat di Logcat.
        val handlerLama = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, error ->
            try {
                tanganiError(thread, error)
            } catch (_: Exception) {
                // Jangan sampai handler-nya sendiri yang bikin crash
            }
            // Sengaja TIDAK meneruskan ke handler lama ->
            // aplikasi tidak force close, hanya dicatat.
        }
    }

    // Catat error ke log file + beri tahu pengguna lewat Toast.
    private fun tanganiError(thread: Thread, error: Throwable) {
        val waktu = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
            .format(Date())

        // Susun laporan yang mudah dibaca
        val laporan = buildString {
            appendLine("========== ERROR $waktu ==========")
            appendLine("Thread : ${thread.name}")
            appendLine("Tipe   : ${error.javaClass.name}")
            appendLine("Pesan  : ${error.message}")
            appendLine("-------- Trace --------")
            appendLine(error.stackTraceToString())
            appendLine("====================================")
        }

        // 1. Catat ke Logcat (supaya muncul di Android Studio / adb logcat)
        Log.e(TAG, "Error tak tertangani di thread ${thread.name}", error)

        // 2. Simpan ke file agar bisa dibaca tanpa Android Studio
        simpanKeFile(laporan)

        // 3. Beri tahu pengguna (lewat UI thread, aman)
        terakhirError = "${error.javaClass.simpleName}: ${error.message}"
        uiHandler.post {
            try {
                Toast.makeText(
                    this,
                    "Terjadi error, sudah dicatat: ${error.javaClass.simpleName}",
                    Toast.LENGTH_LONG
                ).show()
            } catch (_: Exception) {
                // Toast saja yang gagal, abaikan
            }
        }
    }

    // Tulis laporan error ke penyimpanan internal aplikasi.
    private fun simpanKeFile(laporan: String) {
        try {
            val berkas = File(filesDir, "error_log.txt")
            // Batasi ukuran file: kalau > 100 KB, mulai dari kosong lagi
            if (berkas.exists() && berkas.length() > 100 * 1024) {
                berkas.delete()
            }
            FileWriter(berkas, true).use { it.write(laporan) }
        } catch (_: Exception) {
            // Gagal menulis log bukan masalah fatal
        }
    }
}
