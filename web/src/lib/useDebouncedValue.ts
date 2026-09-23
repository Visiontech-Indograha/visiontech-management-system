import { useEffect, useState } from "react";

/** Kembalikan `value` setelah tidak berubah selama `delayMs` — dipakai untuk search-as-you-type. */
export function useDebouncedValue<T>(value: T, delayMs = 350): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
