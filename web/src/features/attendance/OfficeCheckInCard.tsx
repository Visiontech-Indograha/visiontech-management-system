import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { ApiError } from "@/lib/api";
import { TextAreaField } from "@/components/ui/Field";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useAttendanceSites } from "@/features/sites/api";
import { useFaceStatus } from "@/features/account/api";
import { FaceProbeDialog } from "@/features/face/FaceProbeDialog";
import { SelfieCaptureDialog } from "./SelfieCaptureDialog";

type AttendanceList = components["schemas"]["AttendanceListResponse"];
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
      const data = (
        await api.get<AttendanceList>("/attendance", {
          params: { employee_id: employeeId, size: 5 },
        })
      ).data;
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
        <h2 className="font-semibold">Absen hari ini</h2>
        <p className="mt-1 text-sm text-mist">
          Anda terdaftar sebagai pekerja lapangan. Absen masuk dan pulang dilakukan lewat aplikasi HP.
        </p>
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
      return (
        await api.post<Attendance>("/attendance/check-in", {
          channel: "WEB",
          site_id: siteId,
          location: { lat: pos.lat, lng: pos.lng },
          location_origin: "GPS",
          accuracy_m: pos.accuracy,
          explanation: explanation.trim() || null,
          selfie_file_id: vars?.selfieFileId ?? null,
          face_probe_id: probeRef.current,
        })
      ).data;
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

  const checkOut = useMutation({
    mutationFn: async () => {
      const pos = await currentPosition();
      return (
        await api.post<Attendance>("/attendance/check-out", {
          channel: "WEB",
          location: { lat: pos.lat, lng: pos.lng },
          location_origin: "GPS",
          face_probe_id: probeRef.current,
        })
      ).data;
    },
    onSuccess: async () => {
      probeRef.current = null;
      setError(null);
      toast.success("Absen pulang tercatat.");
      await refresh();
    },
    onError: (err) => setError(failMessage(err)),
  });

  const busy = checkIn.isPending || checkOut.isPending;

  return (
    <section aria-label="Absen hari ini" className="mb-6 rounded-panel border border-line bg-surface p-4 shadow-card">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="font-semibold">Absen hari ini</h2>
          <p className="text-sm text-mist">Pekerja kantor · absen lewat web</p>
        </div>
        {rec && <StatusBadge status={rec.status} />}
      </div>

      {error && (
        <p role="alert" className="mt-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}

      {today.isLoading ? (
        <p className="mt-3 text-sm text-mist">Memuat absensi hari ini…</p>
      ) : today.isError ? (
        <p role="alert" className="mt-3 text-sm text-danger">
          Absensi hari ini tidak dapat dimuat.
        </p>
      ) : locked ? (
        <p role="status" className="mt-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          Absensi hari ini ditolak {rejected.length} kali dan tidak dapat diajukan lagi. Hari ini tercatat ditolak.
        </p>
      ) : !rec ? (
        <>
          {rejected.length > 0 && (
            <p role="status" className="mt-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
              Absensi ditolak
              {rejected[0].review_note ? `: ${rejected[0].review_note}` : ""}. Anda dapat mengajukan absen ulang satu
              kali hari ini.
            </p>
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
              <label htmlFor="office-site" className="text-sm font-medium">
                Lokasi kerja
              </label>
              <select
                id="office-site"
                className={selectCls}
                value={siteId}
                disabled={sites.isLoading || busy}
                onChange={(e) => setPicked(e.target.value)}
              >
                {sites.data?.length === 0 && <option value="">Belum ada lokasi kerja</option>}
                {sites.data?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <Button className="h-11" disabled={!siteId || busy} onClick={() => (needFace ? setFaceFor("in") : checkIn.mutate(undefined))}>
              {checkIn.isPending ? "Membaca lokasi…" : rejected.length > 0 ? "Ajukan absen ulang" : "Absen masuk"}
            </Button>
          </div>
        </>
      ) : (
        <div className="mt-3 space-y-3">
          <dl className="text-sm">
            <div>
              <dt className="inline text-mist">Lokasi: </dt>
              <dd className="inline">
                {rec.site_label} · {Math.round(rec.distance_m)} m{rec.is_late ? " · terlambat" : ""}
                {rec.is_early_leave ? " · pulang cepat" : ""}
              </dd>
            </div>
            <div>
              <dt className="inline text-mist">Masuk / pulang: </dt>
              <dd className="inline">
                {formatDateTime(rec.check_in_at)} /{" "}
                {rec.check_out_at ? formatDateTime(rec.check_out_at) : "belum pulang"}
              </dd>
            </div>
          </dl>
          {!rec.check_out_at && rec.status === "NEEDS_REVIEW" ? (
            <p role="status" className="rounded-control border border-warning-border bg-warning-bg px-3 py-2 text-sm text-warning">
              Absen masuk menunggu pemeriksaan. Absen pulang bisa dilakukan setelah absen masuk disetujui.
            </p>
          ) : !rec.check_out_at ? (
            <Button className="h-11 w-full md:w-auto" disabled={busy} onClick={() => (needFace ? setFaceFor("out") : checkOut.mutate())}>
              {checkOut.isPending ? "Membaca lokasi…" : "Absen pulang"}
            </Button>
          ) : (
            <p className="text-sm text-success">Absensi hari ini selesai. Terima kasih!</p>
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
            else checkOut.mutate();
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
