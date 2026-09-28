package com.visiontech.vms_mobile

import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

// FlutterFragmentActivity (bukan FlutterActivity biasa) -- wajib untuk
// package local_auth (login sidik jari, plan Keputusan 7): plugin ini
// memakai androidx.biometric.BiometricPrompt yang butuh FragmentActivity,
// gagal/crash diam-diam kalau tetap pakai FlutterActivity.
class MainActivity : FlutterFragmentActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        // Dipanggil Flutter setelah layar yang mengubah mode sistem (mis. kamera) ditutup.
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "vms/system_ui")
            .setMethodCallHandler { call, result ->
                if (call.method == "hideNavigation") {
                    hideSystemNavigation()
                    result.success(null)
                } else {
                    result.notImplemented()
                }
            }
    }

    override fun onResume() {
        super.onResume()
        hideSystemNavigation()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemNavigation()
    }

    // R-14: navigasi bawaan HP disembunyikan saat aplikasi terbuka; usap dari tepi bawah
    // memunculkannya sementara lalu otomatis tersembunyi lagi. Status bar tetap tampil.
    private fun hideSystemNavigation() {
        val controller = WindowCompat.getInsetsController(window, window.decorView)
        controller.systemBarsBehavior =
            WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        controller.hide(WindowInsetsCompat.Type.navigationBars())
    }
}
