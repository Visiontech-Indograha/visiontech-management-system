import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { Button } from "./Button"

describe("Button pending", () => {
  it("nonaktif dan memakai teks proses saat pending", () => {
    render(<Button pending pendingText="Menyimpan…">Simpan</Button>)
    const b = screen.getByRole("button", { name: "Menyimpan…" })
    expect(b).toBeDisabled()
    expect(b).toHaveAttribute("aria-busy", "true")
  })
  it("normal saat tidak pending", () => {
    render(<Button pendingText="Menyimpan…">Simpan</Button>)
    expect(screen.getByRole("button", { name: "Simpan" })).toBeEnabled()
  })
})
