import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach } from 'vitest'
import { useDrafts } from '@/lib/drafts'

// Mesin CI/verify-branch sempit memori: findBy* bawaan 1 detik terlalu pendek saat beban tinggi;
// 5 dtk pun sempat gagal saat uji API berjalan bersamaan (R-19) — lulus cepat tetap cepat.
configure({ asyncUtilTimeout: 10000 })

afterEach(() => {
  cleanup()
  useDrafts.setState({ drafts: {} }) // draf laporan (R5) tidak bocor antar-uji
})
