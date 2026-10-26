const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const num = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

export const fmtBRL = (v: number) => brl.format(v);
export const fmtNum = (v: number) => num.format(v);
export const fmtPct = (part: number, total: number) => (total === 0 ? "0%" : `${num.format((part / total) * 100)}%`);

// risk_drivers vem como texto separado por ";" (ex.: "nivel de fidelidade; atraso medio elevado")
export const splitDrivers = (s: string) => s.split(";").map((d) => d.trim()).filter(Boolean);

export const PROFILE_COLORS: Record<string, string> = {
  A: "#0b3d91",
  B: "#1e6fd9",
  C: "#5aa2f0",
  D: "#f5a524",
  E: "#e5484d",
};
