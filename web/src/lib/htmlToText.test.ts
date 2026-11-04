import { describe, expect, it } from "vitest";
import { htmlToText } from "./htmlToText";

describe("htmlToText", () => {
  it("teks biasa tidak berubah", () => {
    expect(htmlToText("Pakai helm\nSetiap hari")).toBe("Pakai helm\nSetiap hari");
  });
  it("tag blok menjadi baris dan tag lain dibuang", () => {
    expect(htmlToText("<h2>Judul</h2><p>Isi <b>tebal</b></p><ul><li>satu</li><li>dua</li></ul>")).toBe(
      "Judul\n\nIsi tebal\n\n\n• satu\n• dua".replace("\n\n\n", "\n\n"),
    );
  });
  it("br jadi baris baru, script dibuang, entitas didekode", () => {
    expect(htmlToText("a<br/>b<script>alert(1)</script> &amp; c")).toBe("a\nb & c");
  });
  it("null menjadi string kosong", () => {
    expect(htmlToText(null)).toBe("");
  });
});
