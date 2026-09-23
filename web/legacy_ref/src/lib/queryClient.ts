import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false, // Jangan sering fetch ulang agar server tidak over-load
      retry: 1, // Hanya retry 1 kali jika gagal
    },
  },
});
