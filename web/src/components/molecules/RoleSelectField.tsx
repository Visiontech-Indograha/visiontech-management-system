import type { ChangeEvent } from "react";
import { Label } from "@/components/atoms/Label";
import { Select, SelectOption } from "@/components/atoms/Select";
import { Text } from "@/components/atoms/Text";

/** Dropdown "Peran" (label Indonesia). Nilai dan label diberikan pemanggil; molekul hanya menyusun atom. */
export function RoleSelectField({ label, value, options, onChange }: {
  label: string;
  value: string;
  options: Record<string, string>;
  onChange: (value: string) => void;
}) {
  return (
    <Label className="flex flex-col gap-1 text-sm">
      <Text as="span" className="text-xs font-medium text-mist">{label}</Text>
      <Select
        value={value}
        onChange={(e: ChangeEvent<HTMLSelectElement>) => onChange(e.target.value)}
        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
      >
        {Object.entries(options).map(([v, text]) => (
          <SelectOption key={v} value={v}>{text}</SelectOption>
        ))}
      </Select>
    </Label>
  );
}
