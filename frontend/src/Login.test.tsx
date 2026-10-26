import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "./App";
import { AuthProvider } from "./auth";
import { setToken } from "./api/client";

const b64 = (o: unknown) => btoa(JSON.stringify(o)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
const tokenFor = (role: string) => {
  const exp = Math.floor(Date.now() / 1000) + 3600;
  return `${b64({ alg: "HS256" })}.${b64({ sub: `demo.${role}`, role, iss: "ancora-azul-api", iat: exp - 3600, exp })}.sig`;
};

let calls: { method: string; path: string }[] = [];
function mockApi(enabled: boolean) {
  calls = [];
  vi.stubGlobal("fetch", vi.fn((url: URL, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    calls.push({ method, path: url.pathname });
    if (url.pathname === "/auth/demo" && method === "GET") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ enabled }) } as Response);
    if (url.pathname.startsWith("/auth/demo/")) {
      const role = url.pathname.split("/").pop()!;
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ token: tokenFor(role), role, expires_in: 3600 }) } as Response);
    }
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ detail: "x" }) } as Response);
  }));
}

beforeEach(() => { sessionStorage.clear(); setToken(undefined); });
afterEach(() => vi.unstubAllGlobals());

it("shows one demo button per role and signs in with the chosen one", async () => {
  mockApi(true);
  render(<AuthProvider><App /></AuthProvider>);
  for (const name of ["Entrar como Analista", "Entrar como Gestor", "Entrar como Auditor"]) expect(await screen.findByRole("button", { name })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Entrar como Auditor" }));
  await waitFor(() => expect(screen.getByText("auditor")).toBeInTheDocument());
  expect(calls).toContainEqual({ method: "POST", path: "/auth/demo/auditor" });
  expect(sessionStorage.getItem("ancora.token")).toBeTruthy();
});

it("hides demo buttons when the API has demo login disabled", async () => {
  mockApi(false);
  render(<AuthProvider><App /></AuthProvider>);
  await waitFor(() => expect(calls.some((c) => c.path === "/auth/demo")).toBe(true));
  expect(screen.queryByRole("button", { name: /Entrar como/ })).not.toBeInTheDocument();
  expect(screen.getByText("Entrar com token de acesso")).toBeInTheDocument();
});
