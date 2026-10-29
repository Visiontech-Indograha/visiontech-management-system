import { Button } from "@/components/atoms/Button";
import { Text } from "@/components/atoms/Text";

/** Baris pilihan cepat (mis. lokasi terakhir): tiap chip memanggil `onPick` dengan kuncinya. */
export function ChoiceChips({ label, items, onPick, testId }: {
  label: string;
  items: { key: string; label: string }[];
  onPick: (key: string) => void;
  testId?: string;
}) {
  if (items.length === 0) return null;
  return (
    <div className="mb-2 flex flex-wrap items-center gap-2" data-testid={testId}>
      <Text as="span" className="text-xs text-muted-foreground">{label}</Text>
      {items.map((it) => (
        <Button key={it.key} type="button" variant="outline" size="xs" onClick={() => onPick(it.key)}>
          {it.label}
        </Button>
      ))}
    </div>
  );
}
