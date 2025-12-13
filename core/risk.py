"""
風險管理模組
包含波動率目標和再平衡緩衝區邏輯
"""

import numpy as np
import pandas as pd
from phandas import Factor, ts_std_dev, ts_delay
from typing import Optional


def calculate_volatility_targeted_weights(
    returns: Factor,
    target_volatility: float = 0.15,
    window: int = 20,
    annualization_factor: float = 365.0 * 24.0  # 假設小時數據
) -> Factor:
    """
    計算波動率目標權重
    
    Target Weight = Target Vol / Realized Vol
    
    參數
    ----------
    returns : Factor
        收益率因子
    target_volatility : float
        目標波動率（年化，例如 0.15 = 15%）
    window : int
        計算波動率的窗口大小
    annualization_factor : float
        年化因子
    
    返回
    -------
    Factor
        目標權重因子
    """
    # 計算實現波動率（年化）
    realized_vol = ts_std_dev(returns, window)
    realized_vol_annualized = Factor(
        realized_vol.data.copy().assign(
            factor=realized_vol.data['factor'] * np.sqrt(annualization_factor)
        ),
        "RealizedVol"
    )
    
    # 計算目標權重
    target_weights = Factor(
        realized_vol_annualized.data.copy().assign(
            factor=target_volatility / (realized_vol_annualized.data['factor'] + 1e-10)
        ),
        "TargetWeights"
    )
    
    # 限制最大權重（避免極端槓桿）
    target_weights.data['factor'] = target_weights.data['factor'].clip(upper=2.0)
    
    return target_weights


def apply_rebalancing_buffer(
    current_weights: Factor,
    target_weights: Factor,
    buffer_pct: float = 0.10
) -> Factor:
    """
    應用再平衡緩衝區
    
    只有當當前權重偏離目標權重超過緩衝區時才再平衡
    
    參數
    ----------
    current_weights : Factor
        當前權重因子
    target_weights : Factor
        目標權重因子
    buffer_pct : float
        緩衝區百分比（例如 0.10 = 10%）
    
    返回
    -------
    Factor
        應用緩衝區後的權重因子
    """
    current_data = current_weights.data.set_index(['timestamp', 'symbol'])['factor']
    target_data = target_weights.data.set_index(['timestamp', 'symbol'])['factor']
    
    result_df = current_weights.data.copy()
    
    def apply_buffer(row):
        timestamp = row['timestamp']
        symbol = row['symbol']
        
        current = current_data.get((timestamp, symbol), 0)
        target = target_data.get((timestamp, symbol), 0)
        
        # 計算緩衝區範圍
        buffer_lower = target * (1 - buffer_pct)
        buffer_upper = target * (1 + buffer_pct)
        
        # 如果當前權重在緩衝區內，保持不變
        if buffer_lower <= current <= buffer_upper:
            return current
        else:
            # 超出緩衝區，調整到目標
            return target
    
    result_df['factor'] = result_df.apply(apply_buffer, axis=1)
    
    return Factor(result_df, f"BufferedWeights({buffer_pct:.0%})")

