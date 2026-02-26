#!/usr/bin/env python3
"""
財經新聞分析 - 08:00 早報 / 12:00 午報
中英文新聞 + Ollama（備用 Grok）分析
"""

import requests
import subprocess
import re
from datetime import datetime

# ── 設定 ──────────────────────────────────────────
TELEGRAM_TOKEN = "8724707186:AAHSiDGb1vQ5u_UKA--xxP_L8yMs6D4XEyc"
TELEGRAM_CHAT_ID = "443284363"
OLLAMA_MODEL = "GemmaPro:latest"
OLLAMA_PORT = 11434

# ── 偵測 Windows IP ───────────────────────────────
def get_ollama_ip() -> str:
    candidates = ["172.18.112.1", "10.255.255.254"]
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
            r = requests.get(f"http://{ip}:{OLLAMA_PORT}/api/tags", timeout=3)
            if r.status_code == 200:
                print(f"✅ Ollama 在線：{ip}")
                return ip
        except Exception:
            pass
    return candidates[0]

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

# ── 抓中文新聞（鉅亨網）──────────────────────────
def fetch_zh_news() -> list[str]:
    items = []
    urls = [
        ("台股", "https://news.google.com/rss/search?q=台股&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
        ("美股", "https://news.google.com/rss/search?q=美股+財經&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
        ("總經", "https://news.google.com/rss/search?q=聯準會+通膨+經濟&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
    ]
    for label, url in urls:
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            titles = re.findall(r"<title>(.*?)</title>", r.text)
            for t in titles[1:4]:
                t = re.sub(r"<[^>]+>", "", t).strip()
                if t and "Google 新聞" not in t and len(t) > 10:
                    items.append(f"[{label}] {t}")
        except Exception:
            pass
    return items

# ── 抓英文新聞（Yahoo Finance RSS）───────────────
def fetch_en_news() -> list[str]:
    items = []
    try:
        r = requests.get(
            "https://finance.yahoo.com/rss/headline",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", r.text)
        if not titles:
            titles = re.findall(r"<title>(.*?)</title>", r.text)
        for t in titles[1:5]:
            items.append(f"[EN] {t.strip()}")
    except Exception:
        pass
    return items

# ── Ollama 分析 ───────────────────────────────────
def analyze_ollama(news_text: str, ip: str, session: str) -> tuple[str, str]:
    prompt = f"""你是資深財經分析師，請用繁體中文分析以下{session}財經新聞，條列格式，不超過300字。

{news_text}

輸出格式：
1. 今日重點（2-3行）
2. 台股影響（1-2行）
3. 美股影響（1行）
4. 操作建議（1行）
"""
    try:
        r = requests.post(
            f"http://{ip}:{OLLAMA_PORT}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.3, "num_predict": -1}},
            timeout=300
        )
        r.raise_for_status()
        result = r.json().get("response", "").strip()
        if result:
            return result, "Ollama"
    except Exception as e:
        print(f"⚠️ Ollama 失敗：{e}")
    return None, None


# ── 主流程 ────────────────────────────────────────
def main():
    hour = datetime.now().hour
    session = "午報" if hour >= 10 else "早報"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"🪭 財經新聞分析啟動 [{session}] {now}")

    # 抓新聞
    print("📰 抓取中文新聞...")
    zh = fetch_zh_news()
    print("📰 抓取英文新聞...")
    en = fetch_en_news()

    all_news = zh + en
    if not all_news:
        send_telegram(f"🪭 *財經{session}* `{now}`\n\n新聞抓取失敗")
        return

    news_text = "\n".join(all_news)

    # 新聞清單
    news_list = "\n".join(f"• {n}" for n in all_news)

    # 分析
    ip = get_ollama_ip()
    analysis, engine = analyze_ollama(news_text, ip, session)
    if not analysis:
        analysis, engine = "Ollama 分析失敗", "失敗"

    msg = f"""🪭 *財經{session}* `{now}`

*📰 今日新聞*
{news_list}

*🤖 亮之分析* _（{engine}）_
{analysis}
"""
    send_telegram(msg)
    print("✅ 完成")

if __name__ == "__main__":
    main()
