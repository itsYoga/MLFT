"""
高級技術指標 - 向量化實現
包含 CHOP, Efficiency Ratio, ADX 等市場狀態檢測指標
"""

import numpy as np
import pandas as pd
from phandas import Factor, ts_mean, ts_std_dev, ts_max, ts_min, ts_sum
from typing import Optional


def calculate_atr(high: Factor, low: Factor, close: Factor, period: int = 14) -> Factor:
    """
    計算 ATR（向量化）
    
    參數
    ----------
    high : Factor
        最高價因子
    low : Factor
        最低價因子
    close : Factor
        收盤價因子
    period : int
        計算週期（默認 14）
    
    返回
    -------
    Factor
        ATR 因子
    """
    prev_close = close.data.copy()
    prev_close['factor'] = prev_close.groupby('symbol')['factor'].shift(1)
    
    hl = high.data['factor'] - low.data['factor']
    hc = np.abs(high.data['factor'] - prev_close['factor'])
    lc = np.abs(low.data['factor'] - prev_close['factor'])
    
    tr = pd.DataFrame({
        'timestamp': high.data['timestamp'],
        'symbol': high.data['symbol'],
        'factor': np.maximum(np.maximum(hl, hc), lc)
    })
    
    tr_factor = Factor(tr, "TR")
    atr = ts_mean(tr_factor, period)
    return Factor(atr.data, f"ATR({period})")


def efficiency_ratio(close: Factor, period: int = 10) -> Factor:
    """
    計算 Kaufman's Efficiency Ratio (ER)
    
    ER = |Close_t - Close_{t-n}| / Sum(|Close_i - Close_{i-1}|)
    
    參數
    ----------
    close : Factor
        收盤價因子
    period : int
        計算週期
    
    返回
    -------
    Factor
        Efficiency Ratio 因子 (0-1)
    """
    df = close.data.copy()
    df = df.sort_values(['symbol', 'timestamp']).reset_index(drop=True)
    
    # 計算方向性移動（絕對淨變化）
    change = df.groupby('symbol')['factor'].diff(period).abs()
    
    # 計算波動率（絕對變化的總和）
    volatility = df.groupby('symbol')['factor'].diff(1).abs().groupby('symbol').transform(
        lambda x: x.rolling(window=period, min_periods=1).sum()
    )
    
    # Efficiency Ratio
    er = change / (volatility + 1e-10)  # 避免除零
    er = er.fillna(0).clip(0, 1)  # 限制在 0-1 範圍
    
    result_df = df.copy()
    result_df['factor'] = er
    
    return Factor(result_df, f"ER({period})")


def choppiness_index(high: Factor, low: Factor, close: Factor, period: int = 14) -> Factor:
    """
    計算 Choppiness Index (CHOP)
    
    CHOP = 100 * log10(Sum(ATR) / (MaxHigh - MinLow)) / log10(N)
    
    參數
    ----------
    high : Factor
        最高價因子
    low : Factor
        最低價因子
    close : Factor
        收盤價因子
    period : int
        計算週期
    
    返回
    -------
    Factor
        Choppiness Index 因子 (0-100)
    """
    # 計算 ATR
    atr = calculate_atr(high, low, close, period=1)
    
    # 計算 ATR 總和
    atr_sum = ts_sum(atr, period)
    
    # 計算最高價和最低價
    max_high = ts_max(high, period)
    min_low = ts_min(low, period)
    
    # 計算範圍
    range_val = max_high.data.copy()
    range_val['factor'] = max_high.data['factor'] - min_low.data['factor']
    range_factor = Factor(range_val, "Range")
    
    # 避免除零和對數問題
    range_factor.data['factor'] = range_factor.data['factor'].clip(lower=1e-10)
    
    # 計算 CHOP
    ratio = atr_sum.data.copy()
    ratio['factor'] = atr_sum.data['factor'] / range_factor.data['factor']
    ratio['factor'] = ratio['factor'].clip(lower=1e-10)  # 確保 > 0 以便對數運算
    
    # CHOP = 100 * log10(ratio) / log10(period)
    chop_df = ratio.copy()
    chop_df['factor'] = 100 * np.log10(ratio['factor']) / np.log10(period)
    chop_df['factor'] = chop_df['factor'].clip(0, 100)  # 限制在 0-100
    
    return Factor(chop_df, f"CHOP({period})")


def calculate_adx(high: Factor, low: Factor, close: Factor, period: int = 14) -> Factor:
    """
    計算 Average Directional Index (ADX)
    
    參數
    ----------
    high : Factor
        最高價因子
    low : Factor
        最低價因子
    close : Factor
        收盤價因子
    period : int
        計算週期
    
    返回
    -------
    Factor
        ADX 因子 (0-100)
    """
    # 計算 +DM 和 -DM
    high_diff = high.data.copy()
    high_diff['factor'] = high.data.groupby('symbol')['factor'].diff(1)
    
    low_diff = low.data.copy()
    low_diff['factor'] = -low.data.groupby('symbol')['factor'].diff(1)
    
    # +DM = High_t - High_{t-1} if > 0 and > |Low_t - Low_{t-1}|
    # -DM = Low_{t-1} - Low_t if > 0 and > |High_t - High_{t-1}|
    plus_dm = high_diff.copy()
    plus_dm['factor'] = np.where(
        (high_diff['factor'] > low_diff['factor'].abs()) & (high_diff['factor'] > 0),
        high_diff['factor'],
        0
    )
    
    minus_dm = low_diff.copy()
    minus_dm['factor'] = np.where(
        (low_diff['factor'].abs() > high_diff['factor']) & (low_diff['factor'] < 0),
        low_diff['factor'].abs(),
        0
    )
    
    # 計算 ATR
    atr = calculate_atr(high, low, close, period=1)
    
    # 平滑 +DM 和 -DM
    plus_dm_factor = Factor(plus_dm, "+DM")
    minus_dm_factor = Factor(minus_dm, "-DM")
    
    plus_dm_smooth = ts_mean(plus_dm_factor, period)
    minus_dm_smooth = ts_mean(minus_dm_factor, period)
    
    # 計算 +DI 和 -DI
    atr_data = atr.data.set_index(['timestamp', 'symbol'])['factor']
    plus_dm_data = plus_dm_smooth.data.set_index(['timestamp', 'symbol'])['factor']
    minus_dm_data = minus_dm_smooth.data.set_index(['timestamp', 'symbol'])['factor']
    
    plus_di_df = plus_dm_smooth.data.copy()
    plus_di_df['factor'] = 100 * plus_dm_data / (atr_data + 1e-10)
    plus_di_df['factor'] = plus_di_df['factor'].clip(0, 100)
    
    minus_di_df = minus_dm_smooth.data.copy()
    minus_di_df['factor'] = 100 * minus_dm_data / (atr_data + 1e-10)
    minus_di_df['factor'] = minus_di_df['factor'].clip(0, 100)
    
    # 計算 DX
    dx_df = plus_di_df.copy()
    di_sum = plus_di_df['factor'] + minus_di_df['factor']
    di_diff = np.abs(plus_di_df['factor'] - minus_di_df['factor'])
    dx_df['factor'] = 100 * di_diff / (di_sum + 1e-10)
    
    # 計算 ADX（DX 的移動平均）
    dx_factor = Factor(dx_df, "DX")
    adx = ts_mean(dx_factor, period)
    
    return Factor(adx.data, f"ADX({period})")


def adaptive_donchian_window(base_window: int, er: Factor, min_window: int = 10, max_window: int = 100) -> Factor:
    """
    計算自適應 Donchian 窗口大小
    
    N_adaptive = Floor(base_window / ER)
    
    參數
    ----------
    base_window : int
        基礎窗口大小
    er : Factor
        Efficiency Ratio 因子
    min_window : int
        最小窗口大小
    max_window : int
        最大窗口大小
    
    返回
    -------
    Factor
        自適應窗口大小因子
    """
    result_df = er.data.copy()
    
    # 避免除零，ER 最小為 0.01
    er_clipped = er.data['factor'].clip(lower=0.01, upper=1.0)
    
    # 計算自適應窗口
    adaptive_window = np.floor(base_window / er_clipped).astype(int)
    adaptive_window = np.clip(adaptive_window, min_window, max_window)
    
    result_df['factor'] = adaptive_window
    
    return Factor(result_df, f"AdaptiveWindow({base_window})")


def signal_strength_score(close: Factor, upper_band: Factor, lower_band: Factor) -> Factor:
    """
    計算連續信號強度分數
    
    Score = (Close - LowerBand) / (UpperBand - LowerBand)
    
    參數
    ----------
    close : Factor
        收盤價因子
    upper_band : Factor
        上軌因子
    lower_band : Factor
        下軌因子
    
    返回
    -------
    Factor
        信號強度分數 (-1 到 1)
    """
    close_data = close.data.set_index(['timestamp', 'symbol'])['factor']
    upper_data = upper_band.data.set_index(['timestamp', 'symbol'])['factor']
    lower_data = lower_band.data.set_index(['timestamp', 'symbol'])['factor']
    
    result_df = close.data.copy()
    result_df['factor'] = result_df.apply(
        lambda row: (close_data.get((row['timestamp'], row['symbol']), 0) - 
                    lower_data.get((row['timestamp'], row['symbol']), 0)) / 
                   (upper_data.get((row['timestamp'], row['symbol']), 0) - 
                    lower_data.get((row['timestamp'], row['symbol']), 0) + 1e-10),
        axis=1
    )
    
    # 標準化到 -1 到 1 範圍
    # Score > 1.0: 突破上軌 (做多)
    # Score < 0.0: 跌破下軌 (做空)
    # Score 0.5: 均衡
    result_df['factor'] = (result_df['factor'] - 0.5) * 2  # 轉換到 -1 到 1
    
    return Factor(result_df, "SignalStrength")

