import asyncio
from .ai_strategy import AIStrategy
import csv
from datetime import datetime

class TradingBot:
    def __init__(self, strategy: AIStrategy):
        self.strategy = strategy
        self.portfolio = {}
        self.initial_balance = 1000  # Starting with 1000 USD
        self.balance = self.initial_balance
        self.trades = []

    def get_last_price(self, symbol):
        token_data = self.strategy.tokens_data.get(symbol)
        if token_data:
            virtual_sol_reserves = float(token_data.get('virtual_sol_reserves', 0))
            virtual_token_reserves = float(token_data.get('virtual_token_reserves', 0))
            if virtual_token_reserves > 0:
                return virtual_sol_reserves / virtual_token_reserves
        return None

    async def execute_trade(self):
        try:
            symbol = await self.strategy.select_token()
            if not symbol:
                return {"status": "info", "message": "No suitable token found for trading"}
            
            action, amount = await self.strategy.generate_trade_signal(symbol)
            last_price = self.get_last_price(symbol)
            
            if last_price is None:
                return {"status": "error", "message": f"Unable to determine price for {symbol}"}
            
            if action == 'buy':
                cost = min(amount, self.balance)
                tokens_bought = cost / last_price
                self.balance -= cost
                self.update_portfolio(symbol, tokens_bought, 'buy')
                self.log_trade(symbol, 'buy', tokens_bought, cost)
                return {"status": "success", "message": f"Bought {tokens_bought:.6f} {symbol} for ${cost:.2f}"}
            elif action == 'sell':
                if symbol in self.portfolio:
                    sell_amount = min(amount, self.portfolio[symbol])
                    revenue = sell_amount * last_price
                    self.balance += revenue
                    self.update_portfolio(symbol, sell_amount, 'sell')
                    self.log_trade(symbol, 'sell', sell_amount, revenue)
                    return {"status": "success", "message": f"Sold {sell_amount:.6f} {symbol} for ${revenue:.2f}"}
                else:
                    return {"status": "info", "message": f"No {symbol} in portfolio to sell"}
            else:
                return {"status": "info", "message": "No trade executed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_portfolio(self, symbol, amount, action):
        if symbol not in self.portfolio:
            self.portfolio[symbol] = 0
        if action == 'buy':
            self.portfolio[symbol] += amount
        elif action == 'sell':
            self.portfolio[symbol] = max(0, self.portfolio[symbol] - amount)

    def get_portfolio(self):
        return {symbol: {"amount": amount, "value": amount * self.get_last_price(symbol) if self.get_last_price(symbol) else 0} 
                for symbol, amount in self.portfolio.items()}

    def get_total_value(self):
        return self.balance + sum(self.portfolio[symbol] * self.get_last_price(symbol)
                                  for symbol in self.portfolio if self.get_last_price(symbol))

    def get_profit_loss(self):
        current_value = self.get_total_value()
        return current_value - self.initial_balance, (current_value / self.initial_balance - 1) * 100

    async def get_market_insights(self):
        insights = await self.strategy.generate_market_insights()
        pl_amount, pl_percentage = self.get_profit_loss()
        insights += f"\nBot Performance:\n"
        insights += f"Initial Balance: ${self.initial_balance:.2f}\n"
        insights += f"Current Total Value: ${self.get_total_value():.2f}\n"
        insights += f"Profit/Loss: ${pl_amount:.2f} ({pl_percentage:.2f}%)\n"
        return insights

    def log_trade(self, symbol, action, amount, price):
        self.trades.append({
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'action': action,
            'amount': amount,
            'price': price
        })
        self.save_trades_to_csv()

    def save_trades_to_csv(self):
        with open('trades.csv', 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'symbol', 'action', 'amount', 'price']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for trade in self.trades:
                writer.writerow(trade)

    def save_market_data(self):
        with open('market_data1.csv', 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'created_timestamp', 'symbol', 'name', 'symbol_address', 'image_url',
                          'username', 'signature', 'creator', 'creator_username', 'timestamp', 'reply_count', 'price', 'market_cap', 'usd_market_cap']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for symbol, data in self.strategy.tokens_data.items():
                price = self.get_last_price(symbol)
                # writer.writerow(data)

                writer.writerow({
                    'timestamp': datetime.now().isoformat(),
                    'created_timestamp': data.get('created_timestamp', 'N/A'),
                    'symbol': symbol,
                    'name': data.get('name', 'N/A'),
                    'symbol_address': data.get('symbol', 'N/A'),
                    'image_url': data.get('image_url', 'N/A'),
                    'username': data.get('username', 'N/A'), 'signature': data.get('signature', 'N/A'),
                    'creator': data.get('creator', 'N/A'),
                    'creator_username': data.get('creator_username', 'N/A'),
                    'timestamp': data.get('timestamp', 'N/A'),
                    'reply_count': data.get('reply_count', 'N/A'),
                    'price': price if price else 'N/A',
                    'market_cap': data.get('market_cap', 'N/A'),
                    'usd_market_cap': data.get('usd_market_cap', 'N/A')
                })

    def start(self):
        self.strategy.start_websocket()