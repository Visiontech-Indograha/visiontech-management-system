import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import type { components } from "@/lib/apiTypes";
import { ApiError } from "@/lib/apiClient";
import { TextAreaField } from "@/components/molecules/Field";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useAttendanceSites } from "@/services/siteService";
import { useFaceStatus } from "@/services/accountService";
import { FaceProbeDialog } from "@/components/organisms/face/FaceProbeDialog";
import { SelfieCaptureDialog } from "./SelfieCaptureDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock } from "@/components/molecules/ListBlock";
import { ControlLabel, ControlOption, ControlSelect } from "@/components/molecules/FormBlock";
import { checkIn as submitCheckIn, checkOut as submitCheckOut, listEmployeeAttendance } from "@/services/attendanceService";

type Attendance = components["schemas"]["AttendanceResponse"];
// Keputusan pemilik 2026-10-02: ditolak → boleh mengajukan ulang sekali; ditolak lagi → hari itu terkunci.
const MAX_ATTEMPTS_PER_DAY = 2;
const selectCls = "h-11 w-full rounded-control border border-line bg-surface px-3 text-base";

interface BrowserPosition {
  lat: number;
  lng: number;
  accuracy: number;
}

/** Galat sisi klien yang pesannya untuk pengguna (lokasi browser, penjelasan wajib) — bukan galat API. */
class UserFacingError extends Error {}

const failMessage = (err: unknown) => (err instanceof UserFacingError ? err.message : errorMessage(err));

/** Jarak dua titik (m) — hanya untuk memutuskan apakah form penjelasan perlu tampil; server tetap
 * menghitung ulang jarak & status (aturan inti #3). */
function distanceM(a: { lat: number; lng: number }, b: { lat: number; lng: number }): number {
  const r = 6371000;
  const rad = (d: number) => (d * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat);
  const dLng = rad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(h));
}

/** Lokasi dari browser. Di laptop/PC sumbernya WiFi, jadi bisa lebih kabur dari GPS HP. */
function currentPosition(): Promise<BrowserPosition> {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new UserFacingError("Browser ini tidak mendukung akses lokasi."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) =>
        resolve({
          lat: p.coords.latitude,
          lng: p.coords.longitude,
          accuracy: p.coords.accuracy,
        }),
      (err) =>
        reject(
          new UserFacingError(
            err.code === err.PERMISSION_DENIED
              ? "Akses lokasi ditolak. Izinkan lokasi untuk situs ini di pengaturan browser, lalu coba lagi."
              : "Lokasi tidak dapat dibaca. Pastikan WiFi atau layanan lokasi perangkat menyala.",
          ),
        ),
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 },
    );
  });
}

/** Absensi milik sendiri hari ini: sesi terbuka didahulukan (lewat tengah malam), lalu `today` dari server. */
function useMyToday(employeeId: string | null | undefined) {
  return useQuery({
    queryKey: ["attendance", "mine-today", employeeId],
    enabled: !!employeeId,
    queryFn: async () => {
      const data = await listEmployeeAttendance(employeeId!, 5);
      // R-33: hanya sesi valid yang bisa absen pulang; absen hari lalu yang menunggu pemeriksaan tidak didahulukan.
      const open = data.items.find((a) => !a.check_out_at && (a.status === "AUTO_VALID" || a.status === "APPROVED"));
      const todays = data.items.filter((a) => a.work_date === data.today);
      return {
        rec: open ?? todays.find((a) => a.status !== "REJECTED") ?? null,
        rejected: todays.filter((a) => a.status === "REJECTED"),
      };
    },
  });
}

/**
 * Absen masuk/pulang lewat web — khusus pekerja kantor (`attendance_mode` OFFICE).
 * Pekerja lapangan diarahkan ke aplikasi HP; server menolak kanal yang salah (WRONG_ATTENDANCE_CHANNEL).
 * Jam, tanggal, jarak, terlambat, dan status tetap diputuskan server.
 */
export function OfficeCheckInCard() {
  const { me } = useSession();
  const mode = me?.attendance_mode;
  if (!me?.employee_id || !mode) return null;
  if (mode !== "OFFICE") {
    return (
      <section aria-label="Absen hari ini" className="mb-6 rounded-panel border border-line bg-surface p-4 shadow-card">
        <TextBlock as="h2" className="font-semibold">Absen hari ini</TextBlock>
        <TextBlock className="mt-1 text-sm text-mist">
          Anda terdaftar sebagai pekerja lapangan. Absen masuk dan pulang dilakukan lewat aplikasi HP.
        </TextBlock>
      </section>
    );
  }
  return <OfficeCheckInForm employeeId={me.employee_id} />;
}

function OfficeCheckInForm({ employeeId }: { employeeId: string }) {
  const qc = useQueryClient();
  const today = useMyToday(employeeId);
  const sites = useAttendanceSites();
  const [picked, setPicked] = useState("");
  const [error, setError] = useState<string | null>(null);
  // R-33: penjelasan wajib bila di luar radius atau mengajukan ulang absensi yang ditolak (juga dicek server).
  const [explanation, setExplanation] = useState("");
  const [askExplanation, setAskExplanation] = useState(false);
  // Wajah (web = hanya online): karyawan yang sudah mendaftar wajah memverifikasi dulu; hasilnya dipakai satu absen.
  const face = useFaceStatus();
  const needFace = !!(face.data?.employee_linked && face.data.consent === "GRANTED" && face.data.enrolled);
  const [faceFor, setFaceFor] = useState<"in" | "out" | null>(null);
  const probeRef = useRef<string | null>(null);
  const [selfieFor, setSelfieFor] = useState<{ pos: BrowserPosition; siteName: string; info: string } | null>(null);
  // Bawaan: lokasi yang namanya memuat "kantor", selain itu lokasi pertama; pilihan pengguna didahulukan.
  const siteId = picked || (sites.data?.find((s) => /kantor/i.test(s.name)) ?? sites.data?.[0])?.id || "";

  const rec = today.data?.rec ?? null;
  const rejected = today.data?.rejected ?? [];
  const locked = !rec && rejected.length >= MAX_ATTEMPTS_PER_DAY;
  const resubmit = rejected.length > 0;

  const refresh = async () => {
    await qc.invalidateQueries({ queryKey: ["attendance"] });
    await qc.invalidateQueries({ queryKey: ["attendance-recap"] });
  };

  // Alur (flowchart R-33): cek lokasi & jam → di luar zona/ajukan ulang: alasan wajib → di luar zona: swafoto
  // wajib → kirim. Server menghitung ulang jarak & status dan menolak bila alasan/swafoto tidak ada.
  const checkIn = useMutation({
    mutationFn: async (vars?: { pos: BrowserPosition; selfieFileId: string }): Promise<Attendance | null> => {
      const pos = vars?.pos ?? (await currentPosition());
      const site = sites.data?.find((s) => s.id === siteId);
      const away = site ? Math.round(distanceM(pos, site.location)) : 0;
      const outside = !!site && away > site.radius_m;
      if ((outside || resubmit) && !explanation.trim()) {
        setAskExplanation(true);
        throw new UserFacingError(
          outside
            ? `Anda ${away} m dari ${site.name} (radius ${site.radius_m} m). Isi penjelasan mengapa absen di luar zona.`
            : "Isi penjelasan untuk mengajukan ulang absensi yang ditolak.",
        );
      }
      if (outside && !vars?.selfieFileId) {
        setSelfieFor({
          pos,
          siteName: site.name,
          info: `Anda ${away} m dari ${site.name} (radius ${site.radius_m} m). Swafoto wajib di luar zona.`,
        });
        return null;
      }
      return submitCheckIn({
          channel: "WEB",
          site_id: siteId,
          location: { lat: pos.lat, lng: pos.lng },
          location_origin: "GPS",
          accuracy_m: pos.accuracy,
          explanation: explanation.trim() || null,
          selfie_file_id: vars?.selfieFileId ?? null,
          face_probe_id: probeRef.current,
        });
    },
    onSuccess: async (a) => {
      if (!a) return; // menunggu swafoto
      probeRef.current = null;
      setError(null);
      setExplanation("");
      setAskExplanation(false);
      toast.success(
        a.status === "NEEDS_REVIEW"
          ? `Absen masuk tercatat, tetapi ${Math.round(a.distance_m)} m dari lokasi — menunggu pemeriksaan.`
          : "Absen masuk tercatat.",
      );
      await refresh();
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === "EXPLANATION_REQUIRED") setAskExplanation(true);
      setError(failMessage(err));
    },
  });

  // T7: di luar radius, server mewajibkan swafoto + penjelasan saat pulang. Dicoba dulu tanpa; bila ditolak karena itu,
  // minta penjelasan lalu swafoto dan kirim ulang dengan lokasi yang sama.
  const [outPos, setOutPos] = useState<BrowserPosition | null>(null);
  const [selfieOut, setSelfieOut] = useState(false);
  const checkOut = useMutation({
    mutationFn: async (vars?: { selfieFileId: string }) => {
      const pos = outPos && vars ? outPos : await currentPosition();
      setOutPos(pos);
      return submitCheckOut({
          channel: "WEB",
          location: { lat: pos.lat, lng: pos.lng },
          location_origin: "GPS",
          accuracy_m: pos.accuracy,
          explanation: explanation.trim() || null,
          selfie_file_id: vars?.selfieFileId ?? null,
          face_probe_id: probeRef.current,
        });
    },
    onSuccess: async (a) => {
      probeRef.current = null;
      setOutPos(null);
      setError(null);
      setExplanation("");
      setAskExplanation(false);
      toast.success(a.check_out_outside ? "Absen pulang tercatat di luar radius — menunggu pemeriksaan." : "Absen pulang tercatat.");
      await refresh();
    },
    onError: (err) => {
      if (err instanceof ApiError && /swafoto wajib/i.test(err.message)) {
        setAskExplanation(true);
        if (!explanation.trim()) {
          setError(`${err.message} Isi penjelasan, lalu tekan Absen pulang lagi untuk mengambil swafoto.`);
          return;
        }
        setSelfieOut(true);
        return;
      }
      setError(failMessage(err));
    },
  });

  const busy = checkIn.isPending || checkOut.isPending;

  return (
    <section aria-label="Absen hari ini" className="mb-6 rounded-panel border border-line bg-surface p-4 shadow-card">
      <div className="flex items-start justify-between gap-2">
        <div>
          <TextBlock as="h2" className="font-semibold">Absen hari ini</TextBlock>
          <TextBlock className="text-sm text-mist">Pekerja kantor · absen lewat web</TextBlock>
        </div>
        {rec && <StatusBadge status={rec.status} />}
      </div>

      {error && (
        <TextBlock role="alert" className="mt-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {error}
        </TextBlock>
      )}

      {today.isLoading ? (
        <TextBlock className="mt-3 text-sm text-mist">Memuat absensi hari ini…</TextBlock>
      ) : today.isError ? (
        <TextBlock role="alert" className="mt-3 text-sm text-danger">
          Absensi hari ini tidak dapat dimuat.
        </TextBlock>
      ) : locked ? (
        <TextBlock role="status" className="mt-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          Absensi hari ini ditolak {rejected.length} kali dan tidak dapat diajukan lagi. Hari ini tercatat ditolak.
        </TextBlock>
      ) : !rec ? (
        <>
          {rejected.length > 0 && (
            <TextBlock role="status" className="mt-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
              Absensi ditolak
              {rejected[0].review_note ? `: ${rejected[0].review_note}` : ""}. Anda dapat mengajukan absen ulang satu
              kali hari ini.
            </TextBlock>
          )}
          {(askExplanation || resubmit) && (
            <div className="mt-3">
              <TextAreaField
                label="Penjelasan (wajib)"
                hint={
                  resubmit
                    ? "Wajib saat mengajukan ulang absensi yang ditolak."
                    : "Wajib karena Anda di luar zona lokasi."
                }
                value={explanation}
                maxLength={1000}
                onChange={(e) => setExplanation(e.target.value)}
              />
            </div>
          )}
          <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
            <div className="space-y-1.5">
              <ControlLabel htmlFor="office-site" className="text-sm font-medium">
                Lokasi kerja
              </ControlLabel>
              <ControlSelect
                id="office-site"
                className={selectCls}
                value={siteId}
                disabled={sites.isLoading || busy}
                onChange={(e) => setPicked(e.target.value)}
              >
                {sites.data?.length === 0 && <ControlOption value="">Belum ada lokasi kerja</ControlOption>}
                {sites.data?.map((s) => (
                  <ControlOption key={s.id} value={s.id}>
                    {s.name}
                  </ControlOption>
                ))}
              </ControlSelect>
            </div>
            <ActionButton className="h-11" disabled={!siteId || busy} onClick={() => (needFace ? setFaceFor("in") : checkIn.mutate(undefined))}>
              {checkIn.isPending ? "Membaca lokasi…" : rejected.length > 0 ? "Ajukan absen ulang" : "Absen masuk"}
            </ActionButton>
          </div>
        </>
      ) : (
        <div className="mt-3 space-y-3">
          <ListBlock as="dl" className="text-sm">
            <div>
              <TextBlock as="dt" className="inline text-mist">Lokasi: </TextBlock>
              <TextBlock as="dd" className="inline">
                {rec.site_label} · {Math.round(rec.distance_m)} m{rec.is_late ? " · terlambat" : ""}
                {rec.is_early_leave ? " · pulang cepat" : ""}
              </TextBlock>
            </div>
            <div>
              <TextBlock as="dt" className="inline text-mist">Masuk / pulang: </TextBlock>
              <TextBlock as="dd" className="inline">
                {formatDateTime(rec.check_in_at)} /{" "}
                {rec.check_out_at ? formatDateTime(rec.check_out_at) : "belum pulang"}
              </TextBlock>
            </div>
          </ListBlock>
          {!rec.check_out_at && rec.status === "NEEDS_REVIEW" ? (
            <TextBlock role="status" className="rounded-control border border-warning-border bg-warning-bg px-3 py-2 text-sm text-warning">
              Absen masuk menunggu pemeriksaan. Absen pulang bisa dilakukan setelah absen masuk disetujui.
            </TextBlock>
          ) : !rec.check_out_at ? (
            <ActionButton className="h-11 w-full md:w-auto" disabled={busy} onClick={() => (needFace ? setFaceFor("out") : checkOut.mutate(undefined))}>
              {checkOut.isPending ? "Membaca lokasi…" : "Absen pulang"}
            </ActionButton>
          ) : (
            <TextBlock className="text-sm text-success">Absensi hari ini selesai. Terima kasih!</TextBlock>
          )}
        </div>
      )}
      {faceFor && (
        <FaceProbeDialog
          title={faceFor === "in" ? "Verifikasi wajah — absen masuk" : "Verifikasi wajah — absen pulang"}
          onCancel={() => setFaceFor(null)}
          onDone={(probeId) => {
            const which = faceFor;
            probeRef.current = probeId;
            setFaceFor(null);
            if (which === "in") checkIn.mutate(undefined);
            else checkOut.mutate(undefined);
          }}
        />
      )}
      {selfieOut && outPos && (
        <SelfieCaptureDialog
          info="Anda berada di luar radius lokasi. Swafoto wajib saat pulang di luar zona."
          position={outPos}
          siteName="lokasi kerja"
          onCancel={() => setSelfieOut(false)}
          onCaptured={(fileId) => {
            setSelfieOut(false);
            checkOut.mutate({ selfieFileId: fileId });
          }}
        />
      )}
      {selfieFor && (
        <SelfieCaptureDialog
          info={selfieFor.info}
          position={selfieFor.pos}
          siteName={selfieFor.siteName}
          onCancel={() => setSelfieFor(null)}
          onCaptured={(fileId) => {
            const pos = selfieFor.pos;
            setSelfieFor(null);
            checkIn.mutate({ pos, selfieFileId: fileId });
          }}
        />
      )}
    </section>
  );
}
