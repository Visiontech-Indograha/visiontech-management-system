# Data, query, mutasi, dan form

## 1. Query key

Pola (contoh, bukan kode VMS yang sudah ada; sesuaikan dengan hook di `hooks/` dan `services/`):

```ts
// Pola query key terpusat per domain
export const hseKeys = {
  all: ['hse'] as const,
  campaigns: () => [...hseKeys.all, 'campaigns'] as const,
  campaign: (id: number) => [...hseKeys.campaigns(), id] as const,
};
```

Aturan:
- Key berawal dari nama domain, supaya `invalidateQueries({ queryKey: hseKeys.all })` membersihkan semua turunannya.
- Param daftar masuk ke key (`q`, `page`, `size`), supaya tiap kombinasi punya cache sendiri.
- Hindari key string lepas tersebar di komponen. Riset mencatat query key belum terpusat secara menyeluruh (sumber: riset `03` W-H, belum diverifikasi penuh).

## 2. Query dengan Zod di batas

```ts
// services/<domain>Service.ts (pola)
export async function fetchCampaign(id: number, signal?: AbortSignal): Promise<Campaign> {
  const raw = await api(`/hse/campaigns/${id}`, { signal });   // lib/apiClient
  return CampaignSchema.parse(raw);                            // schemas/
}

// hooks/ atau di organisme
export function useCampaign(id: number) {
  return useQuery({
    queryKey: hseKeys.campaign(id),
    queryFn: ({ signal }) => fetchCampaign(id, signal),
    staleTime: 60_000,
  });
}
```

- `signal` diteruskan agar request dibatalkan saat pindah halaman.
- Tipe dari `apiTypes` untuk respons, dan Zod untuk validasi runtime. Jika skema Zod dan tipe bisa dibentuk dari satu sumber (`z.infer`), pakai satu sumber.
- Zod versi 4 dipakai di proyek (`package.json`: `zod ^4.6.7`). Periksa sintaks saat menulis skema.

## 3. Mutasi dan invalidasi

```ts
const qc = useQueryClient();
const m = useMutation({
  mutationFn: (body: CampaignInput) => saveCampaign(body),
  onSuccess: () => qc.invalidateQueries({ queryKey: hseKeys.all }),
});
```

Aksi persetujuan (approve, reject, serah terima, kunci) tidak optimistic. Tunggu respons server, lalu tampilkan hasil.

## 4. Optimistic update (aksi ringan)

Contoh untuk centang atau tandai baca. Hanya untuk aksi yang gagal tanpa dampak besar.

```ts
useMutation({
  mutationFn: (id: number) => markRead(id),
  onMutate: async (id) => {
    await qc.cancelQueries({ queryKey: notifKeys.list() });
    const prev = qc.getQueryData(notifKeys.list());
    qc.setQueryData(notifKeys.list(), (old) => toggleRead(old, id));
    return { prev };
  },
  onError: (_e, _id, ctx) => { if (ctx?.prev) qc.setQueryData(notifKeys.list(), ctx.prev); },
  onSettled: () => qc.invalidateQueries({ queryKey: notifKeys.list() }),
});
```

Sumber verifikasi: riset `01` F-26. Di VMS saat ini `setQueryData` ada di 4 berkas, `onMutate` nol.

## 5. Form

- `react-hook-form` dengan `zodResolver` (`@hookform/resolvers`).
- Simpan draf bila form panjang (hook `useFormDraft`), dan peringatkan saat keluar dengan perubahan belum disimpan (`useDirtyForm`).
- Tombol simpan: `aria-busy` dan `disabled` saat `isPending`, teks "Menyimpan..." (bukan hanya spinner).
- Galat 422:

```ts
try {
  await m.mutateAsync(values);
} catch (err) {
  if (!applyFieldErrors(err, setError, KNOWN_FIELDS)) {
    toast.error(errorMessage(err));
  }
}
```

`applyFieldErrors` (di `lib/errors.ts`) hanya memetakan field yang ada di daftar `KNOWN_FIELDS`. Field lain jatuh ke pesan umum.

- Batas input harus sama dengan API: `max_length`, pola, `ge`/`le`. Rentang tanggal memakai aturan yang sama dengan API (`check_date_range`, bukti: `CLAUDE.md` dan `api/app/core/list_params.py`).

## 6. Daftar dengan paginasi

- Gunakan `usePagedList` dan `useListControls` (sudah ada di `hooks/`).
- Server mengembalikan total di header `X-Total-Count`. Tampilkan "Menampilkan X dari Y".
- Filter teks: debounce dengan `useDebouncedValue`. Jangan kirim request tiap ketukan.
- Pencarian memakai awalan (`q` = awalan). Aturan SQL proyek melarang `LIKE '%...'` (bukti: `CLAUDE.md`).

## 7. Batas data dan kontrak

- Jangan ubah kontrak API di web saja. Perubahan skema API memerlukan `UPDATE_OPENAPI_SNAPSHOT=1 pytest`, lalu `npm run gen:api:export && npm run gen:api` (bukti: `CLAUDE.md`).
- Respons API lama (APK lapangan) tetap jalan: parameter baru bersifat opsional.
