import { Button } from "../atoms/Button";
import { Text } from "../atoms/Text";

/**
 * Kotak galat memuat data + tombol "Coba lagi" (keadaan galat, docs/11 §8).
 *
 *   <RetryNotice message="Lokasi kerja tidak dapat dimuat." onRetry={() => sites.refetch()} />
 */
export function RetryNotice({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="rounded-panel border border-line bg-surface shadow-card p-6 text-center">
      <Text className="mb-3 text-danger">{message}</Text>
      <Button variant="outline" onClick={onRetry}>
        Coba lagi
      </Button>
    </div>
  );
}
