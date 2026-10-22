// Build file modul aplikasi - HaloDeck (Android Native)
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.halodeck.macropad"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.halodeck.macropad"
        minSdk = 24          // Android 7.0 ke atas
        targetSdk = 34
        versionCode = 3
        versionName = "1.1.0"
    }

    signingConfigs {
        // Rilis ditandatangani dengan keystore debug mesin build.
        //
        // Ini bukan jalan pintas yang keliru: sidik jarinya SAMA PERSIS
        // dengan yang dipakai rilis 1.0.0 dan 1.0.2 (diperiksa lewat
        // apksigner), sehingga APK baru bisa dipasang TIMPA di atas yang
        // lama tanpa perlu uninstall. Aplikasi didistribusikan lewat
        // GitHub Releases, bukan Play Store, jadi syarat keystore rilis
        // khusus yang disimpan jangka panjang tidak berlaku di sini.
        create("rilis") {
            storeFile = file("${System.getProperty("user.home")}/.android/debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("rilis")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    // Tanpa library eksternal — murni Android SDK asli (View + Thread)
    // Sesuai prinsip "native, bukan berbasis web"
}
