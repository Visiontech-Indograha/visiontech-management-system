# Struktur dan aturan impor web VMS

Sumber aturan: `web/eslint.config.js` (ditegakkan ESLint, `no-restricted-imports` dan `no-restricted-syntax`). Komentar di berkas itu merujuk `docs/33` keputusan pemilik 2026-10-09.

## Hierarki

```
tampilan UI > Page > Template > Organism > Molecule > Atom
Page       = kumpulan Template
Template   = kumpulan Organism
Organism   = kumpulan Molecule
Molecule   = kumpulan Atom
```

## Tabel larangan impor

| Berkas di | Boleh impor | Dilarang impor |
|---|---|---|
| `pages/` | templates (lewat `app/` untuk rute) | atoms, molecules, organisms, pages, `lucide-react`, `Link`/`NavLink` dari react-router, `lib/apiClient` (`api`) |
| `components/templates/` | organisms | atoms, molecules, pages |
| `components/organisms/` | molecules | atoms, templates, pages |
| `components/molecules/` | atoms | organisms, templates, pages, molecule lain (`./*`) |
| `components/atoms/` | (hanya lib) | molecules, organisms, templates, pages |
| `services/`, `hooks/`, `stores/` | lib, schemas | pages, components |
| `lib/`, `schemas/` | lib | pages, components, services, hooks |

Catatan:
- Molekul tidak boleh mengimpor molekul lain (`SAME_MOLECULE`). Jika perlu dua molekul, susun di organisme.
- `lucide-react` (ikon) hanya di atom. Ikon dibungkus `components/atoms/Icon`.
- `Link` dan `NavLink` dari react-router hanya di atom atau lewat atom tautan.

## Elemen HTML

Aturan `no-restricted-syntax`:
- Page: tidak boleh elemen HTML sama sekali (termasuk `div`).
- Template, organisme, molekul: hanya `div`, `section`, `main`, `header`, `footer`, `article`, `aside`, `nav`.
- Semua: teks langsung (`<div>Simpan</div>`, atau teks di fragmen) dilarang. Bungkus dengan atom `Text`. Teks sebagai isi atom (`<Button>Simpan</Button>`) boleh.

Contoh benar (organisme):

```tsx
// components/organisms/hse/HseCampaignsPanel.tsx (pola)
export function HseCampaignsPanel() {
  return (
    <section className="space-y-4">
      <Text as="h2" className="text-lg font-semibold">Kampanye K3</Text>
      <div className="flex gap-2">
        <ActionButton variant="outline">Tambah</ActionButton>
      </div>
    </section>
  );
}
```

Contoh salah:

```tsx
// Dilarang di organisme: elemen HTML dan teks langsung
<p>Belum ada kampanye</p>          // teks langsung + elemen p
<button onClick={...}>Tambah</button>  // elemen button di luar atom
```

## Aturan lain

- Tidak ada barrel `index.ts` di `components/`. Impor berkas langsung (`@/components/molecules/QueryState`). Ini membantu tree-shaking Vite (sumber: riset `03` W1).
- Alias `@/` ke `src/` (`vitest.config.ts` dan `vite.config.ts`).
- `react-refresh/only-export-components` sebagai peringatan. Atom boleh mengekspor lebih dari komponen.
- File uji (`*.test.tsx`) tidak terkena aturan atomic.

## Lokasi berkas baru

| Jenis | Lokasi | Contoh nama |
|---|---|---|
| Atom | `components/atoms/` | `Badge.tsx` |
| Molekul | `components/molecules/` | `FormField.tsx` |
| Organisme | `components/organisms/<domain>/` | `organisms/hse/HseCampaignsPanel.tsx` |
| Template | `components/templates/<domain>/` | `templates/hse/HseCampaignsTemplate.tsx` |
| Halaman | `pages/<domain>/` | `pages/hse/HseCampaignsPage.tsx` |
| Service | `services/` | `hseService.ts` |
| Skema | `schemas/` | `accountSchemas.ts` |
| Hook | `hooks/` | `useTimedCarousel.ts` |

## Contoh struktur halaman

```tsx
// pages/hse/HseCampaignsPage.tsx: hanya merangkai template dan data
export default function HseCampaignsPage() {
  const q = useHseCampaigns();
  return <HseCampaignsTemplate query={q} />;
}
```

Template menerima query, lalu memakai `QueryState` (molekul) dan organisme untuk isi.

## Verifikasi aturan impor

- `npm run lint` menjalankan ESLint. Pelanggaran tampil sebagai error.
- Jangan menambah `// eslint-disable` untuk melewati aturan ini tanpa catatan.
- Dependensi `eslint-plugin-boundaries` belum dipakai. Jangan menambah mekanisme kedua tanpa keputusan.
