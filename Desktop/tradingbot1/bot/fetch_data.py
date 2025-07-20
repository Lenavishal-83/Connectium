import pandas as pd
import requests
import websocket
import json
import time
from datetime import datetime
from bot.indicators import add_indicators
from bot.strategy import generate_signals
from pytz import timezone  # For timezone handling

preloaded_dfs = {}
trade_states = {}  # Track buy/sell state and highest condition per pair
last_debug_print = {}  # Track last debug print per pair

def fetch_historical_data(pair, interval='1m', limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignored'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')  # Convert to IST
        df.set_index('timestamp', inplace=True)
        df['close'] = df['close'].astype(float)
        return df
    except requests.RequestException as e:
        print(f"Error fetching data for {pair}: {e}")
        return pd.DataFrame()

def on_message(ws, message, pairs, interval, save_csv, debug, price_precisions):
    global preloaded_dfs, trade_states, last_debug_print
    try:
        data = json.loads(message)
        if data.get('e') == 'kline' and 'k' in data and data['k'].get('x', False):
            kline = data['k']
            pair = kline.get('s')
            if pair and pair in pairs:
                if pair not in trade_states:
                    trade_states[pair] = {'last_action': None, 'highest_condition': 0}
                if pair not in preloaded_dfs or preloaded_dfs[pair].empty:
                    preloaded_dfs[pair] = fetch_historical_data(pair, interval, 100)
                    preloaded_dfs[pair]['pair'] = pair
                df = preloaded_dfs[pair].copy()
                new_candle = pd.DataFrame({
                    'timestamp': [pd.to_datetime(kline['t'], unit='ms', utc=True).tz_convert('Asia/Kolkata')],  # Convert to IST
                    'open': [float(kline['o'])],
                    'high': [float(kline['h'])],
                    'low': [float(kline['l'])],
                    'close': [float(kline['c'])],
                    'volume': [float(kline['v'])]
                })
                new_candle.set_index('timestamp', inplace=True)
                df = pd.concat([df, new_candle]).sort_index().tail(100)
                df = add_indicators(df)
                if len(df) < 50:  # Ensure enough data for EMA_50
                    preloaded_dfs[pair] = fetch_historical_data(pair, interval, 100)
                    df = preloaded_dfs[pair].copy()
                    df = pd.concat([df, new_candle]).sort_index().tail(100)
                    df = add_indicators(df)
                current_time = datetime.now(timezone('Asia/Kolkata'))  # Current time in IST
                delay = (current_time - new_candle.index[0]).total_seconds()
                print(f"🔍 Delay for {pair}: {delay} seconds")  # Debug delay
                if delay > 600:  # Relax to 10 minutes
                    print(f"⚠️ Significant delay for {pair}, syncing with latest data...")
                    preloaded_dfs[pair] = fetch_historical_data(pair, interval, 100)
                    df = preloaded_dfs[pair].copy()
                    df = pd.concat([df, new_candle]).sort_index().tail(100)
                    df = add_indicators(df)
                    if delay > 1200:  # Force reconnect if >20min delay
                        print(f"🔄 Forcing WebSocket reconnect for {pair} due to excessive delay...")
                        time.sleep(5)  # Add delay before reconnect
                        ws.close()
                        return
                signals = generate_signals(df, pair, price_precisions, latest_only=True, debug=debug, trade_state=trade_states[pair])
                if not signals.empty:
                    for _, signal in signals.iterrows():
                        if signal['action'] == 'buy':
                            if (trade_states[pair]['last_action'] is None or trade_states[pair]['last_action'] == 'sell') and signal['condition_count'] >= trade_states[pair]['highest_condition']:
                                print(f"🕒 Time   : {signal['datetime']}")
                                print(f"🔹 Pair   : {signal['pair']}")
                                print(f"🔹 Action : {signal['action'].upper()}")
                                print(f"🔹 Price  : ${signal['price']:.{price_precisions[pair]}f}")
                                print(f"🔹 TP1    : ${signal['tp1_price']:.{price_precisions[pair]}f}")
                                print(f"🔹 TP2    : ${signal['tp2_price']:.{price_precisions[pair]}f}")
                                print(f"🔹 Stop-Loss : ${signal['price'] * 0.95:.{price_precisions[pair]}f}")
                                print(f"🔹 Reason : {signal['reason']}\n")
                                trade_states[pair] = {'last_action': 'buy', 'highest_condition': signal['condition_count']}
                            elif trade_states[pair]['last_action'] == 'buy' and signal['condition_count'] > trade_states[pair]['highest_condition']:
                                print(f"🕒 Time   : {signal['datetime']}")
                                print(f"🔹 Pair   : {signal['pair']}")
                                print(f"🔹 Action : {signal['action'].upper()}")
                                print(f"🔹 Price  : ${signal['price']:.{price_precisions[pair]}f}")
                                print(f"🔹 TP1    : ${signal['tp1_price']:.{price_precisions[pair]}f}")
                                print(f"🔹 TP2    : ${signal['tp2_price']:.{price_precisions[pair]}f}")
                                print(f"🔹 Stop-Loss : ${signal['price'] * 0.95:.{price_precisions[pair]}f}")
                                print(f"🔹 Reason : {signal['reason']}\n")
                                trade_states[pair]['highest_condition'] = signal['condition_count']
                        else:
                            if trade_states[pair]['last_action'] == 'buy':
                                print(f"🕒 Time   : {signal['datetime']}")
                                print(f"🔹 Pair   : {signal['pair']}")
                                print(f"🔹 Action : {signal['action'].upper()}")
                                print(f"🔹 Price  : ${signal['price']:.{price_precisions[pair]}f}")
                                print(f"🔹 TP1    : ${signal['tp1_price']:.{price_precisions[pair]}f}")
                                print(f"🔹 TP2    : ${signal['tp2_price']:.{price_precisions[pair]}f}")
                                print(f"🔹 Stop-Loss : ${signal['price'] * 1.05:.{price_precisions[pair]}f}")
                                print(f"🔹 Reason : {signal['reason']}\n")
                                trade_states[pair] = {'last_action': 'sell', 'highest_condition': 0}
                    if save_csv:
                        signals.to_csv(f"data/signals_{pair}.csv", mode='a', header=not pd.io.common.file_exists(f"data/signals_{pair}.csv"), index=False)
                        print(f"💾 Signals saved to data/signals_{pair}.csv")
                elif debug and (pair not in last_debug_print or last_debug_print[pair] != df.index[-1]):
                    print(f"⚠️ No signals generated for {pair}. Check data or conditions.")
                    print(f"🔍 Last candle data for {pair}:")
                    print(df[['close', 'rsi', 'ema_50', 'MACD', 'MACD_Signal', 'bb_upper', 'bb_lower', 'stoch_k', 'stoch_d']].tail())
                    last_debug_print[pair] = df.index[-1]
    except Exception as e:
        pair_str = pair if 'pair' in locals() else 'undefined'
        print(f"Error processing message for {pairs}: {e} - Pair: {pair_str} - Raw message: {message}")

def on_error(ws, error):
    print(f"WebSocket error: {error}")
    time.sleep(10)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed, reconnecting...")
    time.sleep(10)
    start_websocket(ws.pairs, ws.interval, ws.save_csv, ws.debug, ws.price_precisions)

def on_open(ws):
    print("WebSocket connected")
    ws.send(json.dumps({"method": "SUBSCRIBE", "params": [f"{pair.lower()}@kline_1m" for pair in ws.pairs], "id": 1}))

def start_websocket(pairs, interval, save_csv, debug, price_precisions):
    ws_endpoint = "wss://stream.binance.com:9443/ws"
    streams = "/".join([f"{pair.lower()}@kline_{interval}" for pair in pairs])
    ws_url = f"{ws_endpoint}/{streams}"
    def on_message_wrapper(ws, message):
        on_message(ws, message, pairs, interval, save_csv, debug, price_precisions)
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message_wrapper,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    ws.pairs = pairs
    ws.interval = interval
    ws.save_csv = save_csv
    ws.debug = debug
    ws.price_precisions = price_precisions
    ws.run_forever()