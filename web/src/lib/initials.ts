/** Inisial dari nama (dua kata pertama); cadangan "?" bila kosong. */
export function initialsOf(name: string | null | undefined): string {
  const parts = (name ?? "").replace(/[^\p{L}\p{N} ]/gu, " ").split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}
