import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextAreaField } from "@/components/molecules/Field";
import { TextBlock } from "@/components/molecules/TextBlock";
import { errorMessage } from "@/lib/errors";
import { useLoanRequests, useLoans, useReviewLoanRequest, type Loan, type LoanRequest } from "@/services/assetService";
import { AssetFormDialog } from "./AssetFormDialog";

const CONDITION: Record<string, string> = { ready: "baik", damaged: "rusak", lost: "hilang" };

/** HR/GA memutuskan pengajuan pinjam karyawan dan menerima pengembalian yang sudah diajukan dari HP. */
export function LoanRequestsPanel({ onReceive }: { onReceive: (loan: Loan) => void }) {
  const requests = useLoanRequests("PENDING");
  const loans = useLoans(true);
  const [rejecting, setRejecting] = useState<LoanRequest | null>(null);
  const review = useReviewLoanRequest();
  const returns = (loans.data ?? []).filter((l) => l.return_requested_at);
  const pending = requests.data ?? [];
  if (!pending.length && !returns.length) return null;

  const approve = async (r: LoanRequest) => {
    try {
      await review.mutateAsync({ id: r.request_id, decision: "APPROVED" });
      toast.success(`${r.asset_name} diserahkan ke ${r.employee_name}.`);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <section aria-label="Permintaan karyawan" className="mb-4 flex flex-col gap-3 rounded-panel border border-line bg-surface p-4 shadow-card">
      {pending.length > 0 && (
        <div className="flex flex-col gap-2">
          <TextBlock as="h2" className="text-sm font-semibold">Pengajuan pinjam menunggu keputusan ({pending.length})</TextBlock>
          {pending.map((r) => (
            <div key={r.request_id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <div>
                <TextBlock as="strong" className="font-medium">{r.asset_name} ({r.asset_code}) — {r.employee_name}</TextBlock>
                <TextBlock className="text-mist">{r.purpose}</TextBlock>
              </div>
              <div className="flex gap-2">
                <ActionButton size="sm" disabled={review.isPending} onClick={() => approve(r)}>
                  Setujui & serahkan
                </ActionButton>
                <ActionButton size="sm" variant="outline" disabled={review.isPending} onClick={() => setRejecting(r)}>
                  Tolak
                </ActionButton>
              </div>
            </div>
          ))}
        </div>
      )}
      {returns.length > 0 && (
        <div className="flex flex-col gap-2">
          <TextBlock as="h2" className="text-sm font-semibold">Pengembalian diajukan karyawan ({returns.length})</TextBlock>
          {returns.map((l) => (
            <div key={l.assignment_id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <div>
                <TextBlock as="strong" className="font-medium">{l.asset_name} ({l.asset_code}) — {l.employee_name}</TextBlock>
                <TextBlock className="text-mist">
                  Kondisi dilaporkan: {CONDITION[l.return_condition ?? "ready"]}
                  {l.return_note ? ` · ${l.return_note}` : ""}
                </TextBlock>
              </div>
              <ActionButton size="sm" onClick={() => onReceive(l)}>
                Periksa & terima
              </ActionButton>
            </div>
          ))}
        </div>
      )}
      {rejecting && <RejectDialog request={rejecting} onClose={() => setRejecting(null)} />}
    </section>
  );
}

function RejectDialog({ request, onClose }: { request: LoanRequest; onClose: () => void }) {
  const review = useReviewLoanRequest();
  const [note, setNote] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);
    try {
      await review.mutateAsync({ id: request.request_id, decision: "REJECTED", note: note.trim() || undefined });
      toast.success("Pengajuan ditolak.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  };
  return (
    <AssetFormDialog
      title={`Tolak pengajuan ${request.asset_name}`}
      submitLabel="Tolak pengajuan"
      submitting={review.isPending}
      formError={formError}
      onClose={onClose}
      onSubmit={onSubmit}
    >
      <TextAreaField label="Alasan (opsional)" value={note} onChange={(e) => setNote(e.target.value)} />
    </AssetFormDialog>
  );
}
