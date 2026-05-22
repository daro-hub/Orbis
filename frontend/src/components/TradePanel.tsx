"use client";

import { useState } from "react";
import { placeOrder, closePosition } from "@/lib/api";

interface TradePanelProps {
  symbol: string;
  currentPrice?: number;
}

export default function TradePanel({ symbol, currentPrice }: TradePanelProps) {
  const [quantity, setQuantity] = useState("0.01");
  const [orderType, setOrderType] = useState("market");
  const [limitPrice, setLimitPrice] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleOrder = async (side: string) => {
    setLoading(true);
    setMessage("");
    try {
      const params: any = {
        symbol,
        side,
        quantity: parseFloat(quantity),
        order_type: orderType,
      };
      if (orderType === "limit" && limitPrice) {
        params.price = parseFloat(limitPrice);
      }
      const result = await placeOrder(params);
      setMessage(`Order ${result.status || "placed"}: ${side} ${quantity} ${symbol}`);
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
    }
    setLoading(false);
  };

  const handleClose = async () => {
    setLoading(true);
    try {
      await closePosition(symbol);
      setMessage(`Position closed for ${symbol}`);
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
    }
    setLoading(false);
  };

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <h3 style={{ marginBottom: 12, fontSize: 14 }}>
        Trade {symbol}
        {currentPrice && (
          <span style={{ marginLeft: 12, color: "var(--accent)" }}>
            ${currentPrice.toLocaleString()}
          </span>
        )}
      </h3>

      <div style={{ display: "flex", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
        <div>
          <label>Quantity</label>
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            step="0.01"
            min="0.001"
            style={{ width: 100 }}
          />
        </div>
        <div>
          <label>Type</label>
          <select value={orderType} onChange={(e) => setOrderType(e.target.value)}>
            <option value="market">Market</option>
            <option value="limit">Limit</option>
          </select>
        </div>
        {orderType === "limit" && (
          <div>
            <label>Price</label>
            <input
              type="number"
              value={limitPrice}
              onChange={(e) => setLimitPrice(e.target.value)}
              style={{ width: 120 }}
            />
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          className="btn btn-buy"
          onClick={() => handleOrder("buy")}
          disabled={loading}
        >
          BUY
        </button>
        <button
          className="btn btn-sell"
          onClick={() => handleOrder("sell")}
          disabled={loading}
        >
          SELL
        </button>
        <button
          className="btn"
          style={{ background: "var(--border)", color: "var(--text-primary)" }}
          onClick={handleClose}
          disabled={loading}
        >
          Close Position
        </button>
      </div>

      {message && (
        <p style={{ marginTop: 8, fontSize: 12, color: "var(--text-secondary)" }}>
          {message}
        </p>
      )}
    </div>
  );
}
