import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReviewReasonsNote } from "./ReviewReasonsNote";

const base = { status: "NEEDS_REVIEW", check_out_at: null };

describe("ReviewReasonsNote", () => {
  it("menampilkan alasan, akurasi, dan tombol daftar wajah", () => {
    const onEnroll = vi.fn();
    render(<ReviewReasonsNote rec={{ ...base, review_reasons: ["FACE_NOT_ENROLLED", "LOKASI_KASAR"], location_accuracy_m: 500 }} onEnroll={onEnroll} />);
    expect(screen.getByText("Wajah Anda belum terdaftar. Daftarkan wajah dulu.")).toBeTruthy();
    expect(screen.getByText(/laptop tanpa GPS/)).toBeTruthy();
    expect(screen.getByText("Akurasi lokasi ±500 m")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Daftar wajah" }));
    expect(onEnroll).toHaveBeenCalled();
  });
  it("tanpa alasan memakai catatan lama", () => {
    render(<ReviewReasonsNote rec={base} onEnroll={() => undefined} />);
    expect(screen.getByText(/menunggu pemeriksaan/)).toBeTruthy();
  });
});
