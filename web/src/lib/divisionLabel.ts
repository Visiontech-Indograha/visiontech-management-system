/** Label divisi untuk pilihan: nama saja; kode ditambahkan hanya bila ada nama kembar agar tetap bisa dibedakan. */
export function divisionOptionLabel(d: { name: string; code: string }, all: readonly { name: string }[]): string {
  const kembar = all.filter((x) => x.name === d.name).length > 1;
  return kembar ? `${d.name} (${d.code})` : d.name;
}
