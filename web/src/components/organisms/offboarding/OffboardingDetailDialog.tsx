import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { Pill } from "@/components/molecules/Pill";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { formatDate, formatDateTime } from "@/lib/format";
import {
  CONDITION_LABEL,
  REASON_LABEL,
  STATUS_LABEL,
  useApproveOffboarding,
  useCancelOffboarding,
  useOffboarding,
  useVerifyClearance,
  type ClearanceItem,
  type ClearanceVerify,
} from "@/services/offboardingService";
import { uploadFiles } from "@/services/uploadService";

/** Verifikasi satu barang: kondisi + foto serah terima (wajib kecuali hilang). */
function VerifyItemForm({ item, onDone }: { item: ClearanceItem; onDone: () => void }) {
  const verify = useVerifyClearance();
  const [condition, setCondition] = useState<ClearanceVerify["return_condition"]>("GOOD");
  const [photo, setPhoto] = useState<File | null>(null);

  const submit = async () => {
    if (condition !== "LOST" && !photo) {
      toast.error("Lampirkan foto serah terima.");
      return;
    }
    try {
      const [fileId] = photo ? await uploadFiles([photo]) : [];
      await verify.mutateAsync({
        itemId: item.clearance_item_id,
        body: { return_condition: condition, handover_file_id: fileId ?? null },
      });
      toast.success("Barang terverifikasi.");
      onDone();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <div className="mt-2 grid gap-2 sm:grid-cols-[10rem_1fr_auto] sm:items-end">
      <SelectField label="Kondisi" value={condition}
                   onChange={(e) => setCondition(e.target.value as ClearanceVerify["return_condition"])}>
        <ControlOption value="GOOD">Baik</ControlOption>
        <ControlOption value="DAMAGED">Rusak</ControlOption>
        <ControlOption value="LOST">Hilang</ControlOption>
      </SelectField>
      <TextField label="Foto serah terima" type="file" accept="image/*"
                 onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
      <ActionButton size="sm" disabled={verify.isPending} onClick={() => void submit()}>
        {verify.isPending ? "Menyimpan..." : "Verifikasi"}
      </ActionButton>
    </div>
  );
}

/** Detail offboarding: daftar barang (verifikasi HR/GA), persetujuan PM & HR, pembatalan. */
export function OffboardingDetailDialog({ offboardingId, canManage, canApprovePm, onClose }: {
  offboardingId: string;
  canManage: boolean;
  canApprovePm: boolean;
  onClose: () => void;
}) {
  const detail = useOffboarding(offboardingId);
  const approve = useApproveOffboarding();
  const cancel = useCancelOffboarding();
  const [verifying, setVerifying] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [approving, setApproving] = useState<"PM" | "HR" | null>(null);
  const o = detail.data;

  const doApprove = (approval_type: "PM" | "HR") =>
    approve.mutate({ id: offboardingId, approval_type }, {
      onSuccess: (r) => toast.success(r.status === "COMPLETED" ? "Offboarding selesai; akun dinonaktifkan." : "Disetujui."),
      onError: (err) => toast.error(errorMessage(err)),
    });

  const doCancel = () =>
    cancel.mutate({ id: offboardingId, reason: cancelReason.trim() }, {
      onSuccess: () => {
        toast.success("Offboarding dibatalkan.");
        onClose();
      },
      onError: (err) => toast.error(errorMessage(err)),
    });

  const approvable = !!o && o.is_all_assets_returned && (o.status === "SUBMITTED" || o.status === "APPROVED");

  return (
    <VmsDialog open title={o ? `Offboarding ${o.employee_name ?? ""}` : "Offboarding"} onClose={onClose}
               className="sm:max-w-3xl">
      {!o ? (
        <LoadingBar className="h-32 w-full" />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <TextBlock className="text-sm text-mist">
              {`${REASON_LABEL[o.reason_type] ?? o.reason_type} · efektif ${formatDate(o.effective_date)}`}
            </TextBlock>
            <Pill tone={o.status === "COMPLETED" ? "success" : o.status === "CLEARANCE_PENDING" ? "warning" : "info"}>
              {STATUS_LABEL[o.status] ?? o.status}
            </Pill>
          </div>
          {o.notes && <TextBlock className="whitespace-pre-line text-sm">{o.notes}</TextBlock>}

          <section aria-label="Clearance aset" className="space-y-2">
            <TextBlock as="h3" className="text-sm font-semibold">Pengembalian aset</TextBlock>
            {(o.clearance_items ?? []).length === 0 ? (
              <TextBlock className="text-sm text-mist">Tidak ada pinjaman aset yang perlu dikembalikan.</TextBlock>
            ) : (
              <ListBlock className="divide-y divide-line rounded-control border border-line">
                {o.clearance_items!.map((item) => (
                  <ListEntry key={item.clearance_item_id} className="p-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <TextBlock as="span">
                        {`${item.asset_name ?? "Aset"} (${item.asset_code ?? "-"}) · dipinjam ${formatDate(item.loaned_at)}`}
                      </TextBlock>
                      {item.verified_at ? (
                        <TextBlock as="span" className="text-xs text-mist">
                          {`${CONDITION_LABEL[item.return_condition] ?? item.return_condition} · ${item.verified_by_name ?? "-"} · ${formatDateTime(item.verified_at)}`}
                        </TextBlock>
                      ) : canManage && o.status === "CLEARANCE_PENDING" && verifying !== item.clearance_item_id ? (
                        <ActionButton size="sm" variant="outline" onClick={() => setVerifying(item.clearance_item_id)}>
                          Terima barang
                        </ActionButton>
                      ) : (
                        <Pill tone="warning">Belum dikembalikan</Pill>
                      )}
                    </div>
                    {verifying === item.clearance_item_id && (
                      <VerifyItemForm item={item} onDone={() => setVerifying(null)} />
                    )}
                  </ListEntry>
                ))}
              </ListBlock>
            )}
          </section>

          <section aria-label="Persetujuan" className="space-y-2">
            <TextBlock as="h3" className="text-sm font-semibold">Persetujuan</TextBlock>
            <TextBlock className="text-sm">
              {`PM/OM: ${o.approved_by_pm_name ?? "belum"} · HR: ${o.approved_by_hr_name ?? "belum"}`}
            </TextBlock>
            {o.status !== "COMPLETED" && (
              <div className="flex flex-wrap gap-2">
                {canApprovePm && !o.approved_by_pm_id && (
                  <ActionButton size="sm" disabled={!approvable || approve.isPending} onClick={() => setApproving("PM")}>
                    Setujui sebagai PM
                  </ActionButton>
                )}
                {canManage && !o.approved_by_hr_id && (
                  <ActionButton size="sm" disabled={!approvable || approve.isPending} onClick={() => setApproving("HR")}>
                    Setujui sebagai HR
                  </ActionButton>
                )}
              </div>
            )}
            {!approvable && o.status === "CLEARANCE_PENDING" && (
              <TextBlock className="text-xs text-mist">Persetujuan terbuka setelah semua barang diverifikasi.</TextBlock>
            )}
          </section>

          {canManage && o.status !== "COMPLETED" && (
            <section aria-label="Batalkan" className="space-y-2 border-t border-line pt-3">
              {confirmCancel ? (
                <div className="grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
                  <TextField label="Alasan pembatalan" value={cancelReason}
                             onChange={(e) => setCancelReason(e.target.value)} />
                  <ActionButton size="sm" variant="destructive"
                                disabled={cancelReason.trim().length < 3 || cancel.isPending} onClick={doCancel}>
                    Ya, batalkan
                  </ActionButton>
                </div>
              ) : (
                <ActionButton size="sm" variant="outline" onClick={() => setConfirmCancel(true)}>
                  Batalkan offboarding
                </ActionButton>
              )}
            </section>
          )}
        </div>
      )}
      <ConfirmDialog
        open={approving !== null}
        title={approving === "HR" ? "Setujui sebagai HR?" : "Setujui sebagai PM?"}
        message="Persetujuan tidak dapat dibatalkan. Bila ini persetujuan terakhir, akun karyawan akan dinonaktifkan."
        confirmLabel="Setujui"
        busy={approve.isPending}
        onConfirm={() => {
          if (approving) doApprove(approving);
          setApproving(null);
        }}
        onClose={() => setApproving(null)}
      />
    </VmsDialog>
  );
}
