import { Button } from "@/components/atoms/Button";
import { Text } from "@/components/atoms/Text";
import { cn } from "@/lib/utils";

/** Baris pilihan cepat (mis. lokasi terakhir, preset radius/jam): tiap chip memanggil `onPick` dengan kuncinya. */
export function ChoiceChips({
  label,
  items,
  activeKey,
  onPick,
  testId,
}: {
  label: string;
  items: { key: string; label: string }[];
  activeKey?: string;
  onPick: (key: string) => void;
  testId?: string;
}) {
  if (items.length === 0) return null;
  return (
    <div className="mb-3 flex flex-wrap items-center gap-1.5" data-testid={testId}>
      <Text as="span" className="mr-1 text-xs font-medium text-muted-foreground">
        {label}
      </Text>
      {items.map((it) => {
        const active = activeKey !== undefined && activeKey === it.key;
        return (
          <Button
            key={it.key}
            type="button"
            variant={active ? "default" : "outline"}
            size="sm"
            className={cn(
              "min-h-8 rounded-full px-3 text-xs font-medium",
              active ? "shadow-xs" : "bg-surface text-foreground hover:border-primary/40 hover:bg-accent hover:text-primary",
            )}
            onClick={() => onPick(it.key)}
          >
            {it.label}
          </Button>
        );
      })}
    </div>
  );
}
