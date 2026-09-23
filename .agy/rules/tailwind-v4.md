---
name: Tailwind CSS v4
description: Aturan AI untuk menggunakan Tailwind CSS v4 terbaru tanpa tailwind.config.js
---

# Aturan Tailwind CSS v4

Proyek ini menggunakan **Tailwind CSS v4** (versi terbaru). Terdapat perubahan besar dari versi 3 yang **WAJIB** Anda patuhi saat mengerjakan frontend web:

1. **Tanpa `tailwind.config.js`**: Jangan pernah mencoba membuat atau memodifikasi `tailwind.config.js` atau `tailwind.config.ts`. Konfigurasi Tailwind v4 murni dilakukan melalui file CSS (seperti `web/src/styles/index.css` atau `tokens.css`) menggunakan direktif `@theme`.
2. **Vite Plugin**: Tailwind diintegrasikan menggunakan plugin Vite `@tailwindcss/vite`, bukan melalui PostCSS. Jangan tambahkan `postcss.config.js` untuk keperluan Tailwind.
3. **Impor CSS Utama**: Jangan gunakan `@tailwind base; @tailwind components; @tailwind utilities;`. Di Tailwind v4, Anda hanya perlu melakukan impor tunggal: `@import "tailwindcss";` di bagian atas file CSS utama Anda.
4. **Variabel CSS**: Semua tema desain (warna, spacing, font) telah didefinisikan sebagai variabel CSS modern atau di dalam blok `@theme`. Patuhi token yang sudah ada.

Selalu periksa dokumentasi resmi Tailwind v4 jika merasa ragu terkait sintaks utilitas baru.
