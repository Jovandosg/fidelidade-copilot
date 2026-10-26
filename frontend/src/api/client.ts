import type { components } from "./schema";

export type Kpis = components["schemas"]["Kpis"];
export type Customer = components["schemas"]["CustomerFeature"];
export type CustomerPage = components["schemas"]["CustomerPage"];
export type RoutePage = components["schemas"]["RoutePage"];
export type NbaPage = components["schemas"]["NbaPage"];

export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const MAX_LIMIT = 200;

type Params = Record<string, string | number | boolean | undefined>;

export async function get<T>(path: string, params: Params = {}, signal?: AbortSignal): Promise<T> {
  const url = new URL(path, API_URL);
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
  const res = await fetch(url, { signal });
  if (!res.ok) {
    const detail = await res.json().then((j) => (typeof j.detail === "string" ? j.detail : "")).catch(() => "");
    throw new Error(`Erro ${res.status} ao consultar ${path}${detail ? `: ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  kpis: (params: Params = {}) => get<Kpis>("/kpis", params),
  customers: (params: Params = {}) => get<CustomerPage>("/clientes", params),
  customer: (id: string) => get<Customer>(`/clientes/${encodeURIComponent(id)}`),
  routes: (params: Params = {}) => get<RoutePage>("/rotas", params),
  nba: (params: Params = {}) => get<NbaPage>("/nba", params),
  // A API limita a pagina a 200 itens; percorre as paginas para o mapa valor x risco.
  async allCustomers(cap = 2000): Promise<Customer[]> {
    const first = await get<CustomerPage>("/clientes", { limit: MAX_LIMIT, offset: 0 });
    const items = [...first.items];
    for (let offset = MAX_LIMIT; offset < Math.min(first.total, cap); offset += MAX_LIMIT) {
      items.push(...(await get<CustomerPage>("/clientes", { limit: MAX_LIMIT, offset })).items);
    }
    return items;
  },
};
