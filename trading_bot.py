#!/usr/bin/env python3
"""
trading_bot.py

Usage examples:
    python trading_bot.py --api-key YOURKEY --api-secret YOURSECRET --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --testnet --test
    (Use --test to use the test-order endpoint so no real trade executes.)

Install:
    pip install requests
"""

import os
import sys
import time
import hmac
import hashlib
import argparse
import logging
import urllib.parse
from typing import Dict, Tuple, Optional

import requests

# ---------------------------
# Logging config
# ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("trading_bot")

# ---------------------------
# Binance Client
# ---------------------------
class BinanceClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str,
        recv_window: int = 5000,
        timeout: int = 10,
        debug: bool = False,
    ):
        self.api_key = (api_key or "").strip()
        self.api_secret = (api_secret or "").strip()
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret must be provided (env or CLI).")
        self.base = base_url.rstrip("/")
        self.recv_window = int(recv_window)
        self.timeout = timeout
        self.debug = bool(debug)

        # Compute server time offset (serverTime - localTime)
        self.time_offset_ms = 0
        try:
            r = requests.get(self.base + "/fapi/v1/time", timeout=5)
            r.raise_for_status()
            srv = r.json().get("serverTime")
            if srv:
                self.time_offset_ms = int(srv) - int(time.time() * 1000)
                if abs(self.time_offset_ms) > 5000:
                    logger.warning(
                        "Local clock differs from Binance server by %d ms. Using offset.",
                        self.time_offset_ms,
                    )
            else:
                logger.info("Could not determine serverTime from Binance response.")
        except Exception as e:
            logger.warning("Failed to fetch server time: %s", e)
            self.time_offset_ms = 0

        logger.info("Client initialized (base=%s) recvWindow=%d debug=%s", self.base, self.recv_window, self.debug)

    def _now_ms(self) -> int:
        return int(time.time() * 1000) + int(self.time_offset_ms)

    def _build_qs_and_signature(self, params: Dict) -> Tuple[str, str]:
        """
        Build deterministic query string and compute HMAC-SHA256 signature.
        Returns (query_string, signature_hex).
        """
        # remove None values and convert bools to lowercase 'true'/'false'
        cleaned = {}
        for k, v in (params or {}).items():
            if v is None:
                continue
            if isinstance(v, bool):
                cleaned[k] = "true" if v else "false"
            else:
                cleaned[k] = str(v)

        # Sort lexicographically by key for deterministic order
        ordered_items = sorted(cleaned.items(), key=lambda x: x[0])

        # urllib.parse.urlencode produces predictable encoding; safe='~' matches common Binance expectation
        qs = urllib.parse.urlencode(ordered_items, doseq=False, safe="~")
        signature = hmac.new(self.api_secret.encode("utf-8"), qs.encode("utf-8"), hashlib.sha256).hexdigest()

        if self.debug:
            logger.debug("Unsigned QS: %s", qs)
            logger.debug("Signature: %s", signature)

        return qs, signature

    def _request(self, method: str, path: str, params: Optional[Dict] = None, signed: bool = False):
        """
        Generic request wrapper. For signed requests we append timestamp & recvWindow,
        build signature over the final query string, and send full URL with query and signature.
        """
        method = method.upper()
        params = dict(params or {})

        headers = {"X-MBX-APIKEY": self.api_key}
        url = self.base + path

        if signed:
            params.setdefault("timestamp", self._now_ms())
            params.setdefault("recvWindow", self.recv_window)
            qs, signature = self._build_qs_and_signature(params)
            url = url + "?" + qs + "&signature=" + signature
            if self.debug:
                logger.debug("Final signed URL: %s", url)
            resp = requests.request(method, url, headers=headers, timeout=self.timeout)
        else:
            # unsigned: let requests build the query string
            resp = requests.request(method, url, params=params, headers=headers, timeout=self.timeout)

        # Always reveal response body on error to ease debugging (but don't print secrets)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Log response text (no api secret) for debugging
            logger.error("HTTP error: %s", e)
            try:
                logger.error("Response [%d]: %s", resp.status_code, resp.text)
            except Exception:
                logger.exception("Failed to read response text")
            raise

        # Return parsed JSON when possible
        ct = resp.headers.get("Content-Type", "")
        if "application/json" in ct:
            return resp.json()
        return resp.text

    # Convenience wrappers
    def get_account_info(self):
        return self._request("GET", "/fapi/v2/account", signed=True)

    def get_balances(self):
        # futures: balance endpoint is /fapi/v2/balance
        return self._request("GET", "/fapi/v2/balance", signed=True)

    def place_order(
        self,
        symbol: str,
        side: str,
        type_: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        time_in_force: Optional[str] = None,
        reduce_only: Optional[bool] = None,
        close_position: Optional[bool] = None,
        test: bool = False,
        extra: Optional[Dict] = None,
    ):
        """
        Place a futures order. If test=True, uses the test endpoint which validates the request
        but does not create an order.
        """
        path = "/fapi/v1/order"
        if test:
            path = "/fapi/v1/order/test"

        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": type_.upper(),
        }
        if quantity is not None:
            # Binance expects string decimal formatting
            params["quantity"] = format(float(quantity), "f")
        if price is not None:
            params["price"] = format(float(price), "f")
        if time_in_force:
            params["timeInForce"] = time_in_force
        if reduce_only is not None:
            params["reduceOnly"] = reduce_only
        if close_position is not None:
            params["closePosition"] = close_position
        if extra:
            params.update(extra)

        return self._request("POST", path, params=params, signed=True)


# ---------------------------
# CLI / Main
# ---------------------------
def build_parser():
    p = argparse.ArgumentParser(description="Simple Binance Futures trading bot example (fixed signature).")
    p.add_argument("--api-key", help="Binance API key (or set BINANCE_API_KEY env var).")
    p.add_argument("--api-secret", help="Binance API secret (or set BINANCE_API_SECRET env var).")
    p.add_argument("--symbol", required=True, help="Symbol e.g. BTCUSDT")
    p.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="BUY or SELL")
    p.add_argument("--type", dest="order_type", required=True, choices=["MARKET", "LIMIT", "limit", "market"], help="Order type")
    p.add_argument("--quantity", type=float, help="Order quantity (decimal)")
    p.add_argument("--price", type=float, help="Price (required for LIMIT)")
    p.add_argument("--time-in-force", dest="time_in_force", choices=["GTC", "IOC", "FOK"], help="Time in force for LIMIT orders")
    p.add_argument("--testnet", action="store_true", help="Use futures testnet URL")
    p.add_argument("--test", action="store_true", help="Use order test endpoint (validate only)")
    p.add_argument("--debug", action="store_true", help="Enable debug logging")
    p.add_argument("--recv-window", type=int, default=5000, help="recvWindow parameter (ms)")
    return p

def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    api_key = args.api_key or os.environ.get("BINANCE_API_KEY")
    api_secret = args.api_secret or os.environ.get("BINANCE_API_SECRET")

    # Base URL selection
    if args.testnet:
        # Binance futures testnet base (futures testnet)
        base_url = os.environ.get("BINANCE_FUTURES_TESTNET_URL", "https://testnet.binancefuture.com")
    else:
        base_url = "https://fapi.binance.com"

    # Basic validation
    if args.order_type.upper() == "LIMIT" and args.price is None:
        logger.error("LIMIT orders require --price")
        sys.exit(1)
    if args.quantity is None and args.order_type.upper() == "MARKET":
        # For MARKET on futures you may place by quantity or quoteOrderQty depending on instrument/settings.
        # We require quantity here.
        logger.error("MARKET orders require --quantity for this script")
        sys.exit(1)

    # Initialize client
    try:
        client = BinanceClient(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url,
            recv_window=args.recv_window,
            debug=args.debug,
        )
    except Exception as e:
        logger.error("Failed creating client: %s", e)
        sys.exit(1)

    # Show balances (informational)
    try:
        balances = client.get_balances()
        # It's usually a list of dicts with asset & balance fields (futures endpoint)
        logger.info("Fetched %d balance entries", len(balances) if isinstance(balances, list) else 0)
        # Show a few useful balances
        shown = 0
        if isinstance(balances, list):
            for entry in balances:
                asset = entry.get("asset")
                bal = entry.get("balance") or entry.get("walletBalance") or entry.get("crossWalletBalance")
                if asset and float(bal or 0) > 0:
                    logger.info("Asset=%s balance=%s", asset, bal)
                    shown += 1
                    if shown >= 10:
                        break
    except Exception as e:
        logger.warning("Failed to fetch balances: %s", e)

    # Place order
    try:
        logger.info(
            "Placing order symbol=%s side=%s type=%s quantity=%s price=%s test=%s",
            args.symbol,
            args.side,
            args.order_type,
            args.quantity,
            args.price,
            args.test,
        )
        resp = client.place_order(
            symbol=args.symbol.upper(),
            side=args.side.upper(),
            type_=args.order_type.upper(),
            quantity=args.quantity,
            price=args.price,
            time_in_force=args.time_in_force,
            test=args.test,
        )
        logger.info("Order response: %s", resp)
    except Exception as e:
        logger.error("Order placement failed: %s", e)
        # If detailed error response is present, python-requests exception handling printed it above
        sys.exit(1)


if __name__ == "__main__":
    main()
