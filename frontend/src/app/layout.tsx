import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Orbis — Algorithmic Trading Platform",
  description:
    "Backtest and trade BTC, NASDAQ 100, and Gold with pluggable strategies, real risk management, and an automated bot.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
