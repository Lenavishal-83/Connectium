import pandas as pd
import time
from bot.fetch_data import fetch_historical_data, start_websocket
from bot.indicators import add_indicators
from bot.strategy import generate_signals

def main(backtest=False, save_csv=False, debug=True):
    pairs = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
    interval = '1m'
    limit = 100
    price_precisions = {'BTCUSDT': 2, 'ETHUSDT': 3, 'ADAUSDT': 4, 'SOLUSDT': 2}

    if backtest:
        for pair in pairs:
            df = fetch_historical_data(pair, interval, limit)
            if df.empty:
                print(f"⚠️ Failed to fetch data for {pair}")
                continue
            df['pair'] = pair
            df = add_indicators(df)
            signals = generate_signals(df, pair, price_precisions, latest_only=False, debug=debug)
            if not signals.empty:
                print(f"\n📊 Backtest Signals for {pair}:")
                for _, signal in signals.iterrows():
                    if signal['action'] == 'buy':
                        print(f"🕒 Time   : {signal['datetime']}")
                        print(f"🔹 Pair   : {signal['pair']}")
                        print(f"🔹 Action : {signal['action'].upper()}")
                        print(f"🔹 Price  : ${signal['price']:.{price_precisions[pair]}f}")
                        print(f"🔹 TP1    : ${signal['tp1_price']:.{price_precisions[pair]}f}")
                        print(f"🔹 TP2    : ${signal['tp2_price']:.{price_precisions[pair]}f}")
                        print(f"🔹 Stop-Loss : ${signal['price'] * 0.95:.{price_precisions[pair]}f}")
                        print(f"🔹 Reason : {signal['reason']}\n")
                    else:
                        print(f"🕒 Time   : {signal['datetime']}")
                        print(f"🔹 Pair   : {signal['pair']}")
                        print(f"🔹 Action : {signal['action'].upper()}")
                        print(f"🔹 Price  : ${signal['price']:.{price_precisions[pair]}f}")
                        print(f"🔹 Reason : {signal['reason']}\n")
                    if save_csv:
                        signals.to_csv(f"data/signals_{pair}.csv", index=False)
                        print(f"💾 Signals saved to data/signals_{pair}.csv")
            else:
                print(f"⚠️ No signals generated for {pair} in backtest.")
    else:
        print("Starting WebSocket for all pairs...")
        for pair in pairs:
            df = fetch_historical_data(pair, interval, limit)
            if not df.empty:
                df['pair'] = pair
                df = add_indicators(df)
                print(f"📈 Preloaded {len(df)} candles for {pair}")
            else:
                print(f"⚠️ Failed to preload data for {pair}")
        start_websocket(pairs, interval, save_csv, debug, price_precisions)

if __name__ == "__main__":
    main(backtest=False, save_csv=True, debug=True)