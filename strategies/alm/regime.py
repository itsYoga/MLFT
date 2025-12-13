"""
市場狀態檢測模組
整合 CHOP, ADX, ER 進行狀態分類
"""

import numpy as np
import pandas as pd
from phandas import Factor, Panel
from typing import Dict, Optional
from .indicators import choppiness_index, calculate_adx, efficiency_ratio


def detect_regime(
    panel: Panel,
    chop_period: int = 14,
    adx_period: int = 14,
    er_period: int = 20,
    chop_threshold_choppy: float = 61.8,
    chop_threshold_trending: float = 38.2,
    adx_threshold_weak: float = 20,
    adx_threshold_strong: float = 25
) -> Dict[str, Factor]:
    """
    檢測市場狀態
    
    狀態定義：
    - Choppy (震盪): CHOP > 61.8 OR ADX < 20 → 禁止交易
    - Trending (趨勢): CHOP < 50 AND ADX > 25 → 啟用突破邏輯
    - Extreme Trend (極端趨勢): CHOP < 38.2 AND ADX > 50 → 收緊止損
    
    參數
    ----------
    panel : Panel
        數據面板
    chop_period : int
        CHOP 計算週期
    adx_period : int
        ADX 計算週期
    er_period : int
        ER 計算週期
    chop_threshold_choppy : float
        CHOP 震盪閾值
    chop_threshold_trending : float
        CHOP 趨勢閾值
    adx_threshold_weak : float
        ADX 弱趨勢閾值
    adx_threshold_strong : float
        ADX 強趨勢閾值
    
    返回
    -------
    Dict[str, Factor]
        包含各狀態指標的字典
    """
    high = panel['high']
    low = panel['low']
    close = panel['close']
    
    # 計算指標
    chop = choppiness_index(high, low, close, period=chop_period)
    adx = calculate_adx(high, low, close, period=adx_period)
    er = efficiency_ratio(close, period=er_period)
    
    # 狀態分類
    # Choppy: CHOP > threshold OR ADX < threshold
    is_choppy = Factor(
        chop.data.copy().assign(
            factor=(chop.data['factor'] > chop_threshold_choppy) | 
                   (adx.data['factor'] < adx_threshold_weak)
        ),
        "IsChoppy"
    )
    
    # Trending: CHOP < 50 AND ADX > 25
    is_trending = Factor(
        chop.data.copy().assign(
            factor=(chop.data['factor'] < 50) & 
                   (adx.data['factor'] > adx_threshold_strong)
        ),
        "IsTrending"
    )
    
    # Extreme Trend: CHOP < 38.2 AND ADX > 50
    is_extreme_trend = Factor(
        chop.data.copy().assign(
            factor=(chop.data['factor'] < chop_threshold_trending) & 
                   (adx.data['factor'] > 50)
        ),
        "IsExtremeTrend"
    )
    
    # 綜合狀態過濾器（1=可以交易, 0=禁止交易）
    regime_filter = Factor(
        chop.data.copy().assign(
            factor=((chop.data['factor'] < 50) & 
                   (adx.data['factor'] > adx_threshold_strong)).astype(float)
        ),
        "RegimeFilter"
    )
    
    return {
        'chop': chop,
        'adx': adx,
        'er': er,
        'is_choppy': is_choppy,
        'is_trending': is_trending,
        'is_extreme_trend': is_extreme_trend,
        'regime_filter': regime_filter
    }

