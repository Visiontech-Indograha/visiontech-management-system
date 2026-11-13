import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PasswordField } from "./Field";

describe("PasswordField (U-42: toggle lihat/sembunyikan kata sandi)", () => {
  it("merender input sandi tersembunyi secara bawaan dan berganti ke teks saat tombol toggle diklik", () => {
    render(<PasswordField label="Kata sandi" placeholder="Masukkan kata sandi" />);

    const input = screen.getByPlaceholderText("Masukkan kata sandi") as HTMLInputElement;
    expect(input.type).toBe("password");

    const toggleButton = screen.getByRole("button", { name: "Tampilkan kata sandi" });
    expect(toggleButton).toBeInTheDocument();
    expect(toggleButton.className).toMatch(/min-h-\[44px\]/);
    expect(toggleButton.className).toMatch(/min-w-\[44px\]/);

    // Klik untuk menampilkan
    fireEvent.click(toggleButton);
    expect(input.type).toBe("text");
    expect(screen.getByRole("button", { name: "Sembunyikan kata sandi" })).toBeInTheDocument();

    // Klik untuk menyembunyikan kembali
    fireEvent.click(screen.getByRole("button", { name: "Sembunyikan kata sandi" }));
    expect(input.type).toBe("password");
    expect(screen.getByRole("button", { name: "Tampilkan kata sandi" })).toBeInTheDocument();
  });
});
