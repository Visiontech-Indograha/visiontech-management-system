import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { UploadField } from "./UploadField";

describe("UploadField", () => {
  it("menampilkan label, memakai input berkas, dan meneruskan perubahan", () => {
    const onChange = vi.fn();
    render(<UploadField label="Berkas baru" hint="Maks 10 MB" onChange={onChange} />);
    const input = screen.getByLabelText("Berkas baru") as HTMLInputElement;
    expect(input.type).toBe("file");
    fireEvent.change(input);
    expect(onChange).toHaveBeenCalled();
  });
});
