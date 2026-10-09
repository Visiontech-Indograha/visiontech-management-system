import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

// Atomic design (docs/33, keputusan pemilik 2026-10-09). Arah impor: pages → templates/organisms → molecules → atoms.
const FEATURES = { group: ['@/features/*', '**/features/**'], message: 'components/ dan lib/ tidak boleh mengimpor features/ (docs/33 §2.2).' }
const COMPONENTS = { group: ['@/components/*', '**/components/**'], message: 'lib/ tidak boleh mengimpor components/ (docs/33 §2.2).' }
const level = (names, who) => ({
  group: names.flatMap((n) => [`@/components/${n}/*`, `**/components/${n}/**`, `../${n}/*`]),
  message: `${who} tidak boleh mengimpor tingkat di atasnya (docs/33 §2.2).`,
})

// Page hanya menyusun template + organism + tata letak polos (docs/33 §2.1).
const PAGE_LAYOUT_TAGS = 'div|section|main|header|footer|article|aside'
const pageRules = {
  'no-restricted-imports': ['error', {
    patterns: [
      { group: ['@/components/atoms/*', '**/components/atoms/**'], message: 'Page dilarang memakai atom langsung — pindahkan bagian ini ke organism (docs/33 §2.1).' },
      { group: ['@/components/molecules/*', '**/components/molecules/**'], message: 'Page dilarang memakai molecule langsung — pindahkan bagian ini ke organism (docs/33 §2.1).' },
    ],
    paths: [
      { name: 'lucide-react', message: 'Ikon adalah atom; Page dilarang memakainya langsung (docs/33 §2.1).' },
      { name: 'react-router-dom', importNames: ['Link', 'NavLink'], message: 'Tautan adalah atom; letakkan di organism (docs/33 §2.1).' },
    ],
  }],
  'no-restricted-syntax': ['error',
    {
      selector: `JSXOpeningElement[name.type='JSXIdentifier'][name.name=/^[a-z]/]:not([name.name=/^(${PAGE_LAYOUT_TAGS})$/])`,
      message: `Elemen HTML mentah setara atom/molecule; Page hanya boleh ${PAGE_LAYOUT_TAGS.replaceAll('|', '/')} untuk tata letak (docs/33 §2.1).`,
    },
    { selector: 'JSXText[value=/\\S/]', message: 'Teks langsung di Page — letakkan di organism (docs/33 §2.1).' },
  ],
}

// Page lama yang BELUM dimigrasi (docs/33 §7). Daftar ini HANYA BOLEH MENYUSUT.
const PAGES_NOT_YET_MIGRATED = [
  'src/features/account/pages/AccountPage.tsx',
  'src/features/assets/pages/AssetsPage.tsx',
  'src/features/attendance/pages/AttendancePage.tsx',
  'src/features/audit/pages/AuditLogPage.tsx',
  'src/features/auth/pages/ChangePasswordPage.tsx',
  'src/features/auth/pages/LoginPage.tsx',
  'src/features/directory/pages/DirectoryPage.tsx',
  'src/features/directory/pages/EmployeeDetailPage.tsx',
  'src/features/directory/pages/MyDocumentsPage.tsx',
  'src/features/face/pages/FaceEnrollRequiredPage.tsx',
  'src/features/home/pages/HomePage.tsx',
  'src/features/monitoring/pages/AttendanceRecapPage.tsx',
  'src/features/monitoring/pages/OvertimeRecapPage.tsx',
  'src/features/monitoring/pages/TimelinePage.tsx',
  'src/features/sites/pages/SitesPage.tsx',
  'src/features/system/pages/ComingSoonPage.tsx',
  'src/features/system/pages/ForbiddenPage.tsx',
  'src/features/system/pages/NotFoundPage.tsx',
  'src/features/verify/pages/VerifyPage.tsx',
  'src/features/work-plans/pages/PlanEditorPage.tsx',
  'src/features/work-plans/pages/PresentationPage.tsx',
  'src/features/work-plans/pages/WorkPlanDetailPage.tsx',
  'src/features/work-plans/pages/WorkPlansPage.tsx',
  'src/features/work-types/pages/WorkTypesPage.tsx',
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
      'no-restricted-imports': ['error', { patterns: [FEATURES, level(['molecules', 'organisms', 'templates'], 'Atom')] }],
    },
  },
  {
    files: ['src/components/molecules/**'],
    rules: { 'no-restricted-imports': ['error', { patterns: [FEATURES, level(['organisms', 'templates'], 'Molecule')] }] },
  },
  {
    files: ['src/components/organisms/**'],
    rules: { 'no-restricted-imports': ['error', { patterns: [FEATURES, level(['templates'], 'Organism')] }] },
  },
  {
    files: ['src/components/templates/**'],
    rules: { 'no-restricted-imports': ['error', { patterns: [FEATURES] }] },
  },
  {
    files: ['src/lib/**'],
    rules: { 'no-restricted-imports': ['error', { patterns: [FEATURES, COMPONENTS] }] },
  },
  {
    files: ['src/features/*/pages/**/*.tsx'],
    ignores: ['**/*.test.tsx'],
    rules: pageRules,
  },
  {
    files: PAGES_NOT_YET_MIGRATED,
    rules: { 'no-restricted-imports': 'off', 'no-restricted-syntax': 'off' },
  },
)
