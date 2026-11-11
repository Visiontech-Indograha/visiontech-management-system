import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useForm } from "react-hook-form";
import { MemoryRouter } from "react-router-dom";
import { LoginForm } from "./LoginForm";
import type { LoginValues } from "@/schemas/loginSchema";

function TestLoginWrapper() {
  const form = useForm<LoginValues>({
    defaultValues: { email: "", password: "" },
  });
  return (
    <MemoryRouter>
      <LoginForm
        admin={false}
        form={form}
        onSubmit={vi.fn()}
        formError={null}
        lockSeconds={0}
      />
    </MemoryRouter>
  );
}

describe("LoginForm (U-42)", () => {
  it("menyediakan tombol toggle untuk melihat dan menyembunyikan kata sandi", () => {
    render(<TestLoginWrapper />);

    const passwordInput = document.getElementById("password") as HTMLInputElement;
    expect(passwordInput).toBeInTheDocument();
    expect(passwordInput.type).toBe("password");

    const toggleBtn = screen.getByRole("button", { name: "Tampilkan kata sandi" });
    expect(toggleBtn).toBeInTheDocument();

    fireEvent.click(toggleBtn);
    expect(passwordInput.type).toBe("text");
    expect(screen.getByRole("button", { name: "Sembunyikan kata sandi" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Sembunyikan kata sandi" }));
    expect(passwordInput.type).toBe("password");
    expect(screen.getByRole("button", { name: "Tampilkan kata sandi" })).toBeInTheDocument();
  });
});
