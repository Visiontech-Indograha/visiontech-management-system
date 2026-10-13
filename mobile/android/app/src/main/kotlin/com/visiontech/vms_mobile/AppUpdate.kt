package com.visiontech.vms_mobile

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import androidx.core.content.pm.PackageInfoCompat
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File

/**
 * Pembaruan aplikasi tanpa Play Store (docs/32): versi terpasang, izin "instal aplikasi tak dikenal", dan membuka
 * installer Android untuk APK yang sudah diunduh & diverifikasi Dart. Android sendiri menolak APK yang tidak
 * ditandatangani kunci yang sama, sehingga data aplikasi (antrean luring, kunci Keystore) tetap aman.
 */
class AppUpdate(private val context: Context) : MethodChannel.MethodCallHandler {
    private val authority = "${context.packageName}.updates"

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        try {
            when (call.method) {
                "info" -> result.success(info())
                "updatesDir" -> result.success(updatesDir().absolutePath)
                "canInstall" -> result.success(canInstall())
                "openInstallSettings" -> {
                    openInstallSettings()
                    result.success(null)
                }
                "install" -> {
                    install(File(call.argument<String>("path")!!))
                    result.success(null)
                }
                "sha256" -> result.success(fileSha256(File(call.argument<String>("path")!!)))
                else -> result.notImplemented()
            }
        } catch (e: Exception) {
            result.error("APP_UPDATE_ERROR", e.message, null)
        }
    }

    private fun info(): Map<String, Any> {
        val pm = context.packageManager
        val pkg = if (Build.VERSION.SDK_INT >= 33) {
            pm.getPackageInfo(context.packageName, PackageManager.PackageInfoFlags.of(0))
        } else {
            @Suppress("DEPRECATION")
            pm.getPackageInfo(context.packageName, 0)
        }
        return mapOf(
            "version_name" to (pkg.versionName ?: ""),
            "version_code" to PackageInfoCompat.getLongVersionCode(pkg),
            "abis" to Build.SUPPORTED_ABIS.toList(),
            "sdk" to Build.VERSION.SDK_INT,
            "model" to "${Build.MANUFACTURER} ${Build.MODEL}",
        )
    }

    private fun updatesDir(): File = File(context.cacheDir, "updates").apply { mkdirs() }

    private fun canInstall(): Boolean =
        Build.VERSION.SDK_INT < 26 || context.packageManager.canRequestPackageInstalls()

    private fun openInstallSettings() {
        val intent = if (Build.VERSION.SDK_INT >= 26) {
            Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${context.packageName}"))
        } else {
            Intent(Settings.ACTION_SECURITY_SETTINGS)
        }
        context.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    private fun install(apk: File) {
        // Hanya berkas di folder unduhan pembaruan milik aplikasi ini yang boleh diteruskan ke installer.
        require(apk.canonicalFile.parentFile == updatesDir().canonicalFile && apk.isFile) { "Berkas pembaruan tidak valid" }
        val uri = FileProvider.getUriForFile(context, authority, apk)
        val intent = Intent(Intent.ACTION_VIEW)
            .setDataAndType(uri, "application/vnd.android.package-archive")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }
}
