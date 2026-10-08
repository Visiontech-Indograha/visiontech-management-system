package com.visiontech.vms_mobile

import android.content.ContentValues
import android.content.Context
import android.media.MediaScannerConnection
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File

/**
 * Menyalin foto laporan dari kamera aplikasi ke galeri HP, album "Visiontech" (T10). Hanya foto laporan harian;
 * swafoto absen sengaja TIDAK pernah dikirim ke sini (tetap privat di folder aplikasi).
 * API 29+: MediaStore (RELATIVE_PATH + IS_PENDING, tanpa izin). API 24-28: tulis ke folder Pictures/Visiontech
 * (izin WRITE_EXTERNAL_STORAGE s.d. API 28) lalu pindai agar muncul di galeri.
 */
class GallerySave(private val context: Context) : MethodChannel.MethodCallHandler {
    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        try {
            when (call.method) {
                "saveImage" -> {
                    saveImage(File(call.argument<String>("path")!!))
                    result.success(null)
                }
                else -> result.notImplemented()
            }
        } catch (e: Exception) {
            result.error("GALLERY_SAVE_ERROR", e.message, null)
        }
    }

    private fun saveImage(source: File) {
        require(source.isFile) { "Berkas tidak ditemukan" }
        if (Build.VERSION.SDK_INT >= 29) {
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, source.name)
                put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
                put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/Visiontech")
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
            val resolver = context.contentResolver
            val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                ?: error("MediaStore menolak")
            resolver.openOutputStream(uri)!!.use { out -> source.inputStream().use { it.copyTo(out) } }
            values.clear()
            values.put(MediaStore.Images.Media.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
        } else {
            @Suppress("DEPRECATION")
            val dir = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES), "Visiontech")
            dir.mkdirs()
            val target = File(dir, source.name)
            source.copyTo(target, overwrite = true)
            MediaScannerConnection.scanFile(context, arrayOf(target.absolutePath), arrayOf("image/jpeg"), null)
        }
    }
}
