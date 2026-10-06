import 'dart:math';

import 'package:flutter/material.dart' show IconData, Icons;

/// Satu tantangan keaslian wajah (anti foto layar). `id` HARUS sama dengan yang dikenali face-service
/// (`/face/challenge-check`): kiri, kanan, atas, bawah, buka_mulut. Kedip sengaja tidak dipakai (sulit dideteksi
/// andal). "depan" hanya panduan meluruskan wajah, bukan bukti liveness.
class LivenessChallenge {
  const LivenessChallenge(
    this.id,
    this.instruction,
    this.icon, {
    this.interval = const Duration(milliseconds: 450),
  });

  final String id;
  final String instruction;

  /// Ikon besar di layar kamera supaya arah tantangan langsung terbedakan (panah ke sisi pengguna).
  final IconData icon;

  /// Jeda antar bingkai yang dikirim ke server.
  final Duration interval;
}

const livenessChallenges = <LivenessChallenge>[
  LivenessChallenge('kiri', 'Tengokkan kepala ke KIRI', Icons.arrow_back_rounded),
  LivenessChallenge('kanan', 'Tengokkan kepala ke KANAN', Icons.arrow_forward_rounded),
  LivenessChallenge('atas', 'Dongakkan kepala ke ATAS', Icons.arrow_upward_rounded),
  LivenessChallenge('bawah', 'Tundukkan kepala ke BAWAH', Icons.arrow_downward_rounded),
  LivenessChallenge('buka_mulut', 'BUKA MULUT Anda', Icons.sentiment_satisfied_alt_rounded),
];

/// Langkah penutup setelah semua tantangan lolos: arahkan pengguna meluruskan wajah sebelum gambar diambil.
/// TIDAK menghasilkan bukti (server tidak menerbitkannya untuk "depan").
const straightenStep = LivenessChallenge(
  'depan',
  'Hadap lurus ke kamera',
  Icons.face_rounded,
  interval: Duration(milliseconds: 350),
);

/// Jumlah tantangan BERBEDA yang harus lolos (server mensyaratkan jumlah yang sama).
const livenessChallengeCount = 2;

/// Pilih tantangan acak yang berbeda satu sama lain: urutan tak bisa ditebak, rekaman lama tak bisa diputar ulang.
List<LivenessChallenge> pickLivenessChallenges(
  Random rng, {
  int count = livenessChallengeCount,
}) {
  final pool = [...livenessChallenges]..shuffle(rng);
  return pool.take(count).toList();
}

/// Isi `liveness` untuk /face/probe dan /face/enroll. `proofs` = bukti bertanda tangan server dari
/// /face/challenge-check (satu per tantangan lolos); hanya itu yang dipercaya server untuk absen ONLINE.
Map<String, dynamic> livenessPayload({
  required List<String> challenges,
  required List<String> proofs,
}) => {
  'challenges': challenges,
  'passed': proofs.length >= livenessChallengeCount,
  'proofs': proofs,
};

/// Pesan petunjuk dari server tanpa awalan teknis "Tantangan Gagal: ".
String friendlyChallengeHint(String serverDetail) =>
    serverDetail.replaceFirst(RegExp(r'^Tantangan Gagal:\s*'), '');
