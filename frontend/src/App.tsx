import { useState } from "react";
import { CustomerPage } from "./pages/CustomerPage";
import { ExecutivePage } from "./pages/ExecutivePage";
import { NbaPage } from "./pages/NbaPage";
import { RiskQueuePage } from "./pages/RiskQueuePage";
import { ValueRiskPage } from "./pages/ValueRiskPage";

const TABS = [
  { id: "executiva", label: "Visão Executiva" },
  { id: "mapa", label: "Mapa Valor × Risco" },
  { id: "fila", label: "Fila de Risco" },
  { id: "cliente", label: "Perfil do Cliente" },
  { id: "nba", label: "Próxima Melhor Ação" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>("executiva");
  const [customerId, setCustomerId] = useState<string>();
  const openCustomer = (id: string) => { setCustomerId(id); setTab("cliente"); };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-azul">Âncora Azul — CRM de alto valor</h1>
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
        {tab === "executiva" && <ExecutivePage />}
        {tab === "mapa" && <ValueRiskPage onSelect={openCustomer} />}
        {tab === "fila" && <RiskQueuePage onSelect={openCustomer} />}
        {tab === "cliente" && <CustomerPage customerId={customerId} onSelect={openCustomer} />}
        {tab === "nba" && <NbaPage onSelect={openCustomer} />}
      </main>
    </div>
  );
}
