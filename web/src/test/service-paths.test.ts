import { describe, expect, it } from "vitest";

/** Pencegah: setiap jalur API di services harus ada di openapi.json (kasus reset-sandi 404). */
const spec = JSON.parse(
  Object.values(
    import.meta.glob("/openapi.json", { query: "?raw", import: "default", eager: true }) as Record<string, string>,
  )[0],
) as { paths: Record<string, Record<string, unknown>> };
const services = import.meta.glob(["/src/services/*.ts", "!/src/services/*.test.ts"], {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;
const specPaths = Object.keys(spec.paths).map((p) => p.split("/"));

function cocok(segs: string[]): boolean {
  return specPaths.some(
    (sp) =>
      sp.length === segs.length &&
      sp.every((s, i) => s.startsWith("{") || segs[i] === "{x}" || s === segs[i]),
  );
}

function ekstrak(src: string): string[] {
  const bases = new Map<string, string>();
  for (const m of src.matchAll(/const (\w+) = `([^`]*)`/g)) bases.set(m[1], m[2]);
  const hasil: string[] = [];
  const re = /\bapi\.(?:get|post|put|patch|delete)(?:<[^(]*?>)?\(\s*([`'"])([^`'"]*)\1/g;
  for (const m of src.matchAll(re)) {
    let p = m[2];
    const awal = /^\$\{(\w+)\}/.exec(p);
    if (awal && bases.has(awal[1])) p = bases.get(awal[1])! + p.slice(awal[0].length);
    p = p.replace(/\$\{[^}]*\}/g, "{x}").split("?")[0];
    if (p.startsWith("/")) hasil.push("/api/v1" + p);
  }
  return hasil;
}

describe("jalur API di services ada di openapi.json", () => {
  const files = Object.keys(services);
  it("cukup banyak jalur yang diperiksa", () => {
    expect(files.flatMap((f) => ekstrak(services[f])).length).toBeGreaterThan(100);
  });
  for (const f of files) {
    const paths = ekstrak(services[f]);
    if (!paths.length) continue;
    it(f, () => {
      const hilang = paths.filter((p) => !cocok(p.split("/")));
      expect(hilang).toEqual([]);
    });
  }
});
