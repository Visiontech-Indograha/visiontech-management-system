import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

// Atomic design (docs/33, keputusan pemilik 2026-10-09).
// Urutan: tampilan UI > Page > Template > Organism > Molecule > Atom — tiap tingkat hanya menyusun tingkat di bawahnya.
// Struktur berbasis lapisan (pemilik 2026-10-09): pages/ · components/ · services/ · schemas/ · hooks/ · lib/.
const PAGES = { group: ['@/pages/*', '**/pages/**'], message: 'Hanya app/ (rute) yang boleh mengimpor pages/ (docs/33 §2.2).' }
const COMPONENTS = { group: ['@/components/*', '**/components/**'], message: 'services/, schemas/, hooks/, lib/ tidak boleh mengimpor components/ (docs/33 §2.2).' }
const DATA = { group: ['@/services/*', '**/services/**', '@/hooks/*', '**/hooks/**'], message: 'lib/ dan schemas/ tidak boleh mengimpor services/ atau hooks/ (docs/33 §2.2).' }
const level = (names, who) => ({
  group: names.flatMap((n) => [`@/components/${n}/*`, `**/components/${n}/**`, `../${n}/*`]),
  message: `${who} tidak boleh mengimpor tingkat yang sama atau di atasnya (docs/33 §2.2).`,
})

// Page dan Template hanya menyusun organism (+ template untuk Page) dan tata letak polos (docs/33 §2.1).
const LAYOUT_TAGS = 'div|section|main|header|footer|article|aside'
const compositionRules = (who, extraPatterns = []) => ({
  'no-restricted-imports': ['error', {
    patterns: [
      { group: ['@/components/atoms/*', '**/components/atoms/**', '../atoms/*'], message: `${who} dilarang memakai atom langsung — pindahkan bagian ini ke organism (docs/33 §2.1).` },
      { group: ['@/components/molecules/*', '**/components/molecules/**', '../molecules/*'], message: `${who} dilarang memakai molecule langsung — pindahkan bagian ini ke organism (docs/33 §2.1).` },
      ...extraPatterns,
    ],
    paths: [
      { name: 'lucide-react', message: `Ikon adalah atom; ${who} dilarang memakainya langsung (docs/33 §2.1).` },
      { name: 'react-router-dom', importNames: ['Link', 'NavLink'], message: 'Tautan adalah atom; letakkan di organism (docs/33 §2.1).' },
    ],
  }],
  'no-restricted-syntax': ['error',
    {
      selector: `JSXOpeningElement[name.type='JSXIdentifier'][name.name=/^[a-z]/]:not([name.name=/^(${LAYOUT_TAGS})$/])`,
      message: `Elemen HTML mentah setara atom/molecule; ${who} hanya boleh ${LAYOUT_TAGS.replaceAll('|', '/')} untuk tata letak (docs/33 §2.1).`,
    },
    { selector: 'JSXText[value=/\\S/]', message: `Teks langsung di ${who} — letakkan di organism (docs/33 §2.1).` },
  ],
})

// Page/Template lama yang BELUM dimigrasi (docs/33 §7). Daftar ini HANYA BOLEH MENYUSUT.
const NOT_YET_MIGRATED = [
  'src/pages/assets/AssetsPage.tsx',
  'src/pages/attendance/AttendancePage.tsx',
  'src/pages/work-plans/PlanEditorPage.tsx',
]

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
      'no-restricted-imports': ['error', { patterns: [PAGES, level(['molecules', 'organisms', 'templates'], 'Atom')] }],
    },
  },
  {
    files: ['src/components/molecules/**'],
    ignores: ['**/*.test.tsx'],
    rules: {
      'no-restricted-imports': ['error', { patterns: [
        PAGES, level(['organisms', 'templates'], 'Molecule'),
        { group: ['./*', '@/components/molecules/*'], message: 'Molecule hanya menyusun atom, bukan molecule lain (docs/33 §2.2).' },
      ] }],
    },
  },
  {
    files: ['src/components/organisms/**'],
    rules: { 'no-restricted-imports': ['error', { patterns: [PAGES, level(['templates'], 'Organism')] }] },
  },
  {
    files: ['src/components/templates/**'],
    ignores: ['**/*.test.tsx'],
    rules: compositionRules('Template', [PAGES]),
  },
  {
    files: ['src/services/**', 'src/hooks/**'],
    rules: { 'no-restricted-imports': ['error', { patterns: [PAGES, COMPONENTS] }] },
  },
  {
    files: ['src/lib/**', 'src/schemas/**'],
    rules: { 'no-restricted-imports': ['error', { patterns: [PAGES, COMPONENTS, DATA] }] },
  },
  {
    files: ['src/pages/**/*.tsx'],
    ignores: ['**/*.test.tsx'],
    rules: compositionRules('Page'),
  },
  {
    files: NOT_YET_MIGRATED,
    rules: { 'no-restricted-imports': 'off', 'no-restricted-syntax': 'off' },
  },
)
