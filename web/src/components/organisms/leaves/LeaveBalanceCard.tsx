import type { UseQueryResult } from "@tanstack/react-query";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { Calendar, CheckCircle2, AlertCircle } from "@/components/molecules/Glyphs";
import type { LeaveBalance } from "@/services/leaveService";

export function LeaveBalanceCard({
  balanceQuery,
}: {
  balanceQuery: UseQueryResult<LeaveBalance>;
}) {
  if (balanceQuery.isPending) {
    return <LoadingBar className="h-24 w-full" />;
  }

  if (balanceQuery.isError || !balanceQuery.data) {
    return null;
  }

  const b = balanceQuery.data;

  return (
    <div className="rounded-panel border border-line bg-surface p-5 shadow-card">
      <div className="flex items-center justify-between mb-3 border-b border-line pb-2.5">
        <div className="flex items-center gap-2">
          <Calendar size={18} className="text-primary" />
          <TextBlock className="font-semibold text-foreground">
            Kuota Cuti Tahunan ({b.period_year})
          </TextBlock>
        </div>
        <TextBlock as="span" className="text-xs text-mist">
          {b.employee_name}
        </TextBlock>
      </div>

      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="p-3 rounded-control bg-hover">
          <TextBlock as="span" className="block text-xs text-mist mb-1">
            Total Hak Cuti
          </TextBlock>
          <TextBlock as="span" className="text-xl font-bold text-foreground">
            {b.total_quota} <TextBlock as="span" className="text-xs font-normal text-mist">Hari</TextBlock>
          </TextBlock>
        </div>

        <div className="p-3 rounded-control bg-hover">
          <TextBlock as="span" className="block text-xs text-mist mb-1">
            Sudah Terpakai
          </TextBlock>
          <TextBlock as="span" className="text-xl font-bold text-lens">
            {b.used_quota} <TextBlock as="span" className="text-xs font-normal text-mist">Hari</TextBlock>
          </TextBlock>
        </div>

        <div className="p-3 rounded-control bg-primary/10 border border-primary/20">
          <TextBlock as="span" className="block text-xs text-primary mb-1 font-medium">
            Sisa Kuota Cuti
          </TextBlock>
          <TextBlock as="span" className="text-xl font-bold text-primary">
            {b.remaining_quota} <TextBlock as="span" className="text-xs font-normal text-primary">Hari</TextBlock>
          </TextBlock>
        </div>
      </div>

      {b.remaining_quota <= 2 && (
        <div className="mt-3 flex items-center gap-2 text-xs text-danger">
          <AlertCircle size={14} />
          <TextBlock as="span">Sisa cuti tahunan Anda tinggal {b.remaining_quota} hari. Rencanakan pengajuan dengan bijak.</TextBlock>
        </div>
      )}
      {b.remaining_quota > 2 && (
        <div className="mt-3 flex items-center gap-2 text-xs text-leaf">
          <CheckCircle2 size={14} />
          <TextBlock as="span">Kuota cuti aktif dapat digunakan hingga 31 Desember {b.period_year}.</TextBlock>
        </div>
      )}
    </div>
  );
}
