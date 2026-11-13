import { Pill as Badge } from "@/components/molecules/Pill";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { TextBlock } from "@/components/molecules/TextBlock";
import { useDeviceStatus } from "@/services/hikvisionService";
import { formatWhen } from "./hikvisionLabels";

/** Status satu mesin: jumlah data masuk, data terakhir, dan yang belum cocok dengan karyawan. */
export function DeviceStatusLine({ deviceId }: { deviceId: string }) {
  const status = useDeviceStatus(deviceId);
  if (status.isPending) return <LoadingBar aria-hidden className="h-10" />;
  if (status.isError) return <RetryNotice message="Status mesin belum bisa dimuat." onRetry={() => status.refetch()} />;
  const s = status.data;
  return (
    <div className="space-y-1">
      <TextBlock className="text-sm text-mist">
        Data masuk: {s.event_24_jam} dalam 24 jam, {s.event_7_hari} dalam 7 hari. Terakhir: {formatWhen(s.event_terakhir_diterima)}.
      </TextBlock>
      {s.event_7_hari === 0 && <Badge tone="warning">Belum ada data masuk dalam 7 hari</Badge>}
      {s.belum_terpetakan_7_hari > 0 ? (
        <Badge tone="warning">{`${s.belum_terpetakan_7_hari} data belum cocok dengan karyawan`}</Badge>
      ) : (
        <Badge tone="success">Semua data sudah cocok dengan karyawan</Badge>
      )}
    </div>
  );
}
