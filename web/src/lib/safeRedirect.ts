/** Tujuan setelah login: hanya jalur internal (diawali satu "/"), selain itu kembali ke "/". */
export function safeRedirectPath(value: unknown): string {
  if (typeof value !== "string" || value.length > 2048) return "/";
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\")) return "/";
  if ([...value].some((ch) => ch.charCodeAt(0) < 32)) return "/";
  if (value === "/login" || value.startsWith("/login/") || value.startsWith("/admin-login")) return "/";
  return value;
}
