import { Paperclip, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";
import { useFieldArray, useWatch, type Control, type FieldErrors, type UseFormRegister, type UseFormSetValue } from "react-hook-form";
import { toast } from "sonner";
import { Button } from "@/components/atoms/Button";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import type { TaskValue, Values } from "../pages/PlanEditorPage";
import { oversize, uploadFiles } from "../uploadService";
import { weekday } from "../weekday";

const cell = "border-b border-line p-2 align-top";
const control_ =
  "h-11 w-full rounded-md border border-input bg-transparent px-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

type Option = { id: string; name: string };
type Candidate = Option & { busy: string[] };

interface Props {
  fields: { id: string; work_date: string }[];
  control: Control<Values>;
  register: UseFormRegister<Values>;
  setValue: UseFormSetValue<Values>;
  errors: FieldErrors<Values>;
  sites: Option[];
  workTypes: Option[];
  candidates: Candidate[];
  onHoliday: (iso: string) => void;
}

/**
 * Tabel hari kerja rencana: satu baris per hari — tanggal, jenis pekerjaan, lokasi, detail pekerjaan, pekerja hari itu.
 * Pekerja dipilih lewat dropdown (hanya yang kosong pada tanggal itu) lalu "Tambah"; nama masuk ke kolom Pekerja.
 * Di HP tabel bisa digeser ke samping.
 */
export function PlanDayTable(props: Props) {
  const { fields } = props;
  return (
    <div className="overflow-x-auto rounded-control border border-line">
      <table className="w-full min-w-[1080px] border-collapse text-sm">
        <thead className="bg-canvas text-left">
          <tr>
            <th className={`${cell} w-36`}>Tanggal</th>
            <th className={`${cell} w-44`}>Jenis pekerjaan</th>
            <th className={`${cell} w-44`}>Lokasi</th>
            <th className={cell}>Detail pekerjaan</th>
            <th className={`${cell} w-64`}>Pekerja (ketua selalu ikut)</th>
            <th className={`${cell} w-32`}>Aksi</th>
          </tr>
        </thead>
        <tbody>
          {fields.map((f, i) => (
            <DayRow key={f.id} index={i} workDate={f.work_date} total={fields.length} allDays={fields.map((x) => x.work_date)} {...props} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DayRow({
  index,
  workDate,
  total,
  allDays,
  control,
  register,
  setValue,
  errors,
  sites,
  workTypes,
  candidates,
  onHoliday,
}: Props & { index: number; workDate: string; total: number; allDays: string[] }) {
  const tasks = useFieldArray({ control, name: `days.${index}.tasks` });
  const live = useWatch({ control, name: `days.${index}.tasks` });
  const memberIds = useWatch({ control, name: `days.${index}.member_ids` }) ?? [];
  const daySite = useWatch({ control, name: `days.${index}.site_id` });
  const dayType = useWatch({ control, name: `days.${index}.work_type_id` });
  const [pick, setPick] = useState("");
  const [copyTo, setCopyTo] = useState<number[]>([]);
  const [uploading, setUploading] = useState<number | null>(null);
  const dayErr = errors.days?.[index];
  const filesOf = (t: number): TaskValue["files"] => live?.[t]?.files ?? [];
  const nameOf = (id: string) => candidates.find((c) => c.id === id)?.name ?? id;
  const free = candidates.filter((c) => !memberIds.includes(c.id) && !c.busy.includes(workDate));
  const busyCount = candidates.filter((c) => !memberIds.includes(c.id) && c.busy.includes(workDate)).length;
  const canHoliday = index > 0 && index < total - 1;

  const setMembers = (ids: string[]) => {
    setValue(`days.${index}.member_mode`, "custom", { shouldDirty: true });
    setValue(`days.${index}.member_ids`, ids, { shouldDirty: true });
  };
  const addMember = () => {
    if (!pick) return;
    setMembers([...memberIds, pick]);
    setPick("");
  };
  const applyToOthers = () => {
    for (const t of copyTo) {
      setValue(`days.${t}.work_type_id`, dayType, { shouldDirty: true });
      setValue(`days.${t}.site_id`, daySite, { shouldDirty: true });
      setValue(`days.${t}.member_mode`, "custom", { shouldDirty: true });
      setValue(`days.${t}.member_ids`, [...memberIds], { shouldDirty: true });
    }
    toast.success(`Jenis, lokasi, dan pekerja disalin ke ${copyTo.length} hari.`);
    setCopyTo([]);
  };
  const attach = async (t: number, list: FileList | null) => {
    const files = Array.from(list ?? []);
    if (!files.length) return;
    const tooBig = oversize(files);
    if (tooBig) return toast.error(tooBig);
    setUploading(t);
    try {
      const ids = await uploadFiles(files);
      setValue(`days.${index}.tasks.${t}.files`, [...filesOf(t), ...ids.map((id, k) => ({ file_id: id, file_name: files[k].name }))]);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setUploading(null);
    }
  };

  return (
    <tr>
      <td className={cell}>
        <p className="font-semibold">Hari {index + 1}</p>
        <p>
          {weekday(workDate)}, {formatDate(workDate)}
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-2"
          disabled={!canHoliday}
          onClick={() => onHoliday(workDate)}
          title={canHoliday ? undefined : "Hari pertama dan terakhir tidak bisa diliburkan; ubah tanggal mulai/selesai."}
        >
          Libur
        </Button>
      </td>
      <td className={cell}>
        <select aria-label={`Jenis pekerjaan hari ${index + 1}`} className={control_} {...register(`days.${index}.work_type_id`)}>
          <option value="">Ikut jenis rencana</option>
          {workTypes.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </td>
      <td className={cell}>
        <select aria-label={`Lokasi hari ${index + 1}`} className={control_} {...register(`days.${index}.site_id`)}>
          <option value="">Ikut lokasi rencana</option>
          {sites.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </td>
      <td className={cell}>
        <div className="space-y-2">
          {tasks.fields.map((task, t) => (
            <div key={task.id} className="rounded-control bg-canvas p-2">
              <div className="flex gap-2">
                <input
                  aria-label={`Judul pekerjaan hari ${index + 1} nomor ${t + 1}`}
                  placeholder="Judul pekerjaan"
                  className={control_}
                  {...register(`days.${index}.tasks.${t}.title`)}
                />
                {tasks.fields.length > 1 && (
                  <Button type="button" variant="ghost" size="sm" onClick={() => tasks.remove(t)} aria-label={`Hapus detail ${t + 1} hari ${index + 1}`}>
                    <Trash2 className="size-4" />
                  </Button>
                )}
              </div>
              <textarea
                aria-label={`Deskripsi pekerjaan hari ${index + 1} nomor ${t + 1}`}
                placeholder="Deskripsi"
                rows={2}
                className="mt-1 w-full rounded-md border border-input bg-transparent px-2 py-1 text-sm"
                {...register(`days.${index}.tasks.${t}.description`)}
              />
              {(dayErr?.tasks?.[t]?.title || dayErr?.tasks?.[t]?.description) && (
                <p className="text-xs text-destructive">{dayErr?.tasks?.[t]?.title?.message ?? dayErr?.tasks?.[t]?.description?.message}</p>
              )}
              <label className="flex min-h-11 cursor-pointer items-center gap-1 text-xs text-lens">
                <Paperclip className="size-4" />
                {uploading === t ? "Mengunggah..." : "Foto/PDF (opsional)"}
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png,.pdf"
                  multiple
                  className="sr-only"
                  onChange={(e) => {
                    void attach(t, e.target.files);
                    e.target.value = "";
                  }}
                />
              </label>
              {filesOf(t).map((f) => (
                <div key={f.file_id} className="flex items-center justify-between gap-1 text-xs">
                  <span className="truncate">{f.file_name}</span>
                  <button
                    type="button"
                    className="min-h-11 px-2 text-destructive"
                    onClick={() => setValue(`days.${index}.tasks.${t}.files`, filesOf(t).filter((x) => x.file_id !== f.file_id))}
                  >
                    Hapus
                  </button>
                </div>
              ))}
            </div>
          ))}
          {dayErr?.tasks?.message && <p className="text-xs text-destructive">{dayErr.tasks.message}</p>}
          <Button type="button" variant="outline" size="sm" onClick={() => tasks.append({ title: "", description: "", files: [] })}>
            <Plus className="size-4" /> Tambah detail
          </Button>
        </div>
      </td>
      <td className={cell}>
        <ul className="mb-2 flex flex-wrap gap-1" aria-label={`Pekerja hari ${index + 1}`}>
          {memberIds.length === 0 && <li className="text-xs text-mist">Belum ada anggota (hanya ketua)</li>}
          {memberIds.map((id) => (
            <li key={id} className="flex items-center gap-1 rounded-full bg-canvas px-2 py-1 text-xs">
              {nameOf(id)}
              <button
                type="button"
                aria-label={`Keluarkan ${nameOf(id)} dari hari ${index + 1}`}
                className="flex size-6 items-center justify-center"
                onClick={() => setMembers(memberIds.filter((m) => m !== id))}
              >
                <X className="size-3" />
              </button>
            </li>
          ))}
        </ul>
        <div className="flex gap-1">
          <select aria-label={`Pilih anggota hari ${index + 1}`} className={control_} value={pick} onChange={(e) => setPick(e.target.value)}>
            <option value="">{free.length ? "Pilih anggota…" : "Tidak ada yang kosong"}</option>
            {free.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <Button type="button" size="sm" className="h-11" disabled={!pick} onClick={addMember}>
            Tambah
          </Button>
        </div>
        {busyCount > 0 && <p className="mt-1 text-xs text-mist">{busyCount} orang sibuk di rencana lain pada tanggal ini.</p>}
      </td>
      <td className={cell}>
        {total > 1 && (
          <details>
            <summary className="flex min-h-11 cursor-pointer items-center text-xs font-medium text-lens">Salin ke hari lain</summary>
            <div className="mt-1 space-y-1">
              {allDays.map((d, k) =>
                k === index ? null : (
                  <label key={d} className="flex min-h-11 items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      className="size-5"
                      checked={copyTo.includes(k)}
                      onChange={(e) => setCopyTo(e.target.checked ? [...copyTo, k] : copyTo.filter((x) => x !== k))}
                    />
                    {weekday(d)} {formatDate(d)}
                  </label>
                ),
              )}
              <Button type="button" variant="outline" size="sm" disabled={copyTo.length === 0} onClick={applyToOthers}>
                Terapkan
              </Button>
            </div>
          </details>
        )}
      </td>
    </tr>
  );
}
