import type { ApexOptions } from "apexcharts";
import ReactApexChart from "react-apexcharts";

interface Props {
  type: "bar" | "donut" | "scatter";
  series: ApexOptions["series"];
  options?: ApexOptions;
  height?: number;
}

export function Chart({ type, series, options = {}, height = 300 }: Props) {
  return (
    <ReactApexChart
      type={type}
      series={series}
      height={height}
      options={{ ...options, chart: { toolbar: { show: false }, fontFamily: "inherit", ...options.chart } }}
    />
  );
}
