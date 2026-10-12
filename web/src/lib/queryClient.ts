import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./apiClient";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (count, error) => {
        // Jangan mengulang kesalahan klien (4xx); ulang sekali untuk gangguan jaringan/5xx.
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
        return count < 1;
      },
    },
  },
});
