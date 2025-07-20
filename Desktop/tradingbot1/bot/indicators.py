import pandas as pd
import numpy as np

def add_indicators(df):
    if len(df) < 50:  # Minimum for EMA_50
        return df
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['rsi'] = compute_rsi(df['close'])
    df['MACD'], df['MACD_Signal'] = compute_macd(df['close'])
    df['bb_upper'], df['bb_lower'] = compute_bollinger_bands(df['close'])
    df['stoch_k'], df['stoch_d'] = compute_stochastic(df['high'], df['low'], df['close'])
    return df

def compute_rsi(close, period=14):
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.finfo(float).eps)  # Avoid division by zero
    return 100 - (100 / (1 + rs))

def compute_macd(close, fast=12, slow=26, signal=9):
    exp1 = close.ewm(span=fast, adjust=False).mean()
    exp2 = close.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal

def compute_bollinger_bands(close, period=20, std_dev=2):
    rolling_mean = close.rolling(window=period).mean()
    rolling_std = close.rolling(window=period).std()
    upper = rolling_mean + (rolling_std * std_dev)
    lower = rolling_mean - (rolling_std * std_dev)
    return upper, lower

def compute_stochastic(high, low, close, period=14, smooth_k=3, smooth_d=3):
    low_min = low.rolling(window=period).min()
    high_max = high.rolling(window=period).max()
    k = 100 * (close - low_min) / (high_max - low_min).replace(0, np.finfo(float).eps)
    d = k.rolling(window=smooth_d).mean()
    return k.rolling(window=smooth_k).mean(), d