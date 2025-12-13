"""
超保守版 ALM 策略 - 極致降低換手率

目標：將換手率從 6,665% 降低到 < 500%

主要改進：
1. 極寬的遲滯區間（Hysteresis Band）
2. 強制最小持倉時間（48-72 小時）
3. 更高的信號閾值（0.7-0.8）
4. 更長的信號平滑窗口（10-15）
5. 更嚴格的狀態過濾
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from phandas import *
from .strategy_improved import (
    calculate_weighted_signal_score,
    apply_signal_smoothing,
    calculate_adaptive_parameters
)
from .strategy import apply_inverse_volatility_weighting
from .strategy import (
    calculate_ema,
    calculate_atr,
    calculate_donchian_breakout,
    calculate_4h_trend_filter,
    calculate_volatility_filter,
    calculate_funding_rate_filter,
    broadcast_4h_to_1h,
    OKX_TOP_15_ASSETS
)
import logging

logger = logging.getLogger(__name__)


def apply_ultra_wide_hysteresis(
    signal_score: Factor,
    entry_threshold: float = 0.75,
    exit_threshold: float = 0.25,
    min_holding_periods: int = 48  # 48 小時 = 2 天
) -> Factor:
    """
    應用超寬遲滯區間，大幅降低換手率
    
    參數
    ----------
    signal_score : Factor
        信號強度分數（-1 到 1）
    entry_threshold : float
        入場閾值（必須 > 此值才做多）
    exit_threshold : float
        出場閾值（必須 < 此值才平倉）
    min_holding_periods : int
        最小持倉時間（小時數）
    
    返回
    -------
    Factor
        應用遲滯邏輯後的信號
    """
    signal_data = signal_score.data.copy()
    signal_data = signal_data.sort_values(['symbol', 'timestamp']).reset_index(drop=True)
    
    # 初始化信號列
    signal_data['final_signal'] = 0.0
    signal_data['entry_time'] = None
    
    # 對每個資產分別處理
    for symbol in signal_data['symbol'].unique():
        symbol_mask = signal_data['symbol'] == symbol
        symbol_indices = signal_data[symbol_mask].index
        symbol_data = signal_data.loc[symbol_indices].copy().reset_index(drop=True)
        
        current_signal = 0  # -1: 做空, 0: 空倉, 1: 做多
        entry_timestamp = None
        
        for i in range(len(symbol_data)):
            idx = symbol_indices[i]
            row = symbol_data.iloc[i]
            score = row['factor']
            timestamp = row['timestamp']
            
            # 檢查是否達到最小持倉時間
            if entry_timestamp is not None:
                hours_held = (pd.to_datetime(timestamp) - pd.to_datetime(entry_timestamp)).total_seconds() / 3600
                if hours_held < min_holding_periods:
                    # 強制持有，除非觸發硬止損（這裡簡化處理）
                    signal_data.loc[idx, 'final_signal'] = current_signal
                    if entry_timestamp:
                        signal_data.loc[idx, 'entry_time'] = entry_timestamp
                    continue
            
            # 遲滯邏輯
            if current_signal == 0:  # 空倉狀態
                if score > entry_threshold:
                    current_signal = 1  # 做多
                    entry_timestamp = timestamp
                elif score < -entry_threshold:
                    current_signal = -1  # 做空
                    entry_timestamp = timestamp
            elif current_signal == 1:  # 持有多倉
                if score < exit_threshold:
                    current_signal = 0  # 平倉
                    entry_timestamp = None
            elif current_signal == -1:  # 持有空倉
                if score > -exit_threshold:
                    current_signal = 0  # 平倉
                    entry_timestamp = None
            
            signal_data.loc[idx, 'final_signal'] = current_signal
            if entry_timestamp:
                signal_data.loc[idx, 'entry_time'] = entry_timestamp
            else:
                signal_data.loc[idx, 'entry_time'] = None
    
    # 創建最終信號因子
    final_signal_df = signal_data[['timestamp', 'symbol', 'final_signal']].copy()
    final_signal_df.rename(columns={'final_signal': 'factor'}, inplace=True)
    
    return Factor(final_signal_df, "UltraConservativeSignal")


def build_alm_strategy_ultra_conservative(
    panel_1h: Panel,
    panel_4h: Panel,
    # 信號閾值（極高）
    signal_entry_threshold: float = 0.75,
    signal_exit_threshold: float = 0.25,
    # 平滑參數（極長）
    smoothing_window: int = 15,
    # 持倉時間（極長）
    min_holding_periods: int = 72,  # 72 小時 = 3 天
    # 權重配置（更重視趨勢）
    signal_weights: Optional[Dict[str, float]] = None,
    # 自適應參數
    enable_adaptive_params: bool = True,
    base_window: int = 30,  # 更長的基礎窗口
    # 其他過濾器
    enable_volatility_filter: bool = True,
    volatility_threshold: float = 0.003,  # 更嚴格的波動率過濾
    enable_funding_filter: bool = True
) -> Factor:
    """
    構建超保守版 ALM 策略
    
    目標：極致降低換手率，目標 < 500% 年化
    
    參數
    ----------
    panel_1h : Panel
        1H 時間框架數據
    panel_4h : Panel
        4H 時間框架數據
    signal_entry_threshold : float
        入場信號閾值（0.75 = 75% 信號強度才入場）
    signal_exit_threshold : float
        出場信號閾值（0.25 = 25% 以下才出場）
    smoothing_window : int
        信號平滑窗口（15 = 15 小時移動平均）
    min_holding_periods : int
        最小持倉時間（72 = 72 小時 = 3 天）
    signal_weights : Dict[str, float], optional
        信號權重配置
    enable_adaptive_params : bool
        是否啟用自適應參數
    base_window : int
        基礎窗口大小
    enable_volatility_filter : bool
        是否啟用波動率過濾
    volatility_threshold : float
        波動率閾值
    enable_funding_filter : bool
        是否啟用資金費率過濾
    
    返回
    -------
    Factor
        策略信號因子
    """
    logger.info("構建超保守版 ALM 策略...")
    logger.info(f"  入場閾值: {signal_entry_threshold}")
    logger.info(f"  出場閾值: {signal_exit_threshold}")
    logger.info(f"  平滑窗口: {smoothing_window}")
    logger.info(f"  最小持倉: {min_holding_periods} 小時")
    
    # 1. 4H 趨勢過濾器
    close_4h = panel_4h['close']
    trend_long, trend_short = calculate_4h_trend_filter(close_4h)
    trend_long_1h = broadcast_4h_to_1h(trend_long, panel_1h.data['timestamp'].unique())
    trend_short_1h = broadcast_4h_to_1h(trend_short, panel_1h.data['timestamp'].unique())
    
    # 趨勢評分（0-1）
    trend_score = trend_long_1h.data.copy()
    trend_score['factor'] = trend_score['factor'].astype(float)
    
    # 2. 1H Donchian 突破
    close_1h = panel_1h['close']
    high_1h = panel_1h['high']
    low_1h = panel_1h['low']
    
    # 自適應窗口
    if enable_adaptive_params:
        # 計算波動率（ATR/Price）用於自適應參數
        atr = calculate_atr(high_1h, low_1h, close_1h)
        volatility = atr / close_1h  # ATR/Price 作為波動率指標
        
        adaptive_params = calculate_adaptive_parameters(
            volatility,
            base_window=base_window,
            volatility_percentile=0.7
        )
        # adaptive_params['donchian_window'] 已經是整數，不需要訪問 .data
        donchian_window = adaptive_params['donchian_window']
    else:
        donchian_window = base_window
    
    logger.info(f"  使用 Donchian 窗口: {donchian_window}")
    
    long_breakout, short_breakout = calculate_donchian_breakout(
        close_1h, high_1h, low_1h, window=donchian_window
    )
    
    # 突破評分（0-1）
    breakout_score = long_breakout.data.copy()
    breakout_score['factor'] = breakout_score['factor'].astype(float)
    
    # 3. 波動率過濾器
    if enable_volatility_filter:
        atr = calculate_atr(high_1h, low_1h, close_1h)
        volatility_score = calculate_volatility_filter(
            close_1h, atr, threshold=volatility_threshold
        )
    else:
        volatility_score = close_1h.data.copy()
        volatility_score['factor'] = 1.0
    
    # 4. 成交量確認
    volume_1h = panel_1h['volume']
    volume_ma = ts_mean(volume_1h, window=20)
    # 使用 where 函數（需要 Factor 對象）
    volume_confirmation_factor = where(
        volume_1h > volume_ma,
        Factor(volume_1h.data.copy().assign(factor=1.0), "VolumeConfHigh"),
        Factor(volume_1h.data.copy().assign(factor=0.5), "VolumeConfLow")
    )
    volume_score = volume_confirmation_factor
    
    # 5. 資金費率過濾
    if enable_funding_filter:
        # 假設資金費率數據（實際應從交易所獲取）
        funding_rate = close_1h.data.copy()
        funding_rate['factor'] = 0.0  # 簡化處理
        funding_score_long, funding_score_short = calculate_funding_rate_filter(
            Factor(funding_rate, "FundingRate")
        )
        funding_score = funding_score_long.data.copy()
        funding_score['factor'] = funding_score['factor'].astype(float)
    else:
        funding_score = close_1h.data.copy()
        funding_score['factor'] = 1.0
    
    # 6. 加權評分
    if signal_weights is None:
        signal_weights = {
            'trend': 0.40,      # 更重視趨勢
            'breakout': 0.30,
            'volatility': 0.10,
            'volume': 0.10,
            'funding': 0.10
        }
    
    weighted_score = calculate_weighted_signal_score(
        Factor(trend_score, "Trend"),
        Factor(breakout_score, "Breakout"),
        Factor(volatility_score.data, "Volatility"),
        volume_score,
        Factor(funding_score, "Funding"),
        weights=signal_weights
    )
    
    # 7. 信號平滑（極長窗口）
    smoothed_score = apply_signal_smoothing(
        weighted_score,
        window=smoothing_window,
        method='ma'
    )
    
    # 8. 應用超寬遲滯區間
    final_signal = apply_ultra_wide_hysteresis(
        smoothed_score,
        entry_threshold=signal_entry_threshold,
        exit_threshold=signal_exit_threshold,
        min_holding_periods=min_holding_periods
    )
    
    logger.info("超保守版策略構建完成")
    
    return final_signal

