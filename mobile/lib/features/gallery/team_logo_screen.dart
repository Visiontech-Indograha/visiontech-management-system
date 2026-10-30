import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/error_message.dart';
import '../../core/team_logo.dart';
import '../../shared/ui/vms_ui.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';

/// Celah uji: bila diisi, pemilihan gambar memakai hasil ini (bukan galeri/kamera HP).
@visibleForTesting
Future<(String, Uint8List)?> Function(ImageSource source)? teamLogoPickOverride;

const _defaultLogoAsset = 'assets/branding/logo_visiontech.png';

/// Pengaturan "Logo tim" (dari galeri). Ketua tim: pilih, pratinjau, simpan, hapus.
/// Anggota tim: hanya melihat logo yang sedang dipakai.
class TeamLogoScreen extends ConsumerStatefulWidget {
  const TeamLogoScreen({super.key});

  @override
  ConsumerState<TeamLogoScreen> createState() => _TeamLogoScreenState();
}

class _TeamLogoScreenState extends ConsumerState<TeamLogoScreen> {
  Uint8List? _pending; // pilihan baru yang sudah lolos validasi, belum disimpan
  String? _pendingName;
  String? _pendingError; // galat validasi pilihan terakhir
  bool _busy = false;

  String get _me {
    final auth = ref.read(authControllerProvider);
    return auth is AuthAuthenticated ? auth.user.employeeId : '';
  }

  Future<void> _pick(ImageSource source) async {
    final override = teamLogoPickOverride;
    final picked = override != null
        ? await override(source)
        : await _pickFromDevice(source);
    if (picked == null || !mounted) return; // dibatalkan
    final (name, bytes) = picked;
    final error = await validateTeamLogo(bytes);
    if (!mounted) return;
    setState(() {
      _pendingError = error;
      _pending = error == null ? bytes : null;
      _pendingName = error == null ? name : null;
    });
  }

  Future<(String, Uint8List)?> _pickFromDevice(ImageSource source) async {
    // Tanpa resize: validasi dimensi memakai gambar asli.
    final file = await ImagePicker().pickImage(source: source);
    if (file == null) return null;
    return (file.name, await file.readAsBytes());
  }

  String _errorText(Object e) {
    if (e is DioException && e.response?.statusCode == 403) {
      return 'Hanya ketua tim yang dapat mengganti logo';
    }
    return apiErrorMessage(e);
  }

  Future<void> _save(MyTeam team) async {
    final bytes = _pending;
    if (bytes == null) return;
    setState(() => _busy = true);
    try {
      await ref
          .read(teamLogoServiceProvider)
          .upload(team.teamId, bytes, _pendingName ?? 'logo_tim.png');
      ref.invalidate(teamLogoProvider(team.teamId));
      if (!mounted) return;
      setState(() {
        _pending = null;
        _pendingName = null;
      });
      showVmsToast(context, 'Logo tim disimpan.');
    } catch (e) {
      if (mounted) showVmsToast(context, _errorText(e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _remove(MyTeam team) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Hapus logo tim?'),
        content: const Text(
          'Logo kembali ke logo default Visiontech pada foto dan kartu tim.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Batal'),
          ),
          TextButton(
            key: const Key('team-logo-delete-confirm'),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Hapus'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      await ref.read(teamLogoServiceProvider).remove(team.teamId);
      ref.invalidate(teamLogoProvider(team.teamId));
      if (mounted) showVmsToast(context, 'Logo tim dihapus.');
    } catch (e) {
      if (mounted) showVmsToast(context, _errorText(e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final teamAsync = ref.watch(myTeamProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Logo tim')),
      body: teamAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(apiErrorMessage(e)),
          ),
        ),
        data: (team) => team == null
            ? const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'Logo tim tersedia setelah Anda terdaftar di tim pada jadwal harian.',
                    textAlign: TextAlign.center,
                  ),
                ),
              )
            : _body(context, team),
      ),
    );
  }

  Widget _body(BuildContext context, MyTeam team) {
    final logo = ref.watch(teamLogoProvider(team.teamId));
    final current = logo.value;
    final isLeader = team.leaderEmployeeId != null &&
        team.leaderEmployeeId == _me;
    final text = Theme.of(context).textTheme;

    final Widget preview = _pending != null
        ? Image.memory(_pending!, fit: BoxFit.contain)
        : current != null
        ? Image.memory(current, fit: BoxFit.contain)
        : Image.asset(_defaultLogoAsset, fit: BoxFit.contain);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Tim ${team.teamName}', style: text.titleMedium),
        const SizedBox(height: 12),
        Container(
          key: const Key('team-logo-preview'),
          height: 180,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: Colors.grey.shade400),
          ),
          child: logo.isLoading && _pending == null
              ? const Center(child: CircularProgressIndicator())
              : preview,
        ),
        const SizedBox(height: 8),
        Text(
          _pending != null
              ? 'Pratinjau (belum disimpan). Rasio gambar dipertahankan.'
              : current != null
              ? 'Logo tim yang sedang dipakai.'
              : 'Belum ada logo tim. Logo default Visiontech dipakai.',
          style: text.bodySmall,
        ),
        if (_pendingError != null) ...[
          const SizedBox(height: 8),
          Text(
            _pendingError!,
            key: const Key('team-logo-error'),
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
        ],
        const SizedBox(height: 16),
        if (!isLeader)
          const Text(
            'Hanya ketua tim yang dapat mengganti logo.',
            key: Key('team-logo-readonly'),
          )
        else ...[
          const Text(
            'Format PNG, JPEG, atau WebP · maksimal 2 MB · sisi 64–4000 px.',
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton.icon(
                key: const Key('team-logo-pick-gallery'),
                onPressed: _busy ? null : () => _pick(ImageSource.gallery),
                icon: const Icon(Icons.photo_library_outlined),
                label: const Text('Pilih dari galeri'),
              ),
              OutlinedButton.icon(
                key: const Key('team-logo-pick-camera'),
                onPressed: _busy ? null : () => _pick(ImageSource.camera),
                icon: const Icon(Icons.photo_camera_outlined),
                label: const Text('Ambil foto'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_pending != null)
            FilledButton.icon(
              key: const Key('team-logo-save'),
              onPressed: _busy ? null : () => _save(team),
              icon: const Icon(Icons.save_outlined),
              label: Text(_busy ? 'Menyimpan...' : 'Simpan logo'),
            ),
          if (current != null && _pending == null)
            TextButton.icon(
              key: const Key('team-logo-delete'),
              onPressed: _busy ? null : () => _remove(team),
              icon: const Icon(Icons.delete_outline_rounded),
              label: const Text('Hapus logo (kembali ke default)'),
            ),
        ],
      ],
    );
  }
}
