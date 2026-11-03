import type { ReactNode } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ControlInput } from "@/components/molecules/FormBlock";
import { X } from "@/components/molecules/Glyphs";
import { PlainAction } from "@/components/molecules/PlainAction";
import { TextBlock } from "@/components/molecules/TextBlock";

const inputCls = "h-11 rounded-control border border-line bg-surface pl-3.5 pr-9 text-sm shadow-xs focus-visible:border-ring focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50";

/**
 * Baris cari + filter di atas daftar. Filter (select/chip) dikirim sebagai `children`;
 * tombol "Atur ulang" muncul hanya bila ada pencarian/filter aktif.
 */
export function ListToolbar({
  value,
  onChange,
  placeholder,
  active,
  onReset,
  countLabel,
  children,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  active: boolean;
  onReset: () => void;
  countLabel?: string;
  children?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2.5">
      <div className="relative w-full md:w-72">
        <ControlInput
          type="search"
          aria-label={placeholder}
          placeholder={placeholder}
          maxLength={100}
          autoComplete="off"
          className={`${inputCls} w-full`}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        {value.length > 0 && (
          <PlainAction
            type="button"
            aria-label="Bersihkan pencarian"
            onClick={() => onChange("")}
            className="absolute right-2 top-1/2 flex size-7 -translate-y-1/2 items-center justify-center rounded-full text-mist hover:bg-hover hover:text-ink"
          >
            <X size={15} />
          </PlainAction>
        )}
      </div>
      {children}
      {active && (
        <ActionButton variant="outline" size="sm" onClick={onReset} className="h-11 px-3.5">
          Atur ulang
        </ActionButton>
      )}
      {countLabel && (
        <TextBlock as="span" className="ml-auto text-xs font-medium text-mist">
          {countLabel}
        </TextBlock>
      )}
    </div>
  );
}
