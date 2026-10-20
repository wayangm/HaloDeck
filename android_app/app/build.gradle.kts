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
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
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
