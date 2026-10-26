import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth";
import { Card, Notice } from "../components/ui";

const DEMO_ROLES = [
  { role: "analista", label: "Entrar como Analista", hint: "Consulta o dashboard, pergunta ao agente e gera propostas. Não decide." },
  { role: "gestor", label: "Entrar como Gestor", hint: "Tudo do analista + aprova ou rejeita propostas e ações (aprovação humana)." },
  { role: "auditor", label: "Entrar como Auditor", hint: "Somente leitura + trilha de auditoria. Não pergunta ao agente nem aprova." },
] as const;

function DemoLogin() {
  const { login } = useAuth();
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState<string>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    let alive = true;
    api.demoEnabled().then((r) => alive && setEnabled(r.enabled), () => undefined);
    return () => { alive = false; };
  }, []);

  if (!enabled) return null;
  const enter = async (role: string) => {
    setBusy(role); setError(undefined);
    try {
      const err = login((await api.demoToken(role)).token);
      if (err) setError(err);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(undefined);
    }
  };
  return (
    <Card title="Modo demonstração (teste cada perfil)" className="mb-4">
      <div className="mb-3"><Notice tone="warn">Habilitado só neste ambiente local (<code>DEMO_LOGIN=1</code>) com dados sintéticos. Cada botão abre uma sessão de 1 h com os privilégios reais do perfil.</Notice></div>
      <div className="grid gap-3 sm:grid-cols-3">
        {DEMO_ROLES.map((d) => (
          <div key={d.role} className="flex flex-col justify-between gap-2 rounded-lg border border-slate-200 p-3">
            <p className="text-xs text-slate-600">{d.hint}</p>
            <button type="button" disabled={busy !== undefined} onClick={() => void enter(d.role)}
              className="rounded-full bg-azul px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40">{busy === d.role ? "Entrando…" : d.label}</button>
          </div>
        ))}
      </div>
      {error && <div role="alert" className="mt-3 rounded-lg border border-red-200 bg-red-50 p-2 text-sm text-red-700">{error}</div>}
    </Card>
  );
}

export function LoginPage() {
  const { login, notice } = useAuth();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="mx-auto max-w-xl px-4 py-12">
      <h1 className="mb-1 text-2xl font-bold text-azul">Âncora Azul — CRM de alto valor</h1>
      <p className="mb-6 text-sm text-slate-500">Acesso restrito por perfil (analista, gestor ou auditor) · <strong>dados sintéticos</strong></p>
      <DemoLogin />
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
