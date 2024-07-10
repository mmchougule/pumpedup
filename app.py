from flask import Flask, render_template_string, request, jsonify
import pandas as pd
from flask_socketio import SocketIO
import json
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

app = Flask(__name__)
socketio = SocketIO(app)

new_coins = {}
trades = {}

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>pumpedup trader</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <style>
            body {
                font-family: 'Orbitron', sans-serif;
                background-color: #0a0a0a;
                color: #00ffff;
                margin: 0;
                padding: 20px;
                background-image: 
                    radial-gradient(circle at 10% 20%, rgba(0, 255, 255, 0.05) 0%, transparent 20%),
                    radial-gradient(circle at 90% 80%, rgba(0, 255, 255, 0.05) 0%, transparent 20%);
                background-attachment: fixed;
            }
            h1 {
                text-align: center;
                text-shadow: 0 0 10px #00ffff;
                font-size: 2.5em;
            }
            #coinGrid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
            }
            .coin {
                background-color: rgba(10, 10, 10, 0.8);
                border: 1px solid #00ffff;
                border-radius: 10px;
                padding: 15px;
                box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
                transition: all 0.3s ease;
            }
            .coin:hover {
                transform: scale(1.02);
                box-shadow: 0 0 30px rgba(0, 255, 255, 0.5);
            }
            .new {
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(0, 255, 255, 0.7); }
                70% { box-shadow: 0 0 0 10px rgba(0, 255, 255, 0); }
                100% { box-shadow: 0 0 0 0 rgba(0, 255, 255, 0); }
            }
            .coin-header {
                display: flex;
                align-items: center;
                margin-bottom: 10px;
            }
            .coin-image {
                width: 50px;
                height: 50px;
                border-radius: 25px;
                margin-right: 10px;
            }
            .coin-name {
                font-size: 1.2em;
                font-weight: bold;
            }
            .coin-symbol {
                font-size: 0.9em;
                color: #00ffaa;
            }
            .coin-info {
                font-size: 0.9em;
                margin-bottom: 10px;
            }
            .market-cap {
                font-size: 1.1em;
                font-weight: bold;
            }
            .market-cap-change {
                font-weight: bold;
                font-size: 0.9em;
            }
            .positive-change { color: #00ff00; }
            .negative-change { color: #ff0000; }
            .trades {
                max-height: 150px;
                overflow-y: auto;
                margin-top: 10px;
            }
            .trade {
                background-color: rgba(0, 255, 255, 0.1);
                border-radius: 5px;
                padding: 5px;
                margin-bottom: 5px;
                font-size: 0.8em;
                transition: all 0.3s ease;
            }
            .trade-new {
                animation: tradePulse 1s;
            }
            @keyframes tradePulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); background-color: rgba(0, 255, 255, 0.2); }
                100% { transform: scale(1); }
            }
            .links {
                display: flex;
                justify-content: space-around;
                margin-top: 10px;
            }
            .links a {
                color: #00ffaa;
                text-decoration: none;
                font-size: 0.9em;
            }
            .links a:hover {
                text-decoration: underline;
            }
            ::-webkit-scrollbar {
                width: 5px;
            }
            ::-webkit-scrollbar-track {
                background: #0a0a0a; 
            }
            ::-webkit-scrollbar-thumb {
                background: #00ffff; 
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #00ffaa; 
            }
            .stats-button {
                position: fixed;
                top: 20px;
                right: 20px;
                background-color: #00ffff;
                color: #0a0a0a;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-family: 'Orbitron', sans-serif;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            .stats-button:hover {
                background-color: #00ffaa;
            }

        </style>
    </head>
    <body>
        <h1>pumpedup trader dash</h1>
        <button class="stats-button" onclick="window.location.href='/stats'">View Stats</button>
        <div id="coinGrid"></div>

        <script>
            const socket = io();
            const coinGrid = document.getElementById('coinGrid');
            const coins = {};

            function updateMarketCap(coinElement, newMarketCap) {
                const marketCapElement = coinElement.querySelector('.market-cap');
                const oldMarketCap = parseFloat(marketCapElement.dataset.value);
                const change = newMarketCap - oldMarketCap;
                const changePercent = (change / oldMarketCap) * 100;

                marketCapElement.textContent = `$${newMarketCap.toFixed(2)}`;
                marketCapElement.dataset.value = newMarketCap;

                const changeElement = coinElement.querySelector('.market-cap-change');
                changeElement.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)} (${changePercent.toFixed(2)}%)`;
                changeElement.className = `market-cap-change ${change >= 0 ? 'positive-change' : 'negative-change'}`;
            }

            socket.on('new_coin', (coin) => {
                const div = document.createElement('div');
                div.className = 'coin new';
                div.id = `coin-${coin.mint}`;
                div.innerHTML = `
                    <div class="coin-header">
                        <img class="coin-image" src="${coin.image_uri}" alt="${coin.name} logo">
                        <div>
                            <div class="coin-name">${coin.name}</div>
                            <div class="coin-symbol">${coin.symbol}<a href="https://pump.fun/profile/${coin.creator}" target="_blank" style="color: inherit; text-decoration: none;">check creator</a></div>
                        </div>
                    </div>
                    <div class="coin-info">
                        <p>Created: ${new Date(coin.created_timestamp).toLocaleString()}</p>
                        <p>Market Cap: <span class="market-cap" data-value="${coin.usd_market_cap}">$${parseFloat(coin.usd_market_cap).toFixed(2)}</span></p>
                        <p>Change: <span class="market-cap-change">0.00 (0.00%)</span></p>
                    </div>
                    <div class="trades"></div>
                    <div class="links">
                        <a href="https://solscan.io/token/${coin.mint}" target="_blank">Solscan</a>
                        <a href="https://pump.fun/${coin.mint}" target="_blank">pump.fun</a>
                    </div>
                `;
                coinGrid.prepend(div);
                coins[coin.mint] = coin;
            });

            socket.on('trade', (trade) => {
                const coinElement = document.getElementById(`coin-${trade.mint}`);
                if (coinElement) {
                    const tradeDiv = document.createElement('div');
                    tradeDiv.className = 'trade trade-new';
                    tradeDiv.innerHTML = `
                        <p>${trade.is_buy ? '🟢 Buy' : '🔴 Sell'}: ${trade.symbol} for ${trade.sol_amount / 1e9} SOL, <a href="https://pump.fun/profile/${trade.creator}" target="_blank" style="color: inherit; text-decoration: none;">check trader</a>
                        <p>Price: $${parseFloat(trade.usd_market_cap / (trade.virtual_token_reserves / 1e9)).toFixed(6)}</p>
                    `;
                    const tradesContainer = coinElement.querySelector('.trades');
                    tradesContainer.prepend(tradeDiv);
                    setTimeout(() => tradeDiv.classList.remove('trade-new'), 1000);

                    updateMarketCap(coinElement, parseFloat(trade.usd_market_cap));
                }
            });
        </script>
    </body>
    </html>
    ''')


@app.route('/stats')
def stats():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>pumped stats</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {
                font-family: 'Orbitron', sans-serif;
                background-color: #0a0a0a;
                color: #00ffff;
                margin: 0;
                padding: 20px;
                background-image: 
                    radial-gradient(circle at 10% 20%, rgba(0, 255, 255, 0.05) 0%, transparent 20%),
                    radial-gradient(circle at 90% 80%, rgba(0, 255, 255, 0.05) 0%, transparent 20%);
                background-attachment: fixed;
            }
            h1 {
                text-align: center;
                text-shadow: 0 0 10px #00ffff;
            }
            .chart-container {
                background-color: rgba(10, 10, 10, 0.8);
                border: 1px solid #00ffff;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
            }
            .back-button {
                display: block;
                width: 100px;
                margin: 20px auto;
                background-color: #00ffff;
                color: #0a0a0a;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-family: 'Orbitron', sans-serif;
                font-weight: bold;
                text-align: center;
                text-decoration: none;
                transition: all 0.3s ease;
            }
            .back-button:hover {
                background-color: #00ffaa;
            }
        </style>
    </head>
    <body>
        <h1>pumped stats</h1>
        <div id="totalMarketCap" class="chart-container"></div>
        <div id="topCoins" class="chart-container"></div>
        <div id="tradeVolume" class="chart-container"></div>
        <a href="/" class="back-button">Back</a>

        <script>
            function createOrUpdateChart(elementId, data) {
                var element = document.getElementById(elementId);
                if (element && data) {
                    Plotly.react(elementId, data.data, data.layout);
                }
            }

            function fetchAndUpdateCharts() {
                fetch('/api/stats')
                    .then(response => response.json())
                    .then(data => {console.log(data.trade_volume_chart)
                        createOrUpdateChart('totalMarketCap', JSON.parse(data.total_market_cap_chart));
                        createOrUpdateChart('topCoins', JSON.parse(data.top_coins_chart));
                        createOrUpdateChart('tradeVolume', JSON.parse(data.trade_volume_chart));
                    })
                    .catch(error => console.error('Error fetching stats:', error));
            }

            fetchAndUpdateCharts();
            setInterval(fetchAndUpdateCharts, 60000); // Update every minute
        </script>
    </body>
    </html>
    ''')

# @app.route('/statsd')
# def stats():
#     return render_template_string('''
#     <!DOCTYPE html>
#     <html lang="en">
#     <head>
#         <meta charset="UTF-8">
#         <meta name="viewport" content="width=device-width, initial-scale=1.0">
#         <title>CryptoSageBotTrader Stats</title>
#         <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
#         <style>
#             body {
#                 font-family: 'Orbitron', sans-serif;
#                 background-color: #0a0a0a;
#                 color: #00ffff;
#                 margin: 0;
#                 padding: 20px;
#                 background-image: 
#                     radial-gradient(circle at 10% 20%, rgba(0, 255, 255, 0.05) 0%, transparent 20%),
#                     radial-gradient(circle at 90% 80%, rgba(0, 255, 255, 0.05) 0%, transparent 20%);
#                 background-attachment: fixed;
#             }
#             h1 {
#                 text-align: center;
#                 text-shadow: 0 0 10px #00ffff;
#             }
#             .chart-container {
#                 background-color: rgba(10, 10, 10, 0.8);
#                 border: 1px solid #00ffff;
#                 border-radius: 10px;
#                 padding: 20px;
#                 margin-bottom: 20px;
#                 box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
#             }
#             .back-button {
#                 display: block;
#                 width: 100px;
#                 margin: 20px auto;
#                 background-color: #00ffff;
#                 color: #0a0a0a;
#                 border: none;
#                 padding: 10px 20px;
#                 border-radius: 5px;
#                 cursor: pointer;
#                 font-family: 'Orbitron', sans-serif;
#                 font-weight: bold;
#                 text-align: center;
#                 text-decoration: none;
#                 transition: all 0.3s ease;
#             }
#             .back-button:hover {
#                 background-color: #00ffaa;
#             }
#         </style>
#     </head>
#     <body>
#         <h1>CryptoSageBotTrader Stats</h1>
#         <div id="totalMarketCap" class="chart-container"></div>
#         <div id="topCoins" class="chart-container"></div>
#         <div id="tradeVolume" class="chart-container"></div>
#         <a href="/" class="back-button">Back</a>

#         <script>
#             function fetchAndUpdateCharts() {
#                 fetch('/api/stats')
#                     .then(response => response.json())
#                     .then(data => {console.log(data.total_market_cap_chart)
#                     Plotly.newPlot('totalMarketCap', data.total_market_cap_chart.data, data.total_market_cap_chart.layout);
#                     Plotly.newPlot('topCoins', data.top_coins_chart.data, data.top_coins_chart.layout);
#                     Plotly.newPlot('tradeVolume', data.trade_volume_chart.data, data.trade_volume_chart.layout);
#                     });
#             }

#             fetchAndUpdateCharts();
#             setInterval(fetchAndUpdateCharts, 60000); // Update every minute
#         </script>
#     </body>
#     </html>
#     ''')
# '{"data":[{"x":["DXhMnyzif8YHgAQveAgYyc7uKhEyrPeCkjTE3vk3EkyM","3vRLjDsT7LDYooUG986Qca77tvqgmBPCtxpoPLwkpump","5nUkN6FRAJCMEP2vveeUKKN6UxGjt9fGWb2jMaDvpump","9MWLQk4xRN7LuBEYK1A9HKe5XBpTBBnNQXbiykVbpump","HBqfeFCcmp7qUASSQXzLXzuGDTJhh3bpGgFuAom83vFo"],"y":[42028.55863557151,8732.85413758132,7602.51659405688,7200.99813614652,6316.0904028018795],"type":"bar"}],"layout":{"title":{"text":"Top 5 Coins by Market Cap"},"xaxis":{"title":{"text":"Symbol"}},"yaxis":{"title":{"text":"USD"}},"template":{"data":{"histogram2dcontour":[{"type":"histogram2dcontour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"choropleth":[{"type":"choropleth","colorbar":{"outlinewidth":0,"ticks":""}}],"histogram2d":[{"type":"histogram2d","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"heatmap":[{"type":"heatmap","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"heatmapgl":[{"type":"heatmapgl","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"contourcarpet":[{"type":"contourcarpet","colorbar":{"outlinewidth":0,"ticks":""}}],"contour":[{"type":"contour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"surface":[{"type":"surface","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"mesh3d":[{"type":"mesh3d","colorbar":{"outlinewidth":0,"ticks":""}}],"scatter":[{"fillpattern":{"fillmode":"overlay","size":10,"solidity":0.2},"type":"scatter"}],"parcoords":[{"type":"parcoords","line":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolargl":[{"type":"scatterpolargl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"bar":[{"error_x":{"color":"#2a3f5f"},"error_y":{"color":"#2a3f5f"},"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"bar"}],"scattergeo":[{"type":"scattergeo","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolar":[{"type":"scatterpolar","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"histogram":[{"marker":{"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"histogram"}],"scattergl":[{"type":"scattergl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatter3d":[{"type":"scatter3d","line":{"colorbar":{"outlinewidth":0,"ticks":""}},"marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermapbox":[{"type":"scattermapbox","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterternary":[{"type":"scatterternary","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattercarpet":[{"type":"scattercarpet","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"carpet":[{"aaxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"baxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"type":"carpet"}],"table":[{"cells":{"fill":{"color":"#EBF0F8"},"line":{"color":"white"}},"header":{"fill":{"color":"#C8D4E3"},"line":{"color":"white"}},"type":"table"}],"barpolar":[{"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"barpolar"}],"pie":[{"automargin":true,"type":"pie"}]},"layout":{"autotypenumbers":"strict","colorway":["#636efa","#EF553B","#00cc96","#ab63fa","#FFA15A","#19d3f3","#FF6692","#B6E880","#FF97FF","#FECB52"],"font":{"color":"#2a3f5f"},"hovermode":"closest","hoverlabel":{"align":"left"},"paper_bgcolor":"white","plot_bgcolor":"#E5ECF6","polar":{"bgcolor":"#E5ECF6","angularaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"radialaxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"ternary":{"bgcolor":"#E5ECF6","aaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"baxis":{"gridcolor":"white","linecolor":"white","ticks":""},"caxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"coloraxis":{"colorbar":{"outlinewidth":0,"ticks":""}},"colorscale":{"sequential":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"sequentialminus":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"diverging":[[0,"#8e0152"],[0.1,"#c51b7d"],[0.2,"#de77ae"],[0.3,"#f1b6da"],[0.4,"#fde0ef"],[0.5,"#f7f7f7"],[0.6,"#e6f5d0"],[0.7,"#b8e186"],[0.8,"#7fbc41"],[0.9,"#4d9221"],[1,"#276419"]]},"xaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"yaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"scene":{"xaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"yaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"zaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2}},"shapedefaults":{"line":{"color":"#2a3f5f"}},"annotationdefaults":{"arrowcolor":"#2a3f5f","arrowhead":0,"arrowwidth":1},"geo":{"bgcolor":"white","landcolor":"#E5ECF6","subunitcolor":"white","showland":true,"showlakes":true,"lakecolor":"white"},"title":{"x":0.05},"mapbox":{"style":"light"}}}}}'
# Plotly.newPlot('totalMarketCap', data.total_market_cap_chart.data);
#                         Plotly.newPlot('topCoins', data.top_coins_chart);
#                         Plotly.newPlot('tradeVolume', data.trade_volume_chart);
import pytz

utc_zone = pytz.timezone('UTC')
local_zone = pytz.timezone('America/New_York')


@app.route('/api/stats')
def api_stats():
    df = pd.read_csv('market_data1.csv')
    if df.empty:
        return jsonify({})
    # df['timestamp'] = pd.to_datetime(df['timestamp'])
    # Convert 'created_timestamp' from Unix timestamp (milliseconds) to datetime
    df['created_timestamp'] = pd.to_datetime(df['created_timestamp'], unit='ms')

    # Get current time in UTC
    now_utc = datetime.now(utc_zone)

    # Calculate 'last_hour' in UTC
    last_hour_utc = now_utc - timedelta(hours=1)

    # Filter data for the last hour
    # last_hour_utc = datetime.now() - timedelta(hours=1)
    last_hour_utc_naive = last_hour_utc.replace(tzinfo=None) #tz_localize(None)

    # Now you can safely compare 'last_hour_utc_naive' with 'df['created_timestamp']'
    df_last_hour = df[df['created_timestamp'] > last_hour_utc_naive]
    # df_last_hour = df[df['timestamp'] > last_hour]
    df['created_timestamp'] = pd.to_datetime(df['created_timestamp'], unit='ms')

    # Convert 'reply_count', 'price', 'market_cap', and 'usd_market_cap' to numeric types
    df['reply_count'] = pd.to_numeric(df['reply_count'], errors='coerce')
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce')
    df['usd_market_cap'] = pd.to_numeric(df['usd_market_cap'], errors='coerce')

    # Total Market Cap Chart
    total_market_cap = df_last_hour.groupby('created_timestamp')['usd_market_cap'].sum().reset_index()
    total_market_cap_chart = {
        'data': [go.Scatter(x=total_market_cap['created_timestamp'], y=total_market_cap['usd_market_cap'], mode='lines')],
        'layout': go.Layout(title='Total Market Cap (Last Hour)', xaxis_title='Time', yaxis_title='USD')
    }

    # Top Coins by Market Cap
    latest_data = df_last_hour.loc[df_last_hour.groupby('symbol')['created_timestamp'].idxmax()]
    top_coins = latest_data.nlargest(5, 'usd_market_cap')
    top_coins_chart = {
        'data': [go.Bar(x=top_coins['symbol_address'], y=top_coins['usd_market_cap'])],
        'layout': go.Layout(title='Top 5 Coins by Market Cap', xaxis_title='Symbol', yaxis_title='USD')
    }

    # Trade Volume (assuming we have this data, if not, we'll need to modify the trading_bot.py to log it)
    # For this example, we'll use a dummy calculation

    # trade_volume = df_last_hour.groupby('symbol')['symbol'].count().reset_index().sort_values('symbol', ascending=False)
    # trade_volume = df_last_hour.groupby('created_timestamp')['timestamp'].count().sort_values("price", ascending=False).reset_index()

    trade_volume = df_last_hour.groupby('created_timestamp')['price'].count().reset_index()
    
    trade_volume_chart = {
        'data': [go.Bar(x=trade_volume['created_timestamp'], y=trade_volume['price'])],
        'layout': go.Layout(title='Trade Volume (Last Hour)', xaxis_title='Time', yaxis_title='Number of Trades')
    }

    print("total_market_cap_chart, top_coins_chart, trade_volume_chart")

    # return jsonify({
    #     'total_market_cap_chart': total_market_cap_chart,
    #     'top_coins_chart': top_coins_chart,
    #     'trade_volume_chart': trade_volume_chart
    # })

    return {
        'total_market_cap_chart': pio.to_json(total_market_cap_chart),
        'top_coins_chart': pio.to_json(top_coins_chart),
        'trade_volume_chart': pio.to_json(trade_volume_chart)
    }


@app.route('/new_coin', methods=['POST'])
def receive_new_coin():
    coin_data = request.json
    send_new_coin(coin_data)
    return '', 204

@app.route('/trade', methods=['POST'])
def receive_trade():
    trade_data = request.json
    send_trade(trade_data)
    return '', 204

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    for coin in new_coins.values():
        socketio.emit('new_coin', coin)
    for trade in trades.values():
        socketio.emit('trade', trade)

def send_new_coin(coin_data):
    new_coins[coin_data['mint']] = coin_data
    socketio.emit('new_coin', coin_data)

def send_trade(trade_data):
    trades[trade_data['signature']] = trade_data
    socketio.emit('trade', trade_data)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5001, debug=True, allow_unsafe_werkzeug=True)