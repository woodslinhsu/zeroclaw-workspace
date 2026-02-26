# 系統狀態（唯一真相）
- stock_prices.py：正常，14檔台股，無語法錯誤
- news_analysis.py：正常，GemmaPro:latest，無語法錯誤
- stock_analyzer.py：正常，GemmaPro:latest，無語法錯誤
- Ollama：172.18.112.1:11434，GemmaPro:latest
- cron：4個 python3 直接執行，無 agent -m

# 主公自選股
台股：2330台積電、2382廣達、2317鴻海、3231緯創、2603長榮、2454聯發科、2327國巨、6669緯穎、00878、00713、0050、006802、00631L、00685L
美股：NVDA、AAPL、MSFT、GOOGL

# 捷徑
/stock → python3 stock_prices.py tw
/stockus → python3 stock_prices.py us
/stocknews → python3 news_analysis.py
/token → token-monitor binary

# 禁止事項
- 禁止診斷語法錯誤（已確認全部正常）
- 禁止編造股價
- 禁止推薦 sed 修復指令
