"""
策略模板 - 複製此文件創建新策略

使用步驟：
1. 複製此文件到 strategies/your_strategy/strategy.py
2. 實現 build_your_strategy() 函數
3. 在 strategies/your_strategy/__init__.py 中導出
4. 創建 tests/test_your_strategy.py 測試文件
"""

from typing import Optional
from phandas import *


def build_your_strategy(
    panel_1h: Panel,
    panel_4h: Optional[Panel] = None,
    param1: int = 20,
    param2: float = 0.5,
    **kwargs
) -> Factor:
    """
    構建您的策略信號
    
    Parameters
    ----------
    panel_1h : Panel
        1H 時間框架的數據面板
    panel_4h : Panel, optional
        4H 時間框架的數據面板
    param1 : int
        參數1說明
    param2 : float
        參數2說明
    
    Returns
    -------
    Factor
        策略信號因子（正值表示做多，負值表示做空，0表示無信號）
    """
    # 提取數據
    close_1h = panel_1h['close']
    high_1h = panel_1h['high']
    low_1h = panel_1h['low']
    volume_1h = panel_1h['volume']
    
    # 實現您的策略邏輯
    # 示例：簡單動量策略
    momentum = (close_1h / ts_delay(close_1h, param1)) - 1
    signal = rank(momentum)
    
    # 轉換為交易信號（-1, 0, 1）
    signal_data = close_1h.data.copy()
    signal_data['factor'] = 0.0
    
    # 這裡實現您的信號邏輯
    # signal_data['factor'] = ... 
    
    strategy_signal = Factor(signal_data, "YourStrategy")
    
    return strategy_signal

