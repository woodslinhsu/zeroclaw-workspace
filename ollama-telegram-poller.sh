#!/bin/bash
BOT_TOKEN="your_bot_token"
CHAT_ID="your_chat_id"
OFFSET=0
while true; do
  curl -s "https://api.telegram.org/bot$BOT_TOKEN/getUpdates?offset=$OFFSET" | jq -r '.result[] | select(.message) | .update_id + "|" + .message.text' | while IFS='|' read -r update_id text; do
    if [[ "$text" == "/run"* ]]; then
      ollama run qwen2.5:7b "$text" | tee output.txt
      curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" -d chat_id="$CHAT_ID" -d text="$(cat output.txt)"
    fi
    OFFSET=$((update_id + 1))
  done
  sleep 10
done