import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach } from 'vitest'

// Mesin CI/verify-branch sempit memori: findBy* bawaan 1 detik terlalu pendek saat beban tinggi.
configure({ asyncUtilTimeout: 5000 })

afterEach(() => {
  cleanup()
})
