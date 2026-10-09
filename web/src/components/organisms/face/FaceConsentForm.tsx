import { useState } from "react";
import { Button } from "@/components/atoms/Button";
import { Checkbox } from "@/components/atoms/Checkbox";

/**
 * Persetujuan pemrosesan biometrik: teks kebijakan, centang setuju, tombol lanjut.
 * Centang adalah state lokal; persetujuan dikirim Page lewat `onGrant`.
 */
export function FaceConsentForm({ policyText, pending, onGrant }: {
  policyText: string;
  pending: boolean;
  onGrant: () => void;
}) {
  const [agreed, setAgreed] = useState(false);
  return (
    <>
      <h2 className="text-sm font-medium">Persetujuan Pemrosesan Biometrik</h2>
      <p className="rounded border border-line bg-surface p-2.5 text-xs leading-relaxed text-mist">
        {policyText}
      </p>
      <div className="flex items-center gap-2">
        <Checkbox id="gate-consent" checked={agreed} onCheckedChange={(c) => setAgreed(!!c)} />
        <label htmlFor="gate-consent" className="cursor-pointer text-xs">
          Saya menyetujui pemrosesan data biometrik wajah untuk verifikasi kehadiran.
        </label>
      </div>
      <Button disabled={!agreed || pending} onClick={onGrant}>
        {pending ? "Menyimpan..." : "Setuju dan Lanjut"}
      </Button>
    </>
  );
}
