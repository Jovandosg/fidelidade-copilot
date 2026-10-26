import { useState } from "react";
import { useAuth } from "./auth";
import { CustomerPage } from "./pages/CustomerPage";
import { ExecutivePage } from "./pages/ExecutivePage";
import { HealthPage } from "./pages/HealthPage";
import { LoginPage } from "./pages/LoginPage";
import { NbaPage } from "./pages/NbaPage";
import { RiskQueuePage } from "./pages/RiskQueuePage";
import { RoutesPage } from "./pages/RoutesPage";
import { ValueRiskPage } from "./pages/ValueRiskPage";

const TABS = [
  { id: "executivo", label: "Executivo" },
  { id: "proteger", label: "Proteger (Radar)" },
  { id: "crescer", label: "Crescer (NBA)" },
  { id: "rotas", label: "Rotas (IVR)" },
  { id: "cliente", label: "Perfil do Cliente" },
  { id: "saude", label: "Saúde da plataforma" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const { principal, logout } = useAuth();
  const [tab, setTab] = useState<TabId>("executivo");
  const [customerId, setCustomerId] = useState<string>();
  const openCustomer = (id: string) => { setCustomerId(id); setTab("cliente"); };

  if (!principal) return <LoginPage />;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <header className="mb-6">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-2xl font-bold text-azul">Âncora Azul — CRM de alto valor</h1>
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <span>{principal.sub} · <strong>{principal.role}</strong></span>
            <button onClick={() => logout()} className="rounded-full px-3 py-1 text-xs ring-1 ring-slate-300 hover:bg-slate-100">Sair</button>
          </div>
        </div>
        <p className="text-sm text-slate-500">Identificar → Proteger → Crescer → Surpreender · <strong>dados sintéticos</strong>, sem informações pessoais</p>
        <nav className="mt-4 flex flex-wrap gap-2" aria-label="Seções">
          {TABS.map((t) => (
            <button
              key={t.id}
              aria-current={tab === t.id ? "page" : undefined}
              onClick={() => setTab(t.id)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium ${tab === t.id ? "bg-azul text-white" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100"}`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === "executivo" && <ExecutivePage />}
        {tab === "proteger" && (
          <div className="space-y-6">
            <ValueRiskPage onSelect={openCustomer} />
            <RiskQueuePage onSelect={openCustomer} />
          </div>
        )}
        {tab === "crescer" && <NbaPage onSelect={openCustomer} />}
        {tab === "rotas" && <RoutesPage />}
        {tab === "cliente" && <CustomerPage customerId={customerId} onSelect={openCustomer} />}
        {tab === "saude" && <HealthPage />}
      </main>
    </div>
  );
}
