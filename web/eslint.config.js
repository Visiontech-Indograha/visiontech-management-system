import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

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

const LAYOUT_TAGS = 'div|section|main|header|footer|article|aside|nav'
/** Larangan susunan: impor tingkat terlarang + elemen HTML (kecuali tata letak bila `layout`) + teks langsung. */
const composition = (who, patterns, layout) => ({
  'no-restricted-imports': ['error', {
    patterns: [PAGES, ...patterns],
    paths: [
      { name: 'lucide-react', message: `Ikon adalah atom; ${who} dilarang memakainya langsung (docs/33 §2).` },
      { name: 'react-router-dom', importNames: ['Link', 'NavLink'], message: `Tautan adalah atom; ${who} dilarang memakainya langsung (docs/33 §2).` },
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
      'no-restricted-imports': ['error', { patterns: [PAGES, tier('molecules', 'Atom', 'tidak boleh mengimpor molecule'), tier('organisms', 'Atom', 'tidak boleh mengimpor organism'), TEMPLATES('Atom')] }],
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
    rules: RULES.page,
  },
)
