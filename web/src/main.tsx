import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { Toaster } from "react-hot-toast";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { routes } from "@/app/routes";
import { SessionProvider } from "@/app/session";
import { queryClient } from "@/lib/queryClient";
import "@/styles/index.css";

const router = createBrowserRouter(routes);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <SessionProvider>
        <RouterProvider router={router} />
        <Toaster position="bottom-right" />
      </SessionProvider>
    </QueryClientProvider>
  </StrictMode>,
);
