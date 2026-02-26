#!/bin/bash
# ZeroClaw Ollama Telegram Poller Demo - 改進版 (timeout + offset持久)
# 用法: 改 BOT_TOKEN / CHAT_ID, chmod +x demo-poller.sh && nohup ./demo-poller.sh &

BOT_TOKEN="YOUR_BOT_TOKEN_HERE"  # BotFather 建 bot 取
CHAT_ID="YOUR_CHAT_ID_HERE"     # Telegram 用戶 ID (userinfobot 查)
OFFSET_FILE="/tmp/tg_offset"    # offset 持久檔

# 初設 offset
if [ ! -f "$OFFSET_FILE" ]; then
  echo 0 > "$OFFSET_FILE"
fi
OFFSET=$(cat "$OFFSET_FILE")

echo "🚀 Poller 啟動 (sleep 10s, Ctrl+C 停)"

while true; do
  # curl getUpdates (timeout=10s 長輪詢，省 CPU)
  response=$(curl -s --max-time 15 "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=${OFFSET}&timeout=10" 2>/dev/null)
  
  if [ $? -ne 0 ] || [ -z "$response" ]; then
    sleep 10
    continue
  fi
  
  # jq 解析 (需 jq 安裝)
  echo "$response" | jq -r '.result[]? | select(.message.chat.id == '"${CHAT_ID}"') | "\(.update_id)|\(.message.text // "no text")"' 2>/dev/null | \
  while IFS='|' read -r update_id text; do
    if [[ "$text" =~ ^/run ]]; then
      echo "📨 收到: $text"
      ollama_out=$(ollama run qwen2.5:7b "${text#/run }" 2>/dev/null | head -c 4000)  # 限長防洪
      curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d chat_id="${CHAT_ID}" \
        -d text="🤖 Ollama: ${ollama_out}" \
        -d parse_mode=Markdown >/dev/null
    fi
    OFFSET=$((update_id + 1))
    echo $OFFSET > "$OFFSET_FILE"
  done
  
  sleep 5  # 防 flood
done