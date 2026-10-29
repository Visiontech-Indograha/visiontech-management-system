/**
 * Tombol per peran (docs/diagram/00-peran-dan-izin.md §2). Fungsi murni atas daftar izin pengguna dan status baris,
 * supaya komponen dan matriks uji (src/test/peran-status-matrix.test.ts) memakai aturan yang sama.
 * Izin = nama permission dari API (lib/permissions.ts). Otorisasi sungguhan tetap di API; ini hanya tampilan.
 */

export type WorkTypeAction = "edit" | "materials" | "copy" | "deactivate";
export type AssetRowAction = "lend" | "files" | "status";
export type MessAction = "manageStays" | "managePlaces" | "reviewRequests";

/** Jenis pekerjaan = template: pengelola rencana (create:plan) mengubah, menyalin, menonaktifkan; yang aktif saja
 * yang bisa disalin/dinonaktifkan. Peran lain hanya melihat. */
export function workTypeActions(permissions: readonly string[], isActive: boolean): WorkTypeAction[] {
  if (!permissions.includes("create:plan")) return [];
  return isActive ? ["edit", "materials", "copy", "deactivate"] : ["edit", "materials"];
}

/** Aset (kendaraan & alat): pengelola aset (manage:assets, HR/ASSET) menyerahkan, mengubah status. Berkas kendaraan
 * dapat dibuka semua yang melihat halaman. Aset yang sedang dipinjam tidak bisa diubah statusnya. */
export const canManageAssets = (permissions: readonly string[]) => permissions.includes("manage:assets");

export function assetRowActions(
  canManage: boolean,
  kind: "VEHICLE" | "TOOL",
  status: string,
  assigned: boolean,
): AssetRowAction[] {
  if (!canManage && kind === "TOOL") return [];
  const actions: AssetRowAction[] = [];
  if (canManage && status === "ready") actions.push("lend");
  if (kind === "VEHICLE") actions.push("files");
  if (canManage && !assigned) actions.push("status");
  return actions;
}

/** Mess: pengelola hunian (manage:mess, HR) mengelola penginapan & tempat; peninjau (review:mess, PM/OM/HR)
 * menerima permintaan. Tab lain tidak tampil. */
export function messActions(permissions: readonly string[]): MessAction[] {
  const actions: MessAction[] = [];
  if (permissions.includes("manage:mess")) actions.push("manageStays", "managePlaces");
  if (permissions.includes("review:mess")) actions.push("reviewRequests");
  return actions;
}
