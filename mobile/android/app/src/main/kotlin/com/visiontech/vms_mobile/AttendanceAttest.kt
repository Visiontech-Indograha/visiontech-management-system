package com.visiontech.vms_mobile

import android.content.Context
import android.os.SystemClock
import android.provider.Settings
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.Signature

/**
 * Absensi luring (R-34): bukti yang tidak bisa diubah di data aplikasi.
 * - Kunci EC P-256 dibuat di Android Keystore dan TIDAK PERNAH bisa dikeluarkan dari HP; setiap absen
 *   luring ditandatangani kunci ini, server memverifikasi dengan kunci publiknya.
 * - Jam: SystemClock.elapsedRealtime (penghitung sejak HP menyala — tidak terpengaruh jam/tanggal HP yang
 *   diubah) + jumlah boot (mendeteksi HP dinyalakan ulang saat luring).
 */
class AttendanceAttest(private val context: Context) : MethodChannel.MethodCallHandler {
    private val alias = "vms_attendance_offline_key"

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        try {
            when (call.method) {
                "publicKey" -> result.success(publicKey())
                "sign" -> result.success(sign(call.argument<String>("data")!!))
                "clock" -> result.success(
                    mapOf(
                        "elapsed_ms" to SystemClock.elapsedRealtime(),
                        "boot_count" to Settings.Global.getInt(context.contentResolver, Settings.Global.BOOT_COUNT, -1),
                    ),
                )
                "sha256" -> result.success(sha256(call.argument<String>("path")!!))
                else -> result.notImplemented()
            }
        } catch (e: Exception) {
            result.error("ATTEST_ERROR", e.message, null)
        }
    }

    private fun keyStore(): KeyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    private fun ensureKey() {
        if (keyStore().containsAlias(alias)) return
        val generator = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore")
        generator.initialize(
            KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN)
                .setAlgorithmParameterSpec(java.security.spec.ECGenParameterSpec("secp256r1"))
                .setDigests(KeyProperties.DIGEST_SHA256)
                .build(),
        )
        generator.generateKeyPair()
    }

    private fun publicKey(): String {
        ensureKey()
        val cert = keyStore().getCertificate(alias)
        return Base64.encodeToString(cert.publicKey.encoded, Base64.NO_WRAP)
    }

    private fun sign(data: String): String {
        ensureKey()
        val key = keyStore().getKey(alias, null) as PrivateKey
        val signature = Signature.getInstance("SHA256withECDSA").apply {
            initSign(key)
            update(data.toByteArray(Charsets.UTF_8))
        }
        return Base64.encodeToString(signature.sign(), Base64.NO_WRAP)
    }

    private fun sha256(path: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        File(path).inputStream().use { input ->
            val buffer = ByteArray(8192)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
