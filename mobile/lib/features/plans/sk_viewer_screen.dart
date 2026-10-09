import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';

/// "Tinjau SK" (alur SK v2, flowchart SK2-D): dokumen A4 yang sama persis dengan yang dilihat PM —
/// isi SK, tanda tangan PM/ketua beserta QR, dan statusnya. HTML diambil dengan token pengguna lalu
/// dirender di WebView tanpa JavaScript.
class SkViewerScreen extends ConsumerStatefulWidget {
  const SkViewerScreen({
    super.key,
    required this.planId,
    required this.title,
    this.htmlPath,
  });
  final String planId;
  final String title;

  /// Bila diisi: tampilkan HTML dari jalur API ini (mis. laporan yang disetujui), bukan dokumen SK.
  final String? htmlPath;

  @override
  ConsumerState<SkViewerScreen> createState() => _SkViewerScreenState();
}

class _SkViewerScreenState extends ConsumerState<SkViewerScreen> {
  final _controller = WebViewController()
    ..setJavaScriptMode(JavaScriptMode.disabled)
    ..setBackgroundColor(Colors.white);
  bool _loading = true;
  String? _error;
  String? _status;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(syncEngineProvider).api;
      if (widget.htmlPath != null) {
        await _controller.loadHtmlString(
          (await api.html(widget.htmlPath!)).replaceFirst(
            '<head>',
            '<head><meta name="viewport" content="width=820, initial-scale=0.4">',
          ),
        );
        return;
      }
      final docs = await api.planDocuments(widget.planId);
      if (docs.isEmpty) throw StateError('Dokumen rencana kerja belum terbit.');
      final latest =
          docs.last; // API mengurutkan versi naik; yang berlaku = terakhir
      final html = await api.documentHtml(latest['id'] as String);
      // Lebar A4 diskalakan ke layar HP.
      await _controller.loadHtmlString(
        html.replaceFirst(
          '<head>',
          '<head><meta name="viewport" content="width=820, initial-scale=0.4">',
        ),
      );
      if (mounted) setState(() => _status = latest['status'] as String?);
    } on StateError catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: VmsTopBar(
      onBack: () => Navigator.of(context).maybePop(),
      trailing: HeaderAction(
        icon: Icons.refresh_rounded,
        tooltip: 'Muat ulang',
        onTap: _load,
      ),
    ),
    body: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  widget.title,
                  style: VmsTextStyles.subheading.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              if (_status != null) StatusPill(_status),
            ],
          ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.all(16),
            child: NoticeBanner(
              icon: Icons.error_outline_rounded,
              text: _error!,
              accent: Accent.rose,
            ),
          ),
        Expanded(
          child: Stack(
            children: [
              WebViewWidget(controller: _controller),
              if (_loading) const Center(child: CircularProgressIndicator()),
            ],
          ),
        ),
      ],
    ),
  );
}
