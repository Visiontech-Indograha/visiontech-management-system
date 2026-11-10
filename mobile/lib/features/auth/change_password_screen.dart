import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'auth_controller.dart';
import 'auth_state.dart';

/// Pesan kesalahan isian ganti sandi (batas sama dengan API: min 8, huruf + angka, beda dari sandi lama).
String? validateNewPassword(String current, String next) {
  if (next.length < 8) return 'Sandi baru minimal 8 karakter.';
  if (!RegExp(r'[A-Za-z]').hasMatch(next) || !RegExp(r'[0-9]').hasMatch(next)) {
    return 'Sandi baru harus berisi huruf dan angka.';
  }
  if (next == current) return 'Sandi baru tidak boleh sama dengan sandi lama.';
  return null;
}

/// Layar Ganti sandi. Bila akun wajib mengganti sandi sementara, layar ini satu-satunya yang bisa dibuka
/// (hanya ada tombol Keluar).
class ChangePasswordScreen extends ConsumerStatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  ConsumerState<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends ConsumerState<ChangePasswordScreen> {
  final _current = TextEditingController();
  final _next = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;
  bool _show = false;
  String? _error;

  @override
  void dispose() {
    _current.dispose();
    _next.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_current.text.isEmpty) {
      setState(() => _error = 'Isi sandi saat ini.');
      return;
    }
    final bad = validateNewPassword(_current.text, _next.text);
    if (bad != null) {
      setState(() => _error = bad);
      return;
    }
    if (_next.text != _confirm.text) {
      setState(() => _error = 'Ulangi sandi baru dengan sama persis.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    final err = await ref.read(authControllerProvider.notifier).changePassword(
      current: _current.text,
      next: _next.text,
    );
    if (!mounted) return;
    if (err != null) {
      setState(() {
        _busy = false;
        _error = err;
      });
      return;
    }
    setState(() => _busy = false);
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Sandi berhasil diganti.')));
    if (context.canPop()) {
      context.pop();
    } else {
      context.go('/');
    }
  }

  Widget _field(TextEditingController c, String label, int max, {TextInputAction? action}) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: TextField(
      controller: c,
      obscureText: !_show,
      enabled: !_busy,
      textInputAction: action ?? TextInputAction.next,
      inputFormatters: [LengthLimitingTextInputFormatter(max)],
      decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    final forced = auth is AuthAuthenticated && auth.user.mustChangePassword;
    return PopScope(
      canPop: !forced,
      child: Scaffold(
        appBar: AppBar(title: const Text('Ganti sandi'), automaticallyImplyLeading: !forced),
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (forced)
                const Padding(
                  padding: EdgeInsets.only(bottom: 16),
                  child: Text('Sandi Anda masih sementara. Ganti dulu dengan sandi baru sebelum memakai aplikasi.'),
                ),
              _field(_current, 'Sandi saat ini', 256),
              _field(_next, 'Sandi baru (minimal 8, huruf dan angka)', 128),
              _field(_confirm, 'Ulangi sandi baru', 128, action: TextInputAction.done),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: _show,
                onChanged: (v) => setState(() => _show = v ?? false),
                title: const Text('Tampilkan sandi'),
              ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ),
              const SizedBox(height: 8),
              SizedBox(
                height: 52,
                child: FilledButton(
                  onPressed: _busy ? null : _submit,
                  child: Text(_busy ? 'Menyimpan...' : 'Simpan sandi baru'),
                ),
              ),
              if (forced) ...[
                const SizedBox(height: 12),
                SizedBox(
                  height: 52,
                  child: OutlinedButton(
                    onPressed: _busy ? null : () => ref.read(authControllerProvider.notifier).logout(),
                    child: const Text('Keluar'),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
