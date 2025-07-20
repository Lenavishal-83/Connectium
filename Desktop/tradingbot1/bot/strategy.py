import pandas as pd
import numpy as np

def generate_signals(df, pair, price_precisions, latest_only=True, debug=False, trade_state=None):
    signals = pd.DataFrame(columns=['datetime', 'pair', 'action', 'price', 'tp1_price', 'tp2_price', 'reason', 'condition_count'])
    if df.empty or df['close'].isna().all():
        return signals

    df['ema_50_slope'] = df['ema_50'].diff().shift(-1)
    last_idx = df.index[-1]
    is_bullish_ema = df['ema_50_slope'].iloc[-1] > 0 if not pd.isna(df['ema_50_slope'].iloc[-1]) else False

    rsi = df['rsi'].iloc[-1]
    macd = df['MACD'].iloc[-1]
    macd_signal = df['MACD_Signal'].iloc[-1]
    bb_upper = df['bb_upper'].iloc[-1]
    bb_lower = df['bb_lower'].iloc[-1]
    stoch_k = df['stoch_k'].iloc[-1]
    stoch_d = df['stoch_d'].iloc[-1]

    buy_conditions = [
        rsi < 50,
        macd > macd_signal,
        is_bullish_ema,
        df['close'].iloc[-1] < bb_upper,
        stoch_k < 80
    ]

    sell_conditions = [
        rsi > 50,
        macd < macd_signal,
        not is_bullish_ema,
        df['close'].iloc[-1] > bb_lower,
        stoch_k > 20
    ]

    buy_count = sum(cond for cond in buy_conditions)
    sell_count = sum(cond for cond in sell_conditions)
    price = df['close'].iloc[-1]
    datetime_val = last_idx

    if buy_count >= 3:
        if trade_state['last_action'] != 'buy' or (trade_state['last_action'] == 'buy' and buy_count > trade_state['last_condition']):
            risk = 'Quite Strong' if buy_count == 3 else 'Intermediate' if buy_count == 4 else 'Strong'
            met_conditions = [i for i, cond in enumerate(buy_conditions, 1) if cond]
            reason = f"Buy: {buy_count}/5 conditions met (Risk: {risk}, Met: {', '.join([f'Cond {i}' for i in met_conditions])})"
            signal = pd.DataFrame({
                'datetime': [datetime_val],
                'pair': [pair],
                'action': ['buy'],
                'price': [price],
                'tp1_price': [price * 1.05],
                'tp2_price': [price * 1.075],
                'reason': [reason],
                'condition_count': [buy_count]
            })
            signals = pd.concat([signals, signal], ignore_index=True)

    elif sell_count >= 3 and trade_state['last_action'] == 'buy':  # Allow sell after buy
        risk = 'Quite Strong' if sell_count == 3 else 'Intermediate' if sell_count == 4 else 'Strong'
        met_conditions = [i for i, cond in enumerate(sell_conditions, 1) if cond]
        reason = f"Sell: {sell_count}/5 conditions met (Risk: {risk}, Met: {', '.join([f'Cond {i}' for i in met_conditions])})"
        signal = pd.DataFrame({
            'datetime': [datetime_val],
            'pair': [pair],
            'action': ['sell'],
            'price': [price],
            'tp1_price': [price * 0.95],
            'tp2_price': [price * 0.925],
            'reason': [reason],
            'condition_count': [sell_count]
        })
        signals = pd.concat([signals, signal], ignore_index=True)

    if debug and signals.empty:
        print(f"⚠️ No signals generated for {pair}. Check data or conditions.")
        print(f"🔍 Last candle data for {pair}:")
        print(df[['close', 'rsi', 'ema_50', 'MACD', 'MACD_Signal', 'bb_upper', 'bb_lower', 'stoch_k', 'stoch_d']].tail())

    return signals