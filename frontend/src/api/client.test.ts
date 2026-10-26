import { afterEach, describe, expect, it, vi } from "vitest";
import { api, get } from "./client";

const ok = (body: unknown) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) } as Response);

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("monta querystring ignorando valores vazios", async () => {
    const f = vi.fn(() => ok({}));
    vi.stubGlobal("fetch", f);
    await get("/clientes", { limit: 10, profile: undefined, segment: "" , min_risk: 0 });
    const url = String((f.mock.calls[0] as unknown[])[0]);
    expect(url).toContain("/clientes?limit=10&min_risk=0");
    expect(url).not.toContain("profile");
  });

  it("propaga erro com detalhe da API", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: false, status: 422, json: () => Promise.resolve({ detail: "sort invalido" }) } as Response)));
    await expect(get("/clientes")).rejects.toThrow("Erro 422 ao consultar /clientes: sort invalido");
  });

  it("codifica o id do cliente", async () => {
    const f = vi.fn(() => ok({}));
    vi.stubGlobal("fetch", f);
    await api.customer("C 1/2");
    expect(String((f.mock.calls[0] as unknown[])[0])).toContain("/clientes/C%201%2F2");
  });

  it("allCustomers percorre as paginas de 200 itens", async () => {
    const f = vi.fn((url: URL) => {
      const offset = Number(url.searchParams.get("offset"));
      return ok({ total: 450, limit: 200, offset, items: Array.from({ length: Math.min(200, 450 - offset) }, (_, i) => ({ customer_id: `C${offset + i}` })) });
    });
    vi.stubGlobal("fetch", f);
    const all = await api.allCustomers();
    expect(all).toHaveLength(450);
    expect(f).toHaveBeenCalledTimes(3);
  });
});
