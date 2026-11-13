import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useAutoMap, useMappingSuggestions } from "@/services/hikvisionService";

/** "Cocokkan otomatis": lihat usulan dan yang tidak cocok dulu, baru terapkan. */
export function MappingAutoDialog({ deviceId, onClose }: { deviceId: string; onClose: () => void }) {
  const suggestions = useMappingSuggestions(deviceId, true);
  const auto = useAutoMap(deviceId);
  const [error, setError] = useState<string | null>(null);
  const apply = async () => {
    setError(null);
    try {
      const r = await auto.mutateAsync();
      toast.success(`${r.dibuat} pemetaan dibuat.${r.masih_ada_sisa ? " Masih ada data lama; jalankan lagi bila perlu." : ""}`);
      onClose();
    } catch (err) {
      setError(errorMessage(err, "Belum bisa mencocokkan. Coba lagi."));
    }
  };
  const s = suggestions.data;
  const busy = auto.isPending;
  return (
    <VmsDialog
      open
      title="Cocokkan otomatis"
      onClose={() => !busy && onClose()}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={busy}>Batal</ActionButton>
          <ActionButton onClick={apply} disabled={busy || !s || s.cocok.length === 0}>
            {busy ? "Memproses..." : "Terapkan yang cocok"}
          </ActionButton>
        </>
      }
    >
      <FormErrorText message={error} />
      {suggestions.isPending && <LoadingBar aria-hidden className="h-24" />}
      {suggestions.isError && <RetryNotice message="Usulan belum bisa dimuat." onRetry={() => suggestions.refetch()} />}
      {s && (
        <div className="space-y-4">
          <TextBlock className="text-sm">
            {s.cocok.length} nomor cocok dengan karyawan, {s.tidak_cocok.length} tidak cocok. Periksa dulu sebelum diterapkan.
          </TextBlock>
          {s.cocok.length === 0 && <TextBlock className="text-sm text-mist">Belum ada yang cocok. Tambahkan pemetaan satu per satu.</TextBlock>}
          <ListBlock className="space-y-1">
            {s.cocok.map((c) => (
              <ListEntry key={c.employee_no_string} className="text-sm">
                {c.employee_no_string} {"->"} {c.full_name} ({c.employee_no}) · {c.jumlah_event} data
              </ListEntry>
            ))}
          </ListBlock>
          {s.tidak_cocok.length > 0 && (
            <div>
              <TextBlock className="mb-1 text-sm font-medium text-warning">Tidak cocok, perlu dipetakan sendiri</TextBlock>
              <ListBlock className="space-y-1">
                {s.tidak_cocok.map((t) => (
                  <ListEntry key={t.employee_no_string} className="text-sm text-mist">
                    {t.employee_no_string} · {t.jumlah_event} data · {t.alasan}
                  </ListEntry>
                ))}
              </ListBlock>
            </div>
          )}
        </div>
      )}
    </VmsDialog>
  );
}
