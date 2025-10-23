1) Create and activate virtualenv (recommended)
   python3 -m venv venv
   source venv/bin/activate

2) Install dependencies
   pip install -r requirements.txt

3) Run (testnet example)
   python trading_bot.py \
     --api-key YOUR_TESTNET_KEY \
     --api-secret YOUR_TESTNET_SECRET \
     --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --testnet

Notes:
- This script uses the futures testnet base URL: https://testnet.binancefuture.com. Use the --testnet flag for testnet. :contentReference[oaicite:1]{index=1}
- It fetches balances from GET /fapi/v2/balance (signed). :contentReference[oaicite:2]{index=2}
- It submits new orders to POST /fapi/v1/order. :contentReference[oaicite:3]{index=3}
- Keep your keys secret. Do NOT paste your real production keys into logs or public places.
- Test on testnet first. If you want production, remove the --testnet flag and ensure your API key has FUTURES permissions.
