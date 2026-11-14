import { useState } from "react";
import { QueryState } from "@/components/molecules/QueryState";
import { useListControls } from "@/hooks/useListControls";
import { STATUS_BANDING, type StatusBanding } from "@/lib/hikvisionBanding";
import { jakartaToday } from "@/lib/leaveRules";
import { useBandingBayangan, useHikvisionDevices } from "@/services/hikvisionService";
import { BandingFilters, type BandingFilterValue } from "./BandingFilters";
import { BandingTable } from "./BandingTable";

const SIZE = 20;
const MAX_HARI = 31;

const geser = (iso: string, hari: number) => {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + hari);
  return d.toISOString().slice(0, 10);
};

const totalBaris = (d?: { total_baris?: number | null }) => d?.total_baris ?? 0;

const mesinAktif = (pilihan: string, daftar?: { device_id: string }[]) => pilihan || daftar?.[0]?.device_id || "";

const rentangBenar = (dari: string, sampai: string) =>
  Boolean(dari && sampai && dari <= sampai && (Date.parse(sampai) - Date.parse(dari)) / 86_400_000 < MAX_HARI);

/** Pembanding mode Bayangan: absen mesin vs absen aplikasi per karyawan-hari, dengan filter dan halaman dari server. */
export function BandingPanel() {
  const devices = useHikvisionDevices();
  const controls = useListControls({ size: SIZE });
  const hariIni = jakartaToday();
  const [pilihan, setPilihan] = useState("");
  const [dari, setDari] = useState(geser(hariIni, -6));
  const [sampai, setSampai] = useState(hariIni);
  const deviceId = mesinAktif(pilihan, devices.data);
  const rentangSah = rentangBenar(dari, sampai);
  const status = controls.filter("status", STATUS_BANDING) as StatusBanding | "";
  const query = useBandingBayangan(deviceId, rentangSah ? dari : "", sampai, {
    status: status === "" ? undefined : status,
    q: controls.search,
    page: controls.page,
    size: SIZE,
  });
  const total = totalBaris(query.data);
  const lastPage = Math.max(1, Math.ceil(total / SIZE));

  const terapkan = (p: Partial<BandingFilterValue>) => {
    setPilihan((v) => p.deviceId ?? v);
    setDari((v) => p.dari ?? v);
    setSampai((v) => p.sampai ?? v);
    if (p.status !== undefined) controls.setFilter("status", p.status);
    if (p.input !== undefined) controls.setInput(p.input);
  };

  return (
    <QueryState
      query={devices}
      errorText="Daftar mesin belum bisa dimuat. Periksa sambungan lalu coba lagi."
      empty={devices.data?.length === 0}
      emptyText="Belum ada mesin absensi. Tambahkan mesin dulu di halaman Mesin absensi."
    >
      <BandingFilters
        devices={devices.data ?? []}
        value={{ deviceId, dari, sampai, status, input: controls.input }}
        active={controls.active}
        onReset={controls.reset}
        onChange={terapkan}
      />
      {rentangSah ? (
        <BandingTable
          query={query}
          rows={query.data?.items ?? []}
          total={total}
          page={controls.page}
          shownPage={Math.min(controls.page, lastPage)}
          lastPage={lastPage}
          onPageChange={controls.setPage}
          filtered={Boolean(status || controls.search)}
        />
      ) : (
        <QueryState query={{ isPending: false, isError: true, refetch: () => setSampai(hariIni) }} errorText="Tanggal belum benar. Pilih rentang paling lama 31 hari, dari tanggal awal ke akhir.">{null}</QueryState>
      )}
    </QueryState>
  );
}
