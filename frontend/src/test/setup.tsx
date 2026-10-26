import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// ApexCharts depende de SVG/ResizeObserver reais; nos testes trocamos o grafico por um stub.
vi.mock("react-apexcharts", () => ({
  default: (props: { type?: string; series?: unknown }) => (
    <div data-testid="chart" data-type={props.type} data-series={JSON.stringify(props.series)} />
  ),
}));
