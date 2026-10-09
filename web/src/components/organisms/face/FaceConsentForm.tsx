import { useState } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { CheckControl } from "@/components/molecules/CheckControl";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ControlLabel } from "@/components/molecules/FormBlock";

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
      <TextBlock as="h2" className="text-sm font-medium">Persetujuan Pemrosesan Biometrik</TextBlock>
      <TextBlock className="rounded border border-line bg-surface p-2.5 text-xs leading-relaxed text-mist">
        {policyText}
      </TextBlock>
      <div className="flex items-center gap-2">
        <CheckControl id="gate-consent" checked={agreed} onCheckedChange={(c) => setAgreed(!!c)} />
        <ControlLabel htmlFor="gate-consent" className="cursor-pointer text-xs">
          Saya menyetujui pemrosesan data biometrik wajah untuk verifikasi kehadiran.
        </ControlLabel>
      </div>
      <ActionButton disabled={!agreed || pending} onClick={onGrant}>
        {pending ? "Menyimpan..." : "Setuju dan Lanjut"}
      </ActionButton>
    </>
  );
}
