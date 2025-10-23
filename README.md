# Binance Auto Trading Bot  

A lightweight and fully functional **Python-based trading bot** that interacts with the **Binance API** to fetch market data, place orders, and monitor balances. The bot currently runs via **CLI (Command Line Interface)** and is designed for easy customization and future expansion — such as adding indicators, auto strategies, or a frontend dashboard.

---

## Features  

-  Connects securely to Binance API using your keys  
-  Fetches and displays real-time account balance and symbol prices  
-  Places market buy/sell orders with error handling  
-  Simple CLI for executing commands interactively  
-  Logs all trade actions and responses  
-  Uses `.env` or CLI flags for secure API key management  

---

##  Tech Stack  

- **Language:** Python 3.10+  
- **API:** Binance REST API  
- **Libraries:**  
  - `python-binance`  
  - `requests`  
  - `python-dotenv`  
  - `argparse`  
  - `time`, `os`, `sys`, `logging`  

---

##  Installation  

### 1.Clone the repository  

```bash
git clone https://github.com/Krishnasingh020/trading-bot.git
cd trading-bot
```
## 2.Create a virtual environment 
```bash
python -m venv venv
source venv/bin/activate   # for Linux/Mac
venv\Scripts\activate      # for Windows
```
## 3.Install dependencies
```bash
pip install -r requirements.txt
```
## 4.Configuration 
Pass credentials via CLI
```bash
python trading_bot.py \
  --api-key YOUR_BINANCE_API_KEY \
  --api-secret YOUR_BINANCE_API_SECRET
```

## 5.Future Enhancements

- Add frontend dashboard (React or Flask UI)

- Support for WebSocket live price updates

- Add indicator-based auto strategies (RSI, EMA crossover, etc.)

- Integrate logging dashboard / database for trades

- Deploy to Docker or AWS Lambda

## Disclaimer
This bot is for educational purposes only.
Trading cryptocurrencies carries significant financial risk.
Use this project at your own discretion and always test on Binance Testnet before using real funds.

## Author
Krishna-singh

📧[workforkrishnasingh@gmail.com]



