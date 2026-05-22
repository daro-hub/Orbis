"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  IChartApi,
  CandlestickSeries,
  createSeriesMarkers,
  CandlestickData,
  Time,
} from "lightweight-charts";

interface ChartProps {
  data: Array<{
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
  }>;
  markers?: Array<{
    time: number;
    position: "aboveBar" | "belowBar";
    color: string;
    shape: "arrowUp" | "arrowDown" | "circle";
    text: string;
  }>;
  equityCurve?: number[];
  height?: number;
}

export default function Chart({ data, markers, equityCurve, height = 450 }: ChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || !data.length) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: "#1e2235" },
        textColor: "#8b8fa3",
      },
      grid: {
        vertLines: { color: "#2a2e42" },
        horzLines: { color: "#2a2e42" },
      },
      width: chartContainerRef.current.clientWidth,
      height: height,
      timeScale: { timeVisible: true, secondsVisible: false },
      crosshair: {
        mode: 0,
      },
    });

    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderDownColor: "#ef4444",
      borderUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      wickUpColor: "#22c55e",
    });

    const chartData: CandlestickData<Time>[] = data.map((d) => ({
      time: d.time as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    candleSeries.setData(chartData);

    if (markers && markers.length > 0) {
      const sortedMarkers = [...markers].sort((a, b) => a.time - b.time);
      createSeriesMarkers(
        candleSeries,
        sortedMarkers.map((m) => ({
          time: m.time as Time,
          position: m.position,
          color: m.color,
          shape: m.shape,
          text: m.text,
        }))
      );
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data, markers, height]);

  return <div ref={chartContainerRef} style={{ width: "100%", height }} />;
}
