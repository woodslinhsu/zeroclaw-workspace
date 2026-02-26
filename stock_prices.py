#!/usr/bin/env python3
"""
股價報告 - 台股 14:00 / 美股 23:00
TWSE 官方 API + Yahoo Finance
"""

import requests
import subprocess
import re
import sys
from datetime import datetime

# ── 設定 ──────────────────────────────────────────
TELEGRAM_TOKEN = "8724707186:AAHSiDGb1vQ5u_UKA--xxP_L8yMs6D4XEyc"
TELEGRAM_CHAT_ID = "443284363"

TW_STOCKS = {
    "2330": "台積電",
    "2317": "鴻海",
    "2454": "聯發科",
    "2308": "台達電",
}
US_STOCKS = ["NVDA", "AAPL", "MSFT", "GOOGL"]

# ── Telegram ──────────────────────────────────────
def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for parse_mode in ["Markdown", None]:
        try:
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": True}
            if parse_mode:
                payload["parse_mode"] = parse_mode
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            print("✅ Telegram 已發送")
            return
        except Exception:
            if parse_mode is None:
                raise

# ── 台股 ──────────────────────────────────────────
def fetch_tw_prices() -> tuple[str, str]:
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data = r.json()
        stock_map = {item["Code"]: item for item in data}

        taiex = ""
        try:
            idx = requests.get("https://openapi.twse.com.tw/v1/indicesReport/MI_5MINS_HIST", timeout=10)
            idx_data = idx.json()
            if idx_data:
                taiex = f"加權指數：{idx_data[-1].get('TAIEX', 'N/A')}"
        except Exception:
            pass

        results = []
        for code, name in TW_STOCKS.items():
            if code in stock_map:
                s = stock_map[code]
                close = float(s.get("ClosingPrice", 0))
                change = float(s.get("Change", 0))
                arrow = "▲" if change >= 0 else "▼"
                prev = close - change
                pct = (change / prev * 100) if prev != 0 else 0
                vol = int(s.get("TradeVolume", 0)) // 1000
                results.append(f"{name}({code}): {close} {arrow}{abs(change):.1f} ({pct:+.2f}%) 量{vol}張")
            else:
                results.append(f"{name}({code}): 查詢失敗")
        return "\n".join(results), taiex
    except Exception as e:
        return f"台股查詢失敗：{e}", ""

# ── 美股 ──────────────────────────────────────────
def fetch_us_prices() -> str:
    import yfinance as yf
    results = []
    for ticker in US_STOCKS:
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            price = float(hist["Close"].iloc[-1])
            prev  = float(hist["Close"].iloc[-2])
            change = price - prev
            pct = (change / prev * 100) if prev else 0
            arrow = "\u25b2" if change >= 0 else "\u25bc"
            results.append(f"{ticker}: ${price:.2f} {arrow}{abs(change):.2f} ({pct:+.2f}%)")
        except Exception as e:
            results.append(f"{ticker}: 查詢失敗({e})")
    return "\n".join(results)

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"🪭 股價報告啟動 [{mode}] {now}")

    if mode in ("tw", "both"):
        print("📈 抓取台股...")
        tw, taiex = fetch_tw_prices()
        msg = f"🪭 *台股收盤報告* `{now}`\n\n{taiex}\n{tw}"
        send_telegram(msg)

    if mode in ("us", "both"):
        print("📊 抓取美股...")
        us = fetch_us_prices()
        msg = f"🪭 *美股收盤報告* `{now}`\n\n{us}"
        send_telegram(msg)

if __name__ == "__main__":
    main()
