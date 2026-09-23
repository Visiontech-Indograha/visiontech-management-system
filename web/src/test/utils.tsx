import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import axios from "axios";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { mockMe } from "@/app/mockSession";
import { routes } from "@/app/routes";
import { SessionProvider } from "@/app/session";
import { api } from "@/lib/api";
import type { Me } from "@/lib/types";

/** JSON → objek; FormData → objek (nilai berulang dijadikan array). */
function parseBody(data: unknown): unknown {
  if (!data) return undefined;
  if (data instanceof FormData) {
    const out: Record<string, unknown> = {};
    data.forEach((v, k) => {
      out[k] = k in out ? [...([] as unknown[]).concat(out[k]), v] : v;
    });
    return out;
  }
  return JSON.parse(data as string);
}

export type Handler = (config: InternalAxiosRequestConfig) => { status?: number; data?: unknown } | undefined;

/** Ganti adapter axios dengan handler in-memory. Handler mengembalikan undefined → 404 uniform. */
export function mockApi(handler: Handler) {
  const calls: { method: string; url: string; data: unknown }[] = [];
  api.defaults.adapter = ((config: InternalAxiosRequestConfig) => {
    const method = (config.method ?? "get").toLowerCase();
    const url = String(config.url);
    calls.push({ method, url, data: parseBody(config.data) });
    const out = handler(config) ?? {
      status: 404,
      data: { error: { code: "NOT_FOUND", message: "Data tidak ditemukan.", details: {} } },
    };
    const status = out.status ?? 200;
    const response = { data: out.data, status, statusText: "", headers: {}, config } as AxiosResponse;
    return status < 400
      ? Promise.resolve(response)
      : Promise.reject(new axios.AxiosError("err", String(status), config, null, response));
  }) as AxiosAdapter;
  return calls;
}

export function apiError(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
  return { status, data: { error: { code, message, details } } };
}

export function renderRoute(path: string, opts: { role?: string | null; me?: Me | null } = {}) {
  const me = opts.me !== undefined ? opts.me : opts.role ? mockMe(opts.role) : null;
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const utils = render(
    <QueryClientProvider client={client}>
      <SessionProvider initial={me}>
        <RouterProvider router={router} />
      </SessionProvider>
    </QueryClientProvider>,
  );
  return { router, ...utils };
}
