import { useState } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { CheckCircle2 } from "@/components/molecules/Glyphs";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";

/** Tombol "Setujui hasil survei" dengan konfirmasi: persetujuan mengunci titik dan tidak bisa dibatalkan. */
export function SurveyApproveButton({ pending, onApprove }: { pending: boolean; onApprove: () => Promise<void> }) {
  const [asking, setAsking] = useState(false);
  const approve = async () => {
    await onApprove();
    setAsking(false);
  };
  return (
    <>
      <ActionButton type="button" className="w-full" disabled={pending} onClick={() => setAsking(true)}>
        <CheckCircle2 className="h-4 w-4" aria-hidden />
        {pending ? "Memproses persetujuan..." : "Setujui hasil survei dan kunci tugas"}
      </ActionButton>
      <ConfirmDialog
        open={asking}
        title="Setujui hasil survei?"
        message="Titik survei akan dikunci dan tugas disalin ke jadwal harian. Persetujuan ini tidak bisa dibatalkan."
        confirmLabel="Ya, setujui"
        busy={pending}
        onConfirm={approve}
        onClose={() => setAsking(false)}
      />
    </>
  );
}
