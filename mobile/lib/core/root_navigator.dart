import 'package:flutter/widgets.dart';

/// Navigator akar aplikasi (GoRouter). Dipakai gerbang yang harus tampil di atas SEMUA layar
/// dan menangkap tombol back sistem, mis. popup K3 wajib baca.
final GlobalKey<NavigatorState> rootNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'root');
