import { formatDate } from "@/lib/format";
import { useAssignments, type Employee } from "@/services/employeeService";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";

/** Riwayat jabatan/penempatan (M2) — riwayat lama tetap tersimpan saat mutasi/promosi. */
export function AssignmentHistory({ employee }: { employee: Employee }) {
  const history = useAssignments(employee.id);
  return (
    <section aria-label="Riwayat jabatan" className="mb-8 max-w-xl">
      <TextBlock as="h2" className="mb-3 text-base font-semibold">Riwayat jabatan</TextBlock>
      <div className="rounded-panel border border-line bg-surface shadow-card px-5 py-2 text-sm">
        {history.isPending && <LoadingBar className="my-2 h-4 w-2/3" />}
        {history.isError && <TextBlock className="py-2 text-danger">Riwayat tidak dapat dimuat.</TextBlock>}
        {history.data?.length === 0 && <TextBlock className="py-2 text-mist">Belum ada riwayat penempatan.</TextBlock>}
        <ListBlock as="ol">
          {history.data?.map((a) => (
            <ListEntry key={a.id} className="flex flex-col gap-0.5 border-b border-line py-2 last:border-0 md:flex-row md:justify-between">
              <TextBlock as="span">
                <TextBlock as="span" className="font-medium">{a.position}</TextBlock>
                {a.unit_name && <TextBlock as="span" className="text-mist"> · {a.unit_name}</TextBlock>}
              </TextBlock>
              <TextBlock as="span" className="text-mist">
                {formatDate(a.valid_from)} – {a.valid_to ? formatDate(a.valid_to) : "sekarang"}
              </TextBlock>
            </ListEntry>
          ))}
        </ListBlock>
      </div>
    </section>
  );
}

