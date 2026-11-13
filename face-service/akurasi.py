"""Harness pengukuran FAR/FRR pencocokan wajah (rencana: docs/rencana/akurasi-wajah.md).

Murni Python. Dua sumber skor:
  - sintetis (`--sintetis`): identitas buatan, derau naik per kondisi (frontal, miring, redup). Hanya untuk
    menguji harness dan memberi gambaran bentuk kurva; BUKAN bukti akurasi model.
  - berkas JSON (`--skor berkas.json`): {"kondisi": {"genuine": [..kosinus..], "impostor": [..]}} dari embedding nyata
    yang dihitung pemilik (swafoto persetujuan), tanpa menyimpan wajah di repo.
FAR = impostor yang lolos / seluruh impostor. FRR = genuine yang ditolak / seluruh genuine. Lolos bila skor >= ambang.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / (na * nb) if na and nb else 0.0


def far_frr(genuine: Sequence[float], impostor: Sequence[float], threshold: float) -> tuple[float, float]:
    far = sum(1 for s in impostor if s >= threshold) / len(impostor) if impostor else 0.0
    frr = sum(1 for s in genuine if s < threshold) / len(genuine) if genuine else 0.0
    return far, frr


@dataclass(frozen=True)
class Point:
    threshold: float
    far: float
    frr: float


def sweep(genuine: Sequence[float], impostor: Sequence[float], lo: float = 0.0, hi: float = 1.0,
          step: float = 0.01) -> list[Point]:
    n = round((hi - lo) / step)
    out = []
    for i in range(n + 1):
        t = round(lo + i * step, 6)
        far, frr = far_frr(genuine, impostor, t)
        out.append(Point(t, far, frr))
    return out


def eer(points: Sequence[Point]) -> Point:
    """Titik tempat FAR dan FRR paling dekat (equal error rate)."""
    return min(points, key=lambda p: (abs(p.far - p.frr), p.threshold))


def threshold_for_far(points: Sequence[Point], max_far: float) -> Point | None:
    """Ambang TERENDAH yang FAR-nya <= max_far (FRR terkecil pada batas keamanan itu). None bila tak ada."""
    ok = [p for p in points if p.far <= max_far]
    return min(ok, key=lambda p: p.threshold) if ok else None


# --- data sintetis -------------------------------------------------------------------------------------------

NOISE_BY_CONDITION = {"frontal": 0.4, "miring": 1.0, "redup": 1.8}   # simpangan derau relatif terhadap identitas


def synthetic_scores(seed: int = 7, identities: int = 60, per_identity: int = 10, dim: int = 24,
                     noise: dict[str, float] | None = None) -> dict[str, dict[str, list[float]]]:
    """Skor kosinus genuine (swafoto vs templat sendiri) dan impostor (vs templat orang lain) per kondisi.

    Templat = rata-rata 3 foto frontal; swafoto = identitas + derau kondisi. Deterministik menurut seed.
    """
    rng = random.Random(seed)
    noise = noise or NOISE_BY_CONDITION
    ids = [[rng.gauss(0.0, 1.0) for _ in range(dim)] for _ in range(identities)]
    templates = []
    for ident in ids:
        shots = [[x + rng.gauss(0, noise["frontal"]) for x in ident] for _ in range(3)]
        templates.append([sum(col) / 3 for col in zip(*shots, strict=True)])
    result: dict[str, dict[str, list[float]]] = {}
    for cond, sigma in noise.items():
        gen: list[float] = []
        imp: list[float] = []
        for i, ident in enumerate(ids):
            for _ in range(per_identity):
                probe = [x + rng.gauss(0, sigma) for x in ident]
                gen.append(cosine(probe, templates[i]))
                other = (i + 1 + rng.randrange(identities - 1)) % identities
                imp.append(cosine(probe, templates[other]))
        result[cond] = {"genuine": gen, "impostor": imp}
    return result


def report(scores: dict[str, dict[str, list[float]]], current_threshold: float, max_far: float = 0.001) -> str:
    th = f"{current_threshold:.2f}"
    lines = [f"| kondisi | n genuine | n impostor | FAR@{th} | FRR@{th} | EER (ambang) | ambang untuk FAR<={max_far:g} (FRR) |",
             "|---|---|---|---|---|---|---|"]
    for cond, s in scores.items():
        pts = sweep(s["genuine"], s["impostor"])
        far, frr = far_frr(s["genuine"], s["impostor"], current_threshold)
        e = eer(pts)
        t = threshold_for_far(pts, max_far)
        tgt = f"{t.threshold:.2f} ({t.frr:.1%})" if t else "tidak ada"
        lines.append(f"| {cond} | {len(s['genuine'])} | {len(s['impostor'])} | {far:.2%} | {frr:.2%} | "
                     f"{(e.far + e.frr) / 2:.2%} ({e.threshold:.2f}) | {tgt} |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--sintetis", action="store_true", help="dataset buatan (hanya uji harness)")
    src.add_argument("--skor", help="berkas JSON skor nyata per kondisi")
    ap.add_argument("--ambang", type=float, default=0.80, help="ambang produksi saat ini (MATCH_THRESHOLD)")
    ap.add_argument("--max-far", type=float, default=0.001)
    args = ap.parse_args()
    if args.sintetis:
        scores = synthetic_scores()
    else:
        with open(args.skor, encoding="utf-8") as fh:
            scores = json.load(fh)
    print(report(scores, args.ambang, args.max_far))


if __name__ == "__main__":
    main()
