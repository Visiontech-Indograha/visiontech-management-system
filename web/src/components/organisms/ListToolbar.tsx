import type { ReactNode } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ControlInput } from "@/components/molecules/FormBlock";

const inputCls = "h-10 rounded-control border border-line bg-surface px-3 text-sm";

/**
 * Baris cari + filter di atas daftar. Filter (select/chip) dikirim sebagai `children`;
 * tombol "Atur ulang" muncul hanya bila ada pencarian/filter aktif.
 */
export function ListToolbar({ value, onChange, placeholder, active, onReset, children }: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  active: boolean;
  onReset: () => void;
  children?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-3">
      <ControlInput
        type="search"
        aria-label={placeholder}
        placeholder={placeholder}
        maxLength={100}
        autoComplete="off"
        className={`${inputCls} w-full md:w-64`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {children}
      {active && (
        <ActionButton variant="outline" onClick={onReset}>
          Atur ulang
        </ActionButton>
      )}
    </div>
  );
}
