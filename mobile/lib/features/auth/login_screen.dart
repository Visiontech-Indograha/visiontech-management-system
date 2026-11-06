import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart' show SurfaceCard, logoAsset;

import 'auth_controller.dart';
import 'auth_state.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;
  final _emailFocus = FocusNode();
  final _passwordFocus = FocusNode();
  // Saat keyboard terbuka, layar digulir ke bawah agar tombol Masuk tetap terlihat.
  final _scroll = ScrollController();

  /// Detak per detik untuk hitung mundur cooldown login (R-21); hanya hidup
  /// selama akun terkunci.
  Timer? _ticker;

  @override
  void initState() {
    super.initState();
    _emailFocus.addListener(_onFokus);
    _passwordFocus.addListener(_onFokus);
  }

  void _onFokus() {
    if (!(_emailFocus.hasFocus || _passwordFocus.hasFocus)) return;
    // Beri waktu keyboard selesai naik sebelum menggulir.
    Future<void>.delayed(const Duration(milliseconds: 350), () {
      if (mounted && _scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    _ticker?.cancel();
    _emailFocus.dispose();
    _passwordFocus.dispose();
    _scroll.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _syncTicker(bool locked) {
    if (locked && _ticker == null) {
      _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
        if (mounted) setState(() {});
      });
    } else if (!locked && _ticker != null) {
      _ticker!.cancel();
      _ticker = null;
    }
  }

  static String _mmss(Duration d) {
    final m = d.inMinutes.toString().padLeft(2, '0');
    final s = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  void _submit() {
    if (_lockRemaining() != null) return;
    if (!_formKey.currentState!.validate()) return;
    ref
        .read(authControllerProvider.notifier)
        .login(
          username: _usernameController.text.trim(),
          password: _passwordController.text,
        );
  }

  /// Sisa cooldown, atau null bila tidak sedang terkunci.
  Duration? _lockRemaining() {
    final auth = ref.read(authControllerProvider);
    final until = auth is AuthUnauthenticated ? auth.lockedUntil : null;
    if (until == null) return null;
    final left = until.difference(DateTime.now());
    return left > Duration.zero ? left : null;
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final isLoading = authState is AuthLoading;
    final errorMessage = authState is AuthUnauthenticated
        ? authState.error
        : null;
    final lockRemaining = _lockRemaining();
    _syncTicker(lockRemaining != null);
    final theme = ShadTheme.of(context);

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.dark.copyWith(
        statusBarColor: Colors.transparent,
      ),
      child: Scaffold(
        backgroundColor: VmsColors.neutral50,
        body: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              controller: _scroll,
              keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
              padding: const EdgeInsets.all(20),
              // Masuk sekali: fade + naik (transform/opacity saja, ringan) — R-13/R-14.
              child: TweenAnimationBuilder<double>(
                tween: Tween(begin: 0, end: 1),
                duration: const Duration(milliseconds: 420),
                curve: Curves.easeOutCubic,
                builder: (context, t, child) => Opacity(
                  opacity: t,
                  child: Transform.translate(
                    offset: Offset(0, 16 * (1 - t)),
                    child: child,
                  ),
                ),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Image.asset(
                          logoAsset,
                          height: 32,
                          fit: BoxFit.contain,
                          semanticLabel: 'Visiontech Indograha',
                        ),
                      ),
                      const SizedBox(height: 28),
                      // Kartu sambutan navy + swirl emas (warna logo; gaya rujukan Dribbble, R-14).
                      SurfaceCard(
                        highlight: true,
                        padding: const EdgeInsets.fromLTRB(20, 22, 20, 24),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Aplikasi lapangan',
                              style: VmsTextStyles.bodySm.copyWith(
                                color: VmsColors.gold,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              'Selamat datang',
                              style: VmsTextStyles.titleLg.copyWith(
                                color: Colors.white,
                                fontWeight: FontWeight.w800,
                                fontSize: 28,
                                letterSpacing: -0.6,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Padding(
                              padding: const EdgeInsets.only(right: 72),
                              child: Text(
                                'Absensi, surat kerja, dan laporan harian dalam satu genggaman.',
                                style: VmsTextStyles.bodySm.copyWith(
                                  color: Colors.white.withValues(alpha: 0.78),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      ShadCard(
                        radius: BorderRadius.circular(22),
                        shadows: const [],
                        title: Text(
                          'Masuk',
                          style: theme.textTheme.h4.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        description: const Text(
                          'Masuk dengan email dan sandi akun kantor Anda.',
                        ),
                        child: Padding(
                          padding: const EdgeInsets.only(top: 16),
                          child: Form(
                            key: _formKey,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                if (lockRemaining != null) ...[
                                  ShadAlert.destructive(
                                    key: const Key('login-locked'),
                                    icon: const Icon(LucideIcons.timer),
                                    title: const Text(
                                      'Login dikunci sementara',
                                    ),
                                    description: Text(
                                      'Terlalu banyak percobaan gagal. Coba lagi '
                                      'dalam ${_mmss(lockRemaining)}.',
                                    ),
                                  ),
                                  const SizedBox(height: 12),
                                ] else if (errorMessage != null) ...[
                                  ShadAlert.destructive(
                                    icon: const Icon(LucideIcons.circleAlert),
                                    description: Text(errorMessage),
                                  ),
                                  const SizedBox(height: 12),
                                ],
                                ShadInputFormField(
                                  controller: _usernameController,
                                  focusNode: _emailFocus,
                                  enabled: !isLoading,
                                  label: const Text('Email'),
                                  placeholder: const Text('nama@visiontech.id'),
                                  keyboardType: TextInputType.emailAddress,
                                  textInputAction: TextInputAction.next,
                                  onSubmitted: (_) => _passwordFocus.requestFocus(),
                                  leading: const Icon(
                                    LucideIcons.mail,
                                    size: 18,
                                  ),
                                  validator: (v) => v.trim().isEmpty
                                      ? 'Email wajib diisi'
                                      : null,
                                ),
                                const SizedBox(height: 12),
                                ShadInputFormField(
                                  controller: _passwordController,
                                  focusNode: _passwordFocus,
                                  enabled: !isLoading,
                                  label: const Text('Sandi'),
                                  obscureText: _obscurePassword,
                                  textInputAction: TextInputAction.go,
                                  onSubmitted: (_) => _submit(),
                                  leading: const Icon(
                                    LucideIcons.lock,
                                    size: 18,
                                  ),
                                  trailing: ShadIconButton.ghost(
                                    width: 28,
                                    height: 28,
                                    padding: EdgeInsets.zero,
                                    icon: Icon(
                                      _obscurePassword
                                          ? LucideIcons.eye
                                          : LucideIcons.eyeOff,
                                      size: 18,
                                    ),
                                    onPressed: () => setState(
                                      () =>
                                          _obscurePassword = !_obscurePassword,
                                    ),
                                  ),
                                  validator: (v) =>
                                      v.isEmpty ? 'Sandi wajib diisi' : null,
                                ),
                                const SizedBox(height: 20),
                                ShadButton(
                                  height: 54,
                                  onPressed: isLoading || lockRemaining != null
                                      ? null
                                      : _submit,
                                  leading: isLoading
                                      ? const SizedBox.square(
                                          dimension: 16,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            color: Colors.white,
                                          ),
                                        )
                                      : null,
                                  child: Text(
                                    isLoading
                                        ? 'Memproses...'
                                        : lockRemaining != null
                                        ? 'Tunggu ${_mmss(lockRemaining)}'
                                        : 'Masuk',
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
