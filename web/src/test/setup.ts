import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach } from 'vitest'
import { useDrafts } from '@/hooks/useFormDraft'

// Mesin CI/verify-branch sempit memori: findBy* bawaan 1 detik terlalu pendek saat beban tinggi;
// 5 dtk pun sempat gagal saat uji API berjalan bersamaan (R-19) — lulus cepat tetap cepat.
// 10 dtk pun gagal saat 4 vitest berjalan bersamaan (impor malas halaman pertama 10-13 dtk); batas tes 30 dtk.
configure({ asyncUtilTimeout: 20000 })

if (typeof window !== "undefined" && !window.ResizeObserver) {
  window.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

afterEach(() => {
  cleanup()
  useDrafts.setState({ drafts: {} }) // draf laporan (R5) tidak bocor antar-uji
})
