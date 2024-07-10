import asyncio
import json
import websockets
from datetime import datetime

# from prompt.CryptoSageBotTrader.app import send_new_coin
import requests

# modifying the class to include the new methods
class AIStrategy:
    def __init__(self):
        self.ws_url = "wss://frontend-api.pump.fun/socket.io/?EIO=4&transport=websocket"
        self.tokens_data = {}
        self.trades = []
        self.new_coins = []
        self.websocket_task = None

    async def connect_websocket(self):
        while True:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    await websocket.send("40")
                    while True:
                        try:
                            message = await websocket.recv()
                            if message.startswith("42"):
                                data = json.loads(message[2:])
                                event_type = data[0]
                                event_data = data[1]

                                if event_type == "newCoinCreated":
                                    self.process_new_coin(event_data)
                                elif event_type == "tradeCreated":
                                    self.process_trade(event_data)
                                else:
                                    print(f"Received unknown event: {event_type}")
                        except websockets.exceptions.ConnectionClosed:
                            print("WebSocket connection closed. Reconnecting...")
                            break
            except Exception as e:
                print(f"Error in WebSocket connection: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)

    def process_new_coin(self, coin_data):
        self.new_coins.append(coin_data)
        self.tokens_data[coin_data['mint']] = coin_data
        print(f"New coin created: {coin_data['name']} ({coin_data['symbol']}), Mint: https://pump.fun/{coin_data['mint']}")
        requests.post(f"http://0.0.0.0:5000/new_coin", json=coin_data)

    def process_trade(self, trade_data):
        self.trades.append(trade_data)
        if trade_data['mint'] in self.tokens_data:
            self.tokens_data[trade_data['mint']].update({
                'last_trade_timestamp': trade_data['timestamp'],
                'market_cap': trade_data['market_cap'],
                'usd_market_cap': trade_data['usd_market_cap']
            })
        # print(f"Trade: {'Buy' if trade_data['is_buy'] else 'Sell'} {trade_data['token_amount']} {trade_data['symbol']} for {trade_data['sol_amount'] / 1e9:.6f} SOL, Address {trade_data['mint']}")
        requests.post(f"http://0.0.0.0:5000/trade", json=trade_data)

    async def select_token(self):
        if not self.tokens_data:
            return None
        
        # Strategy: Select the newest token with the highest USD market cap
        best_token = max(self.tokens_data.values(), key=lambda x: (x.get('created_timestamp', 0), x.get('usd_market_cap', 0)))
        return best_token['mint']

    async def generate_trade_signal(self, symbol):
        if symbol not in self.tokens_data:
            return 'hold', 0

        token_data = self.tokens_data[symbol]
        usd_market_cap = float(token_data.get('usd_market_cap', 0))
        created_timestamp = token_data.get('created_timestamp', 0)
        current_time = datetime.now().timestamp() * 1000  # Convert to milliseconds

        # Strategy: Buy if the token is new (less than 5 minutes old) and has a low market cap
        if (current_time - created_timestamp) < 300000 and usd_market_cap < 10000:
            return 'buy', min(100, usd_market_cap * 0.01)  # Buy up to $100 worth or 1% of market cap, whichever is less
        # Sell if the market cap has increased significantly (e.g., 5x) since creation
        elif usd_market_cap > 50000 and usd_market_cap > (token_data.get('initial_usd_market_cap', 0) * 5):
            return 'sell', token_data.get('token_amount', 0) * 0.5  # Sell 50% of holdings
        else:
            return 'hold', 0

    async def generate_market_insights(self):
        if not self.tokens_data:
            return "No market data available yet."

        total_tokens = len(self.tokens_data)
        total_usd_market_cap = sum(float(token.get('usd_market_cap', 0)) for token in self.tokens_data.values())
        avg_usd_market_cap = total_usd_market_cap / total_tokens if total_tokens > 0 else 0

        insights = f"Market Insights:\n"
        insights += f"Total number of tokens: {total_tokens}\n"
        insights += f"Total USD market cap: ${total_usd_market_cap:.2f}\n"
        insights += f"Average USD market cap: ${avg_usd_market_cap:.2f}\n"

        if self.new_coins:
            newest_coin = max(self.new_coins, key=lambda x: x['created_timestamp'])
            insights += f"Newest coin: {newest_coin['name']} ({newest_coin['symbol']}) - Created at {datetime.fromtimestamp(newest_coin['created_timestamp']/1000)}\n"

        if self.trades:
            latest_trade = max(self.trades, key=lambda x: x['timestamp'])
            insights += f"Latest trade: {'Buy' if latest_trade['is_buy'] else 'Sell'} {latest_trade['token_amount']} {latest_trade['symbol']} for {latest_trade['sol_amount'] / 1e9:.6f} SOL\n"

        return insights

    def start_websocket(self):
        if self.websocket_task is None or self.websocket_task.done():
            self.websocket_task = asyncio.create_task(self.connect_websocket())

    def stop_websocket(self):
        if self.websocket_task:
            self.websocket_task.cancel()
            self.websocket_task = None