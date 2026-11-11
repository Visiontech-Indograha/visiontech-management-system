import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import boundaries from 'eslint-plugin-boundaries'
import importPlugin from 'eslint-plugin-import'
import { builtinRules } from 'eslint/use-at-your-own-risk'

// Atomic design ketat (docs/33, keputusan pemilik 2026-10-09):
//   tampilan UI > Page > Template > Organism > Molecule > Atom
//   Page = kumpulan Template · Template = kumpulan Organism · Organism = kumpulan Molecule · Molecule = kumpulan Atom.
//   Elemen HTML (teks, tombol, tabel, gambar) hanya di Atom; Template/Organism/Molecule hanya boleh div tata letak.
// Struktur berbasis lapisan: pages/ · components/ · services/ · schemas/ · hooks/ · lib/.
const PAGES = { group: ['@/pages/*', '**/pages/**'], message: 'Hanya app/ (rute) yang boleh mengimpor pages/ (docs/33 §2.2).' }
const COMPONENTS = { group: ['@/components/*', '**/components/**'], message: 'services/, schemas/, hooks/, lib/ tidak boleh mengimpor components/ (docs/33 §2.2).' }
const DATA = { group: ['@/services/*', '**/services/**', '@/hooks/*', '**/hooks/**'], message: 'lib/ dan schemas/ tidak boleh mengimpor services/ atau hooks/ (docs/33 §2.2).' }
const tier = (name, who, why) => ({
  group: [`@/components/${name}/*`, `@/components/${name}/**`, `**/components/${name}/**`, `../${name}/*`, `../../${name}/*`, `../../${name}/**`],
  message: `${who} ${why} (docs/33 §2).`,
})
const ATOMS = (who) => tier('atoms', who, 'dilarang memakai atom langsung — bungkus dalam molecule')
const MOLECULES = (who) => tier('molecules', who, 'dilarang memakai molecule langsung — susun lewat organism')
const ORGANISMS = (who) => tier('organisms', who, 'dilarang memakai organism langsung — susun lewat template')
const TEMPLATES = (who) => tier('templates', who, 'tidak boleh mengimpor template')
const SAME_MOLECULE = { group: ['./*', '@/components/molecules/*'], message: 'Molecule hanya menyusun atom, bukan molecule lain (docs/33 §2).' }

// Panggilan HTTP hanya di services/ (docs/33 §5); ApiError tetap boleh untuk menangani galat.
const API_ONLY_IN_SERVICES = { name: '@/lib/apiClient', importNames: ['api'], message: 'Panggilan API hanya di services/ — buat fungsi di <domain>Service.ts (docs/33 §5).' }

// G0 (docs/rencana/struktur-dan-kualitas-kode-v2.md): satu jalur dialog (`VmsDialog`) dan tanpa barrel `index.ts`.
// Pemakai lama masuk eslint-suppressions.json (hanya boleh menyusut); impor baru gagal.
const LEGACY_DIALOG = [
  { group: ['@/components/molecules/Modal', '**/molecules/Modal'], message: 'Modal usang: pakai molecules/VmsDialog (G2 butir 1).' },
  { group: ['@/components/atoms/Dialog', '**/atoms/Dialog'], message: 'atoms/Dialog dipakai hanya lewat molecules/VmsDialog (G2 butir 1).' },
]
const NO_BARREL = { group: ['**/index', '**/index.ts', '**/index.tsx'], message: 'Tanpa barrel index.ts: impor langsung dari berkas sumber.' }
const EXTRA = [...LEGACY_DIALOG, NO_BARREL]

const LAYOUT_TAGS = 'div|section|main|header|footer|article|aside|nav'
/** Larangan susunan: impor tingkat terlarang + elemen HTML (kecuali tata letak bila `layout`) + teks langsung. */
const composition = (who, patterns, layout) => ({
  'no-restricted-imports': ['error', {
    patterns: [PAGES, ...patterns, ...EXTRA],
    paths: [
      { name: 'lucide-react', message: `Ikon adalah atom; ${who} dilarang memakainya langsung (docs/33 §2).` },
      { name: 'react-router-dom', importNames: ['Link', 'NavLink'], message: `Tautan adalah atom; ${who} dilarang memakainya langsung (docs/33 §2).` },
      API_ONLY_IN_SERVICES,
    ],
  }],
  'no-restricted-syntax': ['error',
    {
      selector: layout
        ? `JSXOpeningElement[name.type='JSXIdentifier'][name.name=/^[a-z]/]:not([name.name=/^(${LAYOUT_TAGS})$/])`
        : "JSXOpeningElement[name.type='JSXIdentifier'][name.name=/^[a-z]/]",
      message: layout
        ? `Elemen HTML hanya boleh di atom; ${who} hanya boleh ${LAYOUT_TAGS.replaceAll('|', '/')} untuk tata letak (docs/33 §2).`
        : `${who} hanya menyusun template — tanpa elemen HTML, termasuk div (docs/33 §2).`,
    },
    // Teks yang diberikan sebagai isi atom/komponen (mis. <Button>Simpan</Button>) dirender atom itu — boleh.
    {
      selector: "JSXElement[openingElement.name.type='JSXIdentifier'][openingElement.name.name=/^[a-z]/] > JSXText[value=/\\S/]",
      message: `Teks di elemen HTML pada ${who} — bungkus dengan atom Text (docs/33 §2).`,
    },
    { selector: 'JSXFragment > JSXText[value=/\\S/]', message: `Teks langsung di ${who} — bungkus dengan atom Text (docs/33 §2).` },
  ],
})
const RULES = {
  page: composition('Page', [ATOMS('Page'), MOLECULES('Page'), ORGANISMS('Page')], false),
  template: composition('Template', [ATOMS('Template'), MOLECULES('Template')], true),
  organism: composition('Organism', [ATOMS('Organism'), TEMPLATES('Organism')], true),
  molecule: composition('Molecule', [tier('organisms', 'Molecule', 'tidak boleh mengimpor organism'), TEMPLATES('Molecule'), SAME_MOLECULE], true),
}
export default tseslint.config(
  { ignores: ['dist', 'legacy_ref'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
    },
  },
  {
    files: ['src/components/atoms/**'],
    rules: {
      'react-refresh/only-export-components': 'off',
      'no-restricted-imports': ['error', { patterns: [PAGES, tier('molecules', 'Atom', 'tidak boleh mengimpor molecule'), tier('organisms', 'Atom', 'tidak boleh mengimpor organism'), TEMPLATES('Atom'), ...EXTRA] }],
    },
  },
  {
    files: ['src/components/molecules/**/*.tsx'],
    ignores: ['**/*.test.tsx'],
    rules: RULES.molecule,
  },
  {
    files: ['src/components/organisms/**/*.tsx'],
    ignores: ['**/*.test.tsx'],
    rules: RULES.organism,
  },
  {
    files: ['src/components/templates/**/*.tsx'],
    ignores: ['**/*.test.tsx'],
    rules: RULES.template,
  },
  {
    files: ['src/services/**', 'src/hooks/**', 'src/stores/**'],
    rules: { 'no-restricted-imports': ['error', { patterns: [PAGES, COMPONENTS, ...EXTRA] }] },
  },
  {
    files: ['src/lib/**', 'src/schemas/**'],
    rules: { 'no-restricted-imports': ['error', { patterns: [PAGES, COMPONENTS, DATA, ...EXTRA] }] },
  },
  {
    files: ['src/pages/**/*.tsx'],
    ignores: ['**/*.test.tsx'],
    rules: RULES.page,
  },
  // ---- G0 penegak: batas modul, siklus, ukuran ----
  {
    files: ['src/**/*.{ts,tsx}'],
    ignores: ['src/test/**', '**/*.test.{ts,tsx}'],
    plugins: { import: importPlugin },
    settings: {
      'import/extensions': ['.ts', '.tsx'],
      'import/parsers': { '@typescript-eslint/parser': ['.ts', '.tsx'] },
      'import/resolver': { typescript: { project: './tsconfig.app.json' } },
    },
    rules: {
      // Tingkat 'error' + eslint-suppressions.json (bukan 'warn'): `--max-warnings 0` membuat peringatan tak bisa
      // diberi baseline, sedangkan suppressions menghitung pelanggaran lama dan menggagalkan pelanggaran baru.
      'import/no-cycle': ['error', { maxDepth: 6 }],
      'max-lines': ['error', { max: 300, skipBlankLines: true, skipComments: true }],
      'max-lines-per-function': ['error', { max: 80, skipBlankLines: true, skipComments: true, IIFEs: true }],
      complexity: ['error', 12],
    },
  },
  {
    // Berkas > 500 baris (tanpa baris kosong/komentar) adalah galat; berkas lama masuk eslint-suppressions.json.
    files: ['src/**/*.{ts,tsx}'],
    ignores: ['src/test/**', '**/*.test.{ts,tsx}', 'src/lib/apiTypes.ts', 'src/**/apiTypes.ts'],
    // `max-lines` inti tak bisa punya dua tingkat (warn 300 + error 500), jadi batas keras memakai salinan aturan yang sama.
    plugins: { vms: { rules: { 'max-lines-hard': builtinRules.get('max-lines') } } },
    rules: { 'vms/max-lines-hard': ['error', { max: 500, skipBlankLines: true, skipComments: true }] },
  },
  {
    files: ['src/**/apiTypes.ts'],
    rules: { 'max-lines': 'off', 'vms/max-lines-hard': 'off', 'max-lines-per-function': 'off', complexity: 'off' },
  },
  {
    // Organisme lintas domain tidak saling impor (docs/rencana/struktur-dan-kualitas-kode.md 1.3).
    // `organisms/<domain>/X` hanya boleh mengimpor domain yang sama, `organisms/X` (bersama), molecules, atoms.
    files: ['src/components/organisms/**/*.{ts,tsx}'],
    ignores: ['**/*.test.{ts,tsx}'],
    plugins: { boundaries },
    settings: {
      'import/resolver': { typescript: { project: './tsconfig.app.json' } },
      'boundaries/elements': [
        { type: 'organism-domain', pattern: 'src/components/organisms/*/**', capture: ['domain'], partialMatch: false },
        { type: 'other', pattern: 'src/**', partialMatch: false },
      ],
    },
    rules: {
      'boundaries/dependencies': ['error', {
        default: 'allow',
        policies: [{
          from: { element: { type: 'organism-domain' } },
          disallow: { to: { element: { type: 'organism-domain', captured: { domain: '!{{from.domain}}' } } } },
          message: 'Organisme satu domain tidak boleh mengimpor organisme domain lain; pindahkan bagian bersama ke organisms/ (tingkat atas) atau molecules.',
        }],
      }],
    },
  },
)
