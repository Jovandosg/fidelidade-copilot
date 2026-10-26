import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { setToken, setUnauthorizedHandler } from "./api/client";

export type Role = "analista" | "gestor" | "auditor";

export interface Principal {
  sub: string;
  role: Role;
  exp: number;
}

const ROLES: Role[] = ["analista", "gestor", "auditor"];
const STORAGE_KEY = "ancora.token";

// Decodifica apenas para exibir/ajustar a UI. A autorizacao real e sempre da API (assinatura HS256 verificada la).
export function parseToken(token: string): Principal | null {
  const parts = token.trim().split(".");
  if (parts.length !== 3) return null;
  try {
    const b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = new TextDecoder().decode(Uint8Array.from(atob(b64.padEnd(Math.ceil(b64.length / 4) * 4, "=")), (c) => c.charCodeAt(0)));
    const p = JSON.parse(json) as Partial<Principal>;
    if (typeof p.sub !== "string" || typeof p.exp !== "number" || !ROLES.includes(p.role as Role)) return null;
    return { sub: p.sub, role: p.role as Role, exp: p.exp };
  } catch {
    return null;
  }
}

const isExpired = (p: Principal) => p.exp * 1000 <= Date.now();

interface AuthState {
  principal: Principal | null;
  notice?: string;
  login: (token: string) => string | null;
  logout: (notice?: string) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth fora do AuthProvider");
  return ctx;
}

function restore(): Principal | null {
  const stored = sessionStorage.getItem(STORAGE_KEY);
  const p = stored ? parseToken(stored) : null;
  if (stored && p && !isExpired(p)) {
    setToken(stored);
    return p;
  }
  sessionStorage.removeItem(STORAGE_KEY);
  setToken(undefined);
  return null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [principal, setPrincipal] = useState<Principal | null>(restore);
  const [notice, setNotice] = useState<string>();

  const logout = useCallback((msg?: string) => {
    sessionStorage.removeItem(STORAGE_KEY);
    setToken(undefined);
    setPrincipal(null);
    setNotice(msg);
  }, []);

  const login = useCallback((raw: string) => {
    const token = raw.trim();
    const p = parseToken(token);
    if (!p) return "Token inválido: cole o token completo emitido por `python -m src.api.tokens`.";
    if (isExpired(p)) return "Token expirado: emita um novo token.";
    sessionStorage.setItem(STORAGE_KEY, token);
    setToken(token);
    setNotice(undefined);
    setPrincipal(p);
    return null;
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => logout("Sessão encerrada: token inválido ou expirado. Entre novamente."));
    return () => setUnauthorizedHandler(undefined);
  }, [logout]);

  useEffect(() => {
    if (!principal) return;
    const ms = principal.exp * 1000 - Date.now();
    const t = setTimeout(() => logout("Token expirado. Entre novamente."), Math.min(Math.max(ms, 0), 2_147_000_000));
    return () => clearTimeout(t);
  }, [principal, logout]);

  const value = useMemo(() => ({ principal, notice, login, logout }), [principal, notice, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
