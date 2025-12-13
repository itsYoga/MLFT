"""
Numba 加速的路徑依賴邏輯
包含 Hysteresis 和 Chandelier Exit 的優化實現
"""

import numpy as np
from numba import njit
from typing import Tuple


@njit
def apply_hysteresis_numba(
    price: np.ndarray,
    upper_band: np.ndarray,
    lower_band: np.ndarray,
    middle_band: np.ndarray
) -> np.ndarray:
    """
    應用滯後邏輯（Schmitt Trigger）生成信號
    
    入口條件：Price > Upper Band
    出口條件：Price < Middle Band OR Price < Lower Band
    
    參數
    ----------
    price : np.ndarray
        價格數組
    upper_band : np.ndarray
        上軌數組
    lower_band : np.ndarray
        下軌數組
    middle_band : np.ndarray
        中軌數組（用於出口）
    
    返回
    -------
    np.ndarray
        信號數組 (1=做多, -1=做空, 0=無信號)
    """
    n = len(price)
    signal = np.zeros(n, dtype=np.float64)
    state = 0  # 0: 無倉位, 1: 多倉, -1: 空倉
    
    for i in range(1, n):
        if state == 0:
            # 無倉位：檢查入口條件
            if price[i] > upper_band[i]:
                state = 1  # 做多
            elif price[i] < lower_band[i]:
                state = -1  # 做空
        elif state == 1:
            # 多倉：檢查出口條件
            if price[i] < middle_band[i] or price[i] < lower_band[i]:
                state = 0  # 平倉
        elif state == -1:
            # 空倉：檢查出口條件
            if price[i] > middle_band[i] or price[i] > upper_band[i]:
                state = 0  # 平倉
        
        signal[i] = state
    
    return signal


@njit
def calculate_chandelier_exit(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    signal: np.ndarray,
    k: float = 2.5
) -> Tuple[np.ndarray, np.ndarray]:
    """
    計算 Chandelier Exit（追蹤止損）
    
    Stop_long = Highest High since entry - k * ATR
    Stop_short = Lowest Low since entry + k * ATR
    
    參數
    ----------
    high : np.ndarray
        最高價數組
    low : np.ndarray
        最低價數組
    close : np.ndarray
        收盤價數組
    atr : np.ndarray
        ATR 數組
    signal : np.ndarray
        信號數組 (1=做多, -1=做空, 0=無信號)
    k : float
        ATR 倍數（默認 2.5）
    
    返回
    -------
    Tuple[np.ndarray, np.ndarray]
        (stop_long, stop_short) 止損價格數組
    """
    n = len(close)
    stop_long = np.full(n, np.nan)
    stop_short = np.full(n, np.nan)
    
    highest_high = np.nan
    lowest_low = np.nan
    entry_idx = -1
    
    for i in range(n):
        if signal[i] == 1:
            # 做多信號
            if entry_idx == -1:
                # 新開倉
                entry_idx = i
                highest_high = high[i]
            else:
                # 更新最高價
                if high[i] > highest_high:
                    highest_high = high[i]
                # 計算止損
                stop_long[i] = highest_high - k * atr[i]
        elif signal[i] == -1:
            # 做空信號
            if entry_idx == -1:
                # 新開倉
                entry_idx = i
                lowest_low = low[i]
            else:
                # 更新最低價
                if low[i] < lowest_low:
                    lowest_low = low[i]
                # 計算止損
                stop_short[i] = lowest_low + k * atr[i]
        else:
            # 無信號，重置
            entry_idx = -1
            highest_high = np.nan
            lowest_low = np.nan
    
    return stop_long, stop_short


@njit
def apply_chandelier_exit_to_signal(
    close: np.ndarray,
    signal: np.ndarray,
    stop_long: np.ndarray,
    stop_short: np.ndarray
) -> np.ndarray:
    """
    應用 Chandelier Exit 到信號，強制平倉
    
    參數
    ----------
    close : np.ndarray
        收盤價數組
    signal : np.ndarray
        原始信號數組
    stop_long : np.ndarray
        多倉止損價格數組
    stop_short : np.ndarray
        空倉止損價格數組
    
    返回
    -------
    np.ndarray
        應用止損後的信號數組
    """
    n = len(close)
    filtered_signal = signal.copy()
    
    for i in range(n):
        if signal[i] == 1:
            # 多倉：檢查是否觸及止損
            if not np.isnan(stop_long[i]) and close[i] < stop_long[i]:
                filtered_signal[i] = 0  # 平倉
        elif signal[i] == -1:
            # 空倉：檢查是否觸及止損
            if not np.isnan(stop_short[i]) and close[i] > stop_short[i]:
                filtered_signal[i] = 0  # 平倉
    
    return filtered_signal

