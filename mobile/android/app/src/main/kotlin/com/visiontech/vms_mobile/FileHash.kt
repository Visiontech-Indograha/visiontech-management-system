package com.visiontech.vms_mobile

import java.io.File
import java.security.MessageDigest

/** SHA-256 berkas sebagai hex huruf kecil, dibaca bertahap (APK puluhan MB tidak dimuat utuh ke memori). */
fun fileSha256(file: File): String {
    val digest = MessageDigest.getInstance("SHA-256")
    file.inputStream().use { input ->
        val buffer = ByteArray(64 * 1024)
        while (true) {
            val read = input.read(buffer)
            if (read < 0) break
            digest.update(buffer, 0, read)
        }
    }
    return digest.digest().joinToString("") { "%02x".format(it) }
}
