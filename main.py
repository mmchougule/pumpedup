import asyncio
from bot.trading_bot import TradingBot
from bot.ai_strategy import AIStrategy

async def main():
    strategy = AIStrategy()
    bot = TradingBot(strategy)
    
    print("getting pumpedup...")
    print("talking to pump.fun...")
    
    bot.start()

    # Give some time for the websocket to connect and receive initial data
    await asyncio.sleep(10)

    async def periodic_trade():
        while True:
            try:
                result = await bot.execute_trade()
                print(result)
            except Exception as e:
                print(f"Error executing trade: {e}")
            await asyncio.sleep(60)  # Wait for 60 seconds before the next trade attempt

    async def periodic_insights():
        while True:
            try:
                insights = await bot.get_market_insights()
                print("\nMarket Insights and Bot Performance:")
                print(insights)
                print("\nCurrent Portfolio:")
                portfolio = bot.get_portfolio()
                for symbol, data in portfolio.items():
                    print(f"{symbol}: Amount: {data['amount']:.6f}, Value: ${data['value']:.2f}")
                bot.save_market_data()
            except Exception as e:
                print(f"Error generating insights: {e}")
            await asyncio.sleep(300)  # Generate insights every 5 minutes

    trade_task = asyncio.create_task(periodic_trade())
    insights_task = asyncio.create_task(periodic_insights())

    try:
        await asyncio.gather(trade_task, insights_task)
    except asyncio.CancelledError:
        print("Bot operation cancelled.")
    finally:
        strategy.stop_websocket()

if __name__ == "__main__":
    asyncio.run(main())