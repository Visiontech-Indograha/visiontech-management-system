import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Kunci tanda tangan rilis dibaca dari `android/key.properties` (TIDAK masuk Git; contoh: key.properties.example).
val keystoreProperties = Properties().apply {
    val file = rootProject.file("key.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}
val hasReleaseKey = listOf("storeFile", "storePassword", "keyAlias", "keyPassword").all { keystoreProperties.containsKey(it) }

android {
    namespace = "com.visiontech.vms_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.visiontech.vms_mobile"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // Uses the version code from pubspec.yaml. When using split APKs, 1000 * ABI_VERSION
        // is added automatically by Flutter. (https://developer.android.com/studio/build/configure-apk-splits#configure-APK-versions)
        // You can force using the value of versionCode by specifying the `-P force-version-code-ignoring-abi=true`
        // flag during build.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        if (hasReleaseKey) {
            create("release") {
                storeFile = rootProject.file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        // HTTP tanpa enkripsi hanya untuk debug/profile (backend LAN). Rilis wajib HTTPS, kecuali
        // uji LAN sementara: `flutter build apk --release -PallowCleartext=true`.
        getByName("debug") { manifestPlaceholders["usesCleartextTraffic"] = "true" }
        getByName("profile") { manifestPlaceholders["usesCleartextTraffic"] = "true" }
        release {
            manifestPlaceholders["usesCleartextTraffic"] =
                (project.findProperty("allowCleartext") ?: "false").toString()
            // Rilis memakai kunci rilis. Tanpa key.properties, build rilis GAGAL (lihat pemeriksaan di bawah) —
            // kecuali uji lokal dengan `-PallowDebugSigning=true` (APK bertanda kunci debug, jangan dibagikan).
            signingConfig = signingConfigs.findByName("release") ?: signingConfigs.getByName("debug")
        }
    }
}

// APK rilis bertanda kunci debug tidak boleh sampai ke pengguna: pembaruan berikutnya tidak akan bisa dipasang di atasnya.
gradle.taskGraph.whenReady {
    val buildsRelease = allTasks.any { it.name == "assembleRelease" || it.name == "bundleRelease" }
    if (buildsRelease && !hasReleaseKey && !project.hasProperty("allowDebugSigning")) {
        throw GradleException(
            "Build rilis butuh kunci tanda tangan: buat android/key.properties (lihat key.properties.example). " +
                "Untuk uji lokal saja: tambahkan -PallowDebugSigning=true (APK bertanda kunci debug, jangan dibagikan).",
        )
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
