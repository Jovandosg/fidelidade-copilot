import { useState } from "react";
import { useAuth } from "../auth";
import { Card, Notice } from "../components/ui";

export function LoginPage() {
  const { login, notice } = useAuth();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="mx-auto max-w-xl px-4 py-12">
      <h1 className="mb-1 text-2xl font-bold text-azul">Âncora Azul — CRM de alto valor</h1>
      <p className="mb-6 text-sm text-slate-500">Acesso restrito por perfil (analista, gestor ou auditor) · <strong>dados sintéticos</strong></p>
      <Card title="Entrar com token de acesso">
        <form
          className="space-y-3"
          onSubmit={(e) => { e.preventDefault(); setError(login(value)); }}
        >
          {notice && <Notice tone="warn">{notice}</Notice>}
          <label className="block text-sm">
            <span className="mb-1 block text-slate-600">Token (JWT)</span>
            <input
              type="password" autoComplete="off" spellCheck={false} value={value} onChange={(e) => setValue(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-2 py-1.5 font-mono text-xs"
            />
          </label>
          {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-2 text-sm text-red-700">{error}</div>}
          <button type="submit" disabled={!value.trim()} className="rounded-full bg-azul px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40">Entrar</button>
          <p className="text-xs text-slate-500">
            Emita um token local com <code>python -m src.api.tokens --sub seu.apelido --role gestor</code>. O token fica apenas nesta aba
            (sessionStorage) e é enviado somente no cabeçalho Authorization.
          </p>
        </form>
      </Card>
    </div>
  );
}
