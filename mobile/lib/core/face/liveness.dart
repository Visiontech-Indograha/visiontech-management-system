import 'dart:math';

/// Satu tantangan keaslian wajah (anti foto layar). `id` HARUS sama dengan yang dikenali face-service
/// (`/face/challenge-check`): kiri, kanan, atas, buka_mulut, kedip. "depan" tidak dipakai sebagai tantangan.
class LivenessChallenge {
  const LivenessChallenge(
    this.id,
    this.instruction, {
    this.interval = const Duration(milliseconds: 700),
  });

  final String id;
  final String instruction;

  /// Jeda antar bingkai yang dikirim ke server. Kedip singkat sehingga butuh bingkai lebih rapat.
  final Duration interval;
}

const livenessChallenges = <LivenessChallenge>[
  LivenessChallenge('kiri', 'Tengokkan kepala sedikit ke KIRI'),
  LivenessChallenge('kanan', 'Tengokkan kepala sedikit ke KANAN'),
  LivenessChallenge('atas', 'Dongakkan kepala sedikit ke ATAS'),
  LivenessChallenge('buka_mulut', 'BUKA MULUT Anda'),
  LivenessChallenge(
    'kedip',
    'KEDIPKAN mata Anda',
    interval: Duration(milliseconds: 400),
  ),
];

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
