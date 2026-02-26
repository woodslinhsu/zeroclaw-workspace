#!/usr/bin/env python3
"""
股市分析器 v3 - ZeroClaw × Ollama × Telegram
- 自動偵測 Windows IP（解決 IP 漂移）
"""

import requests
import re
import subprocess
from datetime import datetime

# ── 設定 ──────────────────────────────────────────
TELEGRAM_TOKEN = "8724707186:AAHSiDGb1vQ5u_UKA--xxP_L8yMs6D4XEyc"
TELEGRAM_CHAT_ID = "443284363"
OLLAMA_MODEL = "GemmaPro:latest"
OLLAMA_PORT = 11434


TW_STOCKS = {
    "2330": "台積電",
    "2317": "鴻海",
    "2454": "聯發科",
    "2308": "台達電",
}
US_STOCKS = ["NVDA", "AAPL", "MSFT", "GOOGL"]

# ── 自動偵測 Windows IP ───────────────────────────
def get_windows_ip() -> str:
    """嘗試多個已知 IP，回傳第一個可連到 Ollama 的"""
    candidates = ["172.18.112.1"]
    # 從 resolv.conf 補充
    try:
        result = subprocess.run(["cat", "/etc/resolv.conf"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.startswith("nameserver"):
                ip = line.split()[1]
                if ip not in candidates:
                    candidates.append(ip)
    except Exception:
        pass

    for ip in candidates:
        try:
            r = requests.get(f"http://{ip}:11434/api/tags", timeout=3)
            if r.status_code == 200:
                print(f"✅ Ollama 在線：{ip}")
                return ip
        except Exception:
            pass

    print(f"⚠️ 所有 IP 均無法連到 Ollama，使用預設 {candidates[0]}")
    return candidates[0]

# ── 讀取 OpenRouter API Key ───────────────────────
def get_openrouter_key() -> str:
    try:
        with open("/home/woodslinhsu/.zeroclaw/config.toml") as f:
            content = f.read()
        match = re.search(r'api_key\s*=\s*"(sk-or-[^"]+)"', content)
        if match:
            return match.group(1)
    except Exception:
        pass
    return ""

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
            break
        except Exception:
            if parse_mode is None:
                raise
    print("✅ Telegram 已發送")

# ── 台股：TWSE 官方 API ───────────────────────────
def fetch_tw_prices() -> str:
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data = r.json()
        stock_map = {item["Code"]: item for item in data}
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
        return "\n".join(results)
    except Exception as e:
        return f"台股查詢失敗：{e}"

def fetch_taiex() -> str:
    try:
        url = "https://openapi.twse.com.tw/v1/indicesReport/MI_5MINS_HIST"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data:
            latest = data[-1]
            return f"加權指數：{latest.get('TAIEX', 'N/A')}"
    except Exception:
        pass
    return ""

# ── 美股：Yahoo Finance ───────────────────────────
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
            arrow = "▲" if change >= 0 else "▼"
            results.append(f"{ticker}: ${price:.2f} {arrow}{abs(change):.2f} ({pct:+.2f}%)")
        except Exception as e:
            results.append(f"{ticker}: 查詢失敗({e})")
    return "\n".join(results)

# ── 財經新聞 ──────────────────────────────────────
def fetch_news() -> str:
    news_items = []
    try:
        r = requests.get("https://news.cnyes.com/news/cat/tw_stock_news", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        titles = re.findall(r'"title":"([^"]{5,80})"', r.text)
        for t in titles[:4]:
            news_items.append(f"[台股] {t}")
    except Exception:
        pass
    try:
        r = requests.get("https://finance.yahoo.com/rss/headline", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", r.text)
        if not titles:
            titles = re.findall(r"<title>(.*?)</title>", r.text)
        for t in titles[1:4]:
            news_items.append(f"[美股] {t.strip()}")
    except Exception:
        pass
    return "\n".join(news_items) if news_items else "新聞抓取失敗"

# ── 分析：Ollama（主）→ Grok（備）────────────────
PROMPT_TEMPLATE = """你是專業財經分析師，請用繁體中文，簡潔條列格式整理以下資訊，不超過250字。

【大盤】{taiex}
【台股個股】
{tw}
【美股個股】
{us}
【今日新聞】
{news}

輸出格式：
1. 今日重點（2行）
2. 台股觀察（1-2行）
3. 美股觀察（1行）
4. 注意（1行）
"""

def analyze_with_ollama(prompt: str, windows_ip: str) -> str:
    ollama_url = f"http://{windows_ip}:{OLLAMA_PORT}"
    print(f"🤖 嘗試 Ollama ({ollama_url})...")
    try:
        r = requests.post(f"{ollama_url}/api/generate", json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": -1}
        }, timeout=60)
        r.raise_for_status()
        result = r.json().get("response", "").strip()
        if result:
            print("✅ Ollama 分析成功")
            return result, "Ollama"
    except Exception as e:
        print(f"⚠️ Ollama 失敗：{e}")
    return None, None

#
def analyze(tw: str, us: str, news: str, taiex: str, windows_ip: str):
    prompt = PROMPT_TEMPLATE.format(tw=tw, us=us, news=news, taiex=taiex)
    result, engine = analyze_with_ollama(prompt, windows_ip)
    if not result:
        result, engine = "Ollama 分析失敗", "失敗"
    return result, engine

# ── 主流程 ────────────────────────────────────────
def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"🪭 股市分析器 v3 啟動 {now}")

    windows_ip = get_windows_ip()

    print("📈 抓取台股（TWSE 官方）...")
    tw = fetch_tw_prices()
    taiex = fetch_taiex()

    print("📊 抓取美股...")
    us = fetch_us_prices()

    print("📰 抓取財經新聞...")
    news = fetch_news()

    print("🧠 分析中...")
    analysis, engine = analyze(tw, us, news, taiex, windows_ip)

    msg = f"""🪭 *諸葛亮財經日報* `{now}`

*📈 台股* {taiex}
{tw}

*📊 美股*
{us}

*🤖 亮之分析* _（{engine}）_
{analysis}
"""

    print("📨 發送 Telegram...")
    send_telegram(msg)
    print("✅ 完成")

if __name__ == "__main__":
    main()
