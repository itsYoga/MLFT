"""
優化版 ALM 策略 - 降低換手率版本
添加了多種信號過濾器來避免頻繁交易
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from phandas import *
from .strategy import (
    calculate_ema,
    calculate_atr,
    calculate_donchian_breakout,
    calculate_4h_trend_filter,
    calculate_volatility_filter,
    calculate_funding_rate_filter,
    OKX_TOP_15_ASSETS
)
import logging

logger = logging.getLogger(__name__)


def apply_signal_persistence_filter(
    signal: Factor,
    min_periods: int = 4,
    method: str = 'forward_fill'
) -> Factor:
    """
    信號持續性過濾器：要求信號持續一定時間才生效
    
    這可以大幅降低換手率，避免因短期波動導致的頻繁交易
    
    Parameters
    ----------
    signal : Factor
        原始信號因子
    min_periods : int
        信號必須持續的最少週期數（例如 4 小時）
    method : str
        過濾方法：
        - 'forward_fill': 前向填充，信號持續 min_periods 後才生效
        - 'backward_fill': 後向填充，信號出現後回溯 min_periods
        - 'both': 雙向填充，最嚴格
    
    Returns
    -------
    Factor
        過濾後的信號
    """
    result_data = signal.data.copy()
    
    def filter_group(group):
        """對每個資產應用過濾"""
        values = group['factor'].values
        
        if method == 'forward_fill':
            # 前向填充：信號出現後，需要持續 min_periods 才生效
            filtered = np.zeros_like(values)
            signal_start = None
            
            for i in range(len(values)):
                if values[i] != 0:
                    if signal_start is None:
                        signal_start = i
                    elif i - signal_start >= min_periods - 1:
                        # 信號已持續足夠時間，開始生效
                        filtered[signal_start:i+1] = values[i]
                else:
                    signal_start = None
                    filtered[i] = 0
            
            return pd.Series(filtered, index=group.index)
        
        elif method == 'backward_fill':
            # 後向填充：信號出現後，回溯填充前 min_periods
            filtered = np.zeros_like(values)
            
            for i in range(len(values)):
                if values[i] != 0:
                    start_idx = max(0, i - min_periods + 1)
                    filtered[start_idx:i+1] = values[i]
            
            return pd.Series(filtered, index=group.index)
        
        else:  # both
            # 最嚴格：信號必須在 min_periods 內持續存在
            filtered = np.zeros_like(values)
            
            for i in range(min_periods - 1, len(values)):
                window = values[i - min_periods + 1:i + 1]
                if len(window) == min_periods and np.all(window != 0) and np.all(np.sign(window) == np.sign(window[0])):
                    filtered[i] = values[i]
            
            return pd.Series(filtered, index=group.index)
    
    # Fix FutureWarning: apply only to 'factor' column
    def apply_to_group(name_group):
        name, group = name_group
        return filter_group(group)
    
    grouped = result_data.groupby('symbol', group_keys=False)
    result_data['factor'] = pd.concat([
        pd.Series(filter_group(group), index=group.index, name='factor')
        for name, group in grouped
    ]).reindex(result_data.index)
    
    return Factor(result_data, f"PersistenceFilter({signal.name},{min_periods})")


def apply_signal_strength_filter(
    signal: Factor,
    strength_threshold: float = 0.5
) -> Factor:
    """
    信號強度過濾器：只保留強信號
    
    通過設置閾值，過濾掉弱信號，只保留強信號，減少交易頻率
    
    Parameters
    ----------
    signal : Factor
        原始信號因子
    strength_threshold : float
        信號強度閾值（0-1），只有絕對值大於此值的信號才保留
    
    Returns
    -------
    Factor
        過濾後的信號
    """
    result_data = signal.data.copy()
    result_data['factor'] = np.where(
        np.abs(result_data['factor']) >= strength_threshold,
        result_data['factor'],
        0.0
    )
    
    return Factor(result_data, f"StrengthFilter({signal.name},{strength_threshold})")


def apply_min_holding_period_filter(
    signal: Factor,
    min_holding_hours: int = 8
) -> Factor:
    """
    最小持倉時間過濾器：防止過快反轉
    
    一旦開倉，必須持倉至少 min_holding_hours 小時才能平倉
    
    Parameters
    ----------
    signal : Factor
        原始信號因子
    min_holding_hours : int
        最小持倉時間（小時）
    
    Returns
    -------
    Factor
        過濾後的信號
    """
    result_data = signal.data.copy()
    
    def filter_group(group):
        """對每個資產應用最小持倉時間過濾"""
        values = group['factor'].values
        filtered = values.copy()
        last_position = 0  # 0=無倉位, 1=多倉, -1=空倉
        position_start = None
        
        for i in range(len(values)):
            current_signal = np.sign(values[i])
            
            if current_signal == 0:
                # 無信號
                if last_position != 0:
                    # 檢查是否達到最小持倉時間
                    if position_start is not None and (i - position_start) >= min_holding_hours:
                        filtered[i] = 0  # 可以平倉
                        last_position = 0
                        position_start = None
                    else:
                        filtered[i] = filtered[i-1] if i > 0 else 0  # 維持倉位
                else:
                    filtered[i] = 0
            elif current_signal != last_position:
                # 信號改變
                if last_position == 0:
                    # 開新倉
                    filtered[i] = values[i]
                    last_position = current_signal
                    position_start = i
                else:
                    # 嘗試反轉倉位
                    if position_start is not None and (i - position_start) >= min_holding_hours:
                        filtered[i] = values[i]
                        last_position = current_signal
                        position_start = i
                    else:
                        filtered[i] = filtered[i-1] if i > 0 else 0  # 維持原倉位
            else:
                # 信號相同，維持
                filtered[i] = values[i]
                if position_start is None:
                    position_start = i
        
        return pd.Series(filtered, index=group.index)
    
    # Fix FutureWarning: apply only to 'factor' column
    grouped = result_data.groupby('symbol', group_keys=False)
    result_data['factor'] = pd.concat([
        pd.Series(filter_group(group), index=group.index, name='factor')
        for name, group in grouped
    ]).reindex(result_data.index)
    
    return Factor(result_data, f"MinHoldingFilter({signal.name},{min_holding_hours})")


def apply_cooldown_filter(
    signal: Factor,
    cooldown_hours: int = 4
) -> Factor:
    """
    冷卻期過濾器：平倉後需要等待一段時間才能再次開倉
    
    防止在震盪市場中頻繁開平倉
    
    Parameters
    ----------
    signal : Factor
        原始信號因子
    cooldown_hours : int
        冷卻期（小時）
    
    Returns
    -------
    Factor
        過濾後的信號
    """
    result_data = signal.data.copy()
    
    def filter_group(group):
        """對每個資產應用冷卻期過濾"""
        values = group['factor'].values
        filtered = values.copy()
        last_position = 0
        last_close_time = None
        
        for i in range(len(values)):
            current_signal = np.sign(values[i])
            prev_signal = np.sign(values[i-1]) if i > 0 else 0
            
            # 檢查是否剛平倉
            if last_position != 0 and current_signal == 0 and prev_signal != 0:
                last_close_time = i
            
            # 檢查是否在冷卻期
            if last_close_time is not None and (i - last_close_time) < cooldown_hours:
                if current_signal != 0:
                    filtered[i] = 0  # 冷卻期內禁止開倉
                else:
                    filtered[i] = 0
            else:
                filtered[i] = values[i]
            
            if current_signal != 0:
                last_position = current_signal
        
        return pd.Series(filtered, index=group.index)
    
    # Fix FutureWarning: apply only to 'factor' column
    grouped = result_data.groupby('symbol', group_keys=False)
    result_data['factor'] = pd.concat([
        pd.Series(filter_group(group), index=group.index, name='factor')
        for name, group in grouped
    ]).reindex(result_data.index)
    
    return Factor(result_data, f"CooldownFilter({signal.name},{cooldown_hours})")


def build_alm_strategy_optimized(
    panel_1h: Panel,
    panel_4h: Optional[Panel] = None,
    funding_rates: Optional[Dict[str, Factor]] = None,
    # 原始參數
    ema20: int = 20,
    ema50: int = 50,
    ema200: int = 200,
    donchian_window: int = 20,
    atr_window: int = 14,
    volatility_threshold: float = 0.005,
    funding_long_threshold: float = 0.0005,
    funding_short_threshold: float = -0.0005,
    # 新增：換手率控制參數
    enable_persistence_filter: bool = True,
    persistence_periods: int = 4,
    enable_strength_filter: bool = True,
    strength_threshold: float = 0.5,
    enable_min_holding: bool = True,
    min_holding_hours: int = 8,
    enable_cooldown: bool = True,
    cooldown_hours: int = 4
) -> Factor:
    """
    構建優化版 ALM 策略信號（降低換手率版本）
    
    新增參數說明：
    - enable_persistence_filter: 啟用信號持續性過濾
    - persistence_periods: 信號必須持續的週期數
    - enable_strength_filter: 啟用信號強度過濾
    - strength_threshold: 信號強度閾值
    - enable_min_holding: 啟用最小持倉時間過濾
    - min_holding_hours: 最小持倉時間（小時）
    - enable_cooldown: 啟用冷卻期過濾
    - cooldown_hours: 冷卻期（小時）
    """
    # 先構建基礎策略信號（使用原始函數）
    from .strategy import build_alm_strategy
    
    base_signal = build_alm_strategy(
        panel_1h=panel_1h,
        panel_4h=panel_4h,
        funding_rates=funding_rates,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        donchian_window=donchian_window,
        atr_window=atr_window,
        volatility_threshold=volatility_threshold,
        funding_long_threshold=funding_long_threshold,
        funding_short_threshold=funding_short_threshold
    )
    
    # 應用換手率控制過濾器
    filtered_signal = base_signal
    
    if enable_persistence_filter:
        logger.info(f"應用信號持續性過濾器（{persistence_periods} 週期）")
        filtered_signal = apply_signal_persistence_filter(
            filtered_signal,
            min_periods=persistence_periods,
            method='forward_fill'
        )
    
    if enable_strength_filter:
        logger.info(f"應用信號強度過濾器（閾值 {strength_threshold}）")
        filtered_signal = apply_signal_strength_filter(
            filtered_signal,
            strength_threshold=strength_threshold
        )
    
    if enable_min_holding:
        logger.info(f"應用最小持倉時間過濾器（{min_holding_hours} 小時）")
        filtered_signal = apply_min_holding_period_filter(
            filtered_signal,
            min_holding_hours=min_holding_hours
        )
    
    if enable_cooldown:
        logger.info(f"應用冷卻期過濾器（{cooldown_hours} 小時）")
        filtered_signal = apply_cooldown_filter(
            filtered_signal,
            cooldown_hours=cooldown_hours
        )
    
    filtered_signal.name = f"ALM_Optimized_{filtered_signal.name}"
    
    return filtered_signal

