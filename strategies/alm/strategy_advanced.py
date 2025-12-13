"""
ALM 策略 - 高級優化版本
整合市場狀態檢測、自適應參數、滯後邏輯、Chandelier Exit 等
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from phandas import *
from .indicators import (
    calculate_atr,
    efficiency_ratio,
    choppiness_index,
    calculate_adx,
    adaptive_donchian_window,
    signal_strength_score
)
from .regime import detect_regime
from .numba_logic import (
    apply_hysteresis_numba,
    calculate_chandelier_exit,
    apply_chandelier_exit_to_signal
)
from .strategy import broadcast_4h_to_1h
from core.risk import calculate_volatility_targeted_weights, apply_rebalancing_buffer
import logging

logger = logging.getLogger(__name__)


def build_adaptive_donchian_channels(
    high: Factor,
    low: Factor,
    close: Factor,
    base_window: int = 20,
    er_period: int = 20,
    min_window: int = 10,
    max_window: int = 100
) -> Tuple[Factor, Factor, Factor]:
    """
    構建自適應 Donchian 通道
    
    參數
    ----------
    high : Factor
        最高價因子
    low : Factor
        最低價因子
    close : Factor
        收盤價因子
    base_window : int
        基礎窗口大小
    er_period : int
        Efficiency Ratio 計算週期
    min_window : int
        最小窗口大小
    max_window : int
        最大窗口大小
    
    返回
    -------
    Tuple[Factor, Factor, Factor]
        (upper_band, lower_band, middle_band)
    """
    # 計算 Efficiency Ratio
    er = efficiency_ratio(close, period=er_period)
    
    # 計算自適應窗口
    adaptive_window = adaptive_donchian_window(
        base_window=base_window,
        er=er,
        min_window=min_window,
        max_window=max_window
    )
    
    # 對每個資產和時間點計算自適應通道
    result_rows = []
    
    for symbol in close.data['symbol'].unique():
        symbol_data = close.data[close.data['symbol'] == symbol].copy()
        symbol_data = symbol_data.sort_values('timestamp').reset_index(drop=True)
        
        symbol_high = high.data[high.data['symbol'] == symbol].sort_values('timestamp')
        symbol_low = low.data[low.data['symbol'] == symbol].sort_values('timestamp')
        symbol_window = adaptive_window.data[adaptive_window.data['symbol'] == symbol].sort_values('timestamp')
        
        upper_values = []
        lower_values = []
        middle_values = []
        
        for i in range(len(symbol_data)):
            window_size = int(symbol_window.iloc[i]['factor'])
            start_idx = max(0, i - window_size + 1)
            
            # 計算滾動最高和最低
            window_high = symbol_high.iloc[start_idx:i+1]['factor'].max()
            window_low = symbol_low.iloc[start_idx:i+1]['factor'].min()
            
            upper_values.append(window_high)
            lower_values.append(window_low)
            middle_values.append((window_high + window_low) / 2)
        
        for i, row in symbol_data.iterrows():
            result_rows.append({
                'timestamp': row['timestamp'],
                'symbol': symbol,
                'upper': upper_values[i],
                'lower': lower_values[i],
                'middle': middle_values[i]
            })
    
    result_df = pd.DataFrame(result_rows)
    
    upper_band = Factor(
        result_df[['timestamp', 'symbol']].assign(factor=result_df['upper']),
        "AdaptiveUpperBand"
    )
    lower_band = Factor(
        result_df[['timestamp', 'symbol']].assign(factor=result_df['lower']),
        "AdaptiveLowerBand"
    )
    middle_band = Factor(
        result_df[['timestamp', 'symbol']].assign(factor=result_df['middle']),
        "AdaptiveMiddleBand"
    )
    
    return upper_band, lower_band, middle_band


def build_alm_strategy_advanced(
    panel_1h: Panel,
    panel_daily: Optional[Panel] = None,
    # 基礎參數
    base_window: int = 20,
    atr_window: int = 14,
    # 狀態檢測參數
    chop_period: int = 14,
    adx_period: int = 14,
    er_period: int = 20,
    chop_threshold_choppy: float = 61.8,
    chop_threshold_trending: float = 38.2,
    adx_threshold_weak: float = 20,
    adx_threshold_strong: float = 25,
    # 自適應參數
    min_window: int = 10,
    max_window: int = 100,
    # Chandelier Exit 參數
    chandelier_k: float = 2.5,
    enable_chandelier: bool = True,
    # 風險管理參數
    target_volatility: float = 0.15,
    rebalance_buffer: float = 0.10,
    enable_vol_targeting: bool = True,
    # 信號強度閾值
    signal_threshold: float = 0.3
) -> Factor:
    """
    構建高級優化版 ALM 策略
    
    主要特性：
    1. 市場狀態檢測（CHOP + ADX）
    2. 自適應 Donchian 通道（基於 ER）
    3. 滯後邏輯（Hysteresis）
    4. Chandelier Exit（追蹤止損）
    5. 波動率目標和再平衡緩衝區
    
    參數
    ----------
    panel_1h : Panel
        1H 數據面板
    panel_daily : Panel, optional
        日線數據面板（用於狀態檢測）
    base_window : int
        基礎 Donchian 窗口
    atr_window : int
        ATR 計算窗口
    chop_period : int
        CHOP 計算週期
    adx_period : int
        ADX 計算週期
    er_period : int
        ER 計算週期
    chandelier_k : float
        Chandelier Exit 的 ATR 倍數
    target_volatility : float
        目標波動率（年化）
    rebalance_buffer : float
        再平衡緩衝區百分比
    signal_threshold : float
        信號強度閾值
    
    返回
    -------
    Factor
        策略信號因子
    """
    logger.info("構建高級優化版 ALM 策略...")
    
    # 提取數據
    close_1h = panel_1h['close']
    high_1h = panel_1h['high']
    low_1h = panel_1h['low']
    open_1h = panel_1h['open']
    volume_1h = panel_1h['volume']
    
    # 1. 市場狀態檢測（使用日線數據，如果提供）
    logger.info("檢測市場狀態...")
    if panel_daily is not None:
        regime_data = detect_regime(
            panel_daily,
            chop_period=chop_period,
            adx_period=adx_period,
            er_period=er_period,
            chop_threshold_choppy=chop_threshold_choppy,
            chop_threshold_trending=chop_threshold_trending,
            adx_threshold_weak=adx_threshold_weak,
            adx_threshold_strong=adx_threshold_strong
        )
        
        # 將日線狀態廣播到 1H
        regime_filter_daily = regime_data['regime_filter']
        index_1h = pd.DatetimeIndex(pd.to_datetime(close_1h.data['timestamp']).unique())
        regime_filter_1h = broadcast_4h_to_1h(regime_filter_daily, index_1h)
    else:
        # 使用 1H 數據（簡化）
        regime_data = detect_regime(
            panel_1h,
            chop_period=chop_period,
            adx_period=adx_period,
            er_period=er_period
        )
        regime_filter_1h = regime_data['regime_filter']
    
    logger.info(f"  狀態過濾器已應用")
    
    # 2. 構建自適應 Donchian 通道
    logger.info("構建自適應 Donchian 通道...")
    upper_band, lower_band, middle_band = build_adaptive_donchian_channels(
        high_1h,
        low_1h,
        close_1h,
        base_window=base_window,
        er_period=er_period,
        min_window=min_window,
        max_window=max_window
    )
    logger.info(f"  自適應通道已構建")
    
    # 3. 應用滯後邏輯（Hysteresis）
    logger.info("應用滯後邏輯...")
    
    # 準備數據用於 Numba 函數
    signal_data = []
    
    for symbol in close_1h.data['symbol'].unique():
        symbol_close = close_1h.data[close_1h.data['symbol'] == symbol].sort_values('timestamp')
        symbol_high = high_1h.data[high_1h.data['symbol'] == symbol].sort_values('timestamp')
        symbol_low = low_1h.data[low_1h.data['symbol'] == symbol].sort_values('timestamp')
        symbol_upper = upper_band.data[upper_band.data['symbol'] == symbol].sort_values('timestamp')
        symbol_lower = lower_band.data[lower_band.data['symbol'] == symbol].sort_values('timestamp')
        symbol_middle = middle_band.data[middle_band.data['symbol'] == symbol].sort_values('timestamp')
        
        # 轉換為 NumPy 數組
        price = symbol_close['factor'].values
        upper = symbol_upper['factor'].values
        lower = symbol_lower['factor'].values
        middle = symbol_middle['factor'].values
        
        # 應用 Numba 優化的滯後邏輯
        raw_signal = apply_hysteresis_numba(price, upper, lower, middle)
        
        # 保存結果
        for i, row in symbol_close.iterrows():
            signal_data.append({
                'timestamp': row['timestamp'],
                'symbol': symbol,
                'factor': raw_signal[i]
            })
    
    raw_signal_factor = Factor(pd.DataFrame(signal_data), "RawSignal")
    logger.info(f"  滯後邏輯已應用")
    
    # 4. 應用狀態過濾器
    logger.info("應用狀態過濾器...")
    regime_data_1h = regime_filter_1h.data.set_index(['timestamp', 'symbol'])['factor']
    filtered_signal_data = raw_signal_factor.data.copy()
    
    filtered_signal_data['factor'] = filtered_signal_data.apply(
        lambda row: raw_signal_factor.data.loc[row.name, 'factor'] * 
                   regime_data_1h.get((row['timestamp'], row['symbol']), 0),
        axis=1
    )
    
    filtered_signal = Factor(filtered_signal_data, "FilteredSignal")
    logger.info(f"  狀態過濾器已應用")
    
    # 5. 計算 Chandelier Exit（如果啟用）
    if enable_chandelier:
        logger.info("計算 Chandelier Exit...")
        
        atr = calculate_atr(high_1h, low_1h, close_1h, atr_window)
        
        chandelier_signals = []
        
        for symbol in close_1h.data['symbol'].unique():
            symbol_close = close_1h.data[close_1h.data['symbol'] == symbol].sort_values('timestamp')
            symbol_high = high_1h.data[high_1h.data['symbol'] == symbol].sort_values('timestamp')
            symbol_low = low_1h.data[low_1h.data['symbol'] == symbol].sort_values('timestamp')
            symbol_atr = atr.data[atr.data['symbol'] == symbol].sort_values('timestamp')
            symbol_signal = filtered_signal.data[filtered_signal.data['symbol'] == symbol].sort_values('timestamp')
            
            price = symbol_close['factor'].values
            high_arr = symbol_high['factor'].values
            low_arr = symbol_low['factor'].values
            atr_arr = symbol_atr['factor'].values
            signal_arr = symbol_signal['factor'].values
            
            # 計算 Chandelier Exit
            stop_long, stop_short = calculate_chandelier_exit(
                high_arr, low_arr, price, atr_arr, signal_arr, k=chandelier_k
            )
            
            # 應用止損到信號
            final_signal = apply_chandelier_exit_to_signal(price, signal_arr, stop_long, stop_short)
            
            for i, row in symbol_close.iterrows():
                chandelier_signals.append({
                    'timestamp': row['timestamp'],
                    'symbol': symbol,
                    'factor': final_signal[i]
                })
        
        final_signal_factor = Factor(pd.DataFrame(chandelier_signals), "FinalSignal")
        logger.info(f"  Chandelier Exit 已應用")
    else:
        final_signal_factor = filtered_signal
    
    # 6. 應用信號強度閾值（可選）
    if signal_threshold > 0:
        logger.info(f"應用信號強度閾值 ({signal_threshold})...")
        signal_strength = signal_strength_score(close_1h, upper_band, lower_band)
        
        final_data = final_signal_factor.data.copy()
        strength_data = signal_strength.data.set_index(['timestamp', 'symbol'])['factor']
        
        final_data['factor'] = final_data.apply(
            lambda row: final_signal_factor.data.loc[row.name, 'factor'] 
                       if abs(strength_data.get((row['timestamp'], row['symbol']), 0)) >= signal_threshold
                       else 0.0,
            axis=1
        )
        
        final_signal_factor = Factor(final_data, "ThresholdedSignal")
    
    logger.info("策略構建完成")
    
    return final_signal_factor

