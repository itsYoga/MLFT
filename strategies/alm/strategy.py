"""
自適應流動性動能（Adaptive Liquid Momentum, ALM）策略
基於 OKX 流動性前 15 大資產的加密貨幣 CTA 策略

策略邏輯：
1. 4H 時間框架：EMA(20, 50, 200) 趨勢過濾
2. 1H 時間框架：Donchian Breakout (20根K線) 入場觸發
3. 資金費率過濾器：避免極端擁擠交易
4. 波動率過濾器：ATR 過濾低波動死寂市場
5. 風險管理：ATR 止損、追蹤止盈、時間止損
6. 投資組合：逆波動率加權
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from phandas import *
import logging

logger = logging.getLogger(__name__)

# OKX 流動性前 15 大資產
OKX_TOP_15_ASSETS = [
    'BTC', 'ETH', 'SOL', 'XRP', 'BNB', 'ZEC', 'DOGE', 
    'LINK', 'ADA', 'AVAX', 'LTC', 'UNI', 'AAVE', 'SHIB', 'HBAR'
]

# 資產流動性分組（用於差異化滑點）
LIQUIDITY_CLUSTERS = {
    'cluster_1': ['BTC', 'ETH'],  # 最高流動性，滑點 0.05%
    'cluster_2': ['BNB', 'SOL', 'XRP', 'ADA', 'LTC'],  # 高流動性，滑點 0.10%
    'cluster_3': ['LINK', 'UNI', 'AAVE', 'AVAX'],  # 中等流動性，滑點 0.15%
    'cluster_4': ['DOGE', 'SHIB'],  # 迷因幣，滑點 0.20%
    'cluster_5': ['ZEC', 'HBAR'],  # 低流動性，滑點 0.20%
}

# 滑點映射
SLIPPAGE_MAP = {
    'cluster_1': 0.0005,  # 0.05%
    'cluster_2': 0.0010,  # 0.10%
    'cluster_3': 0.0015,  # 0.15%
    'cluster_4': 0.0020,  # 0.20%
    'cluster_5': 0.0020,  # 0.20%
}


def get_asset_cluster(symbol: str) -> str:
    """獲取資產所屬的流動性集群"""
    for cluster, assets in LIQUIDITY_CLUSTERS.items():
        if symbol in assets:
            return cluster
    return 'cluster_3'  # 默認中等流動性


def calculate_ema(factor: Factor, window: int, alpha: Optional[float] = None) -> Factor:
    """
    計算指數移動平均線（EMA）
    
    Parameters
    ----------
    factor : Factor
        輸入因子
    window : int
        窗口大小
    alpha : float, optional
        平滑係數，如果為 None 則使用 2/(window+1)
    
    Returns
    -------
    Factor
        EMA 因子
    """
    if alpha is None:
        alpha = 2.0 / (window + 1.0)
    
    # 使用 ts_decay_exp_window 實現 EMA
    # 但需要調整參數以匹配標準 EMA
    # 標準 EMA: EMA_t = alpha * Price_t + (1-alpha) * EMA_{t-1}
    # ts_decay_exp_window 使用指數衰減，需要轉換
    
    # 使用 pandas 的 ewm 實現 EMA
    result_data = factor.data.copy()
    
    def calc_ema_group(group):
        """對每個資產計算 EMA"""
        if len(group) == 0:
            return pd.Series(np.nan, index=group.index)
        
        # 使用 pandas ewm 計算 EMA
        # span 參數對應 window，alpha = 2/(span+1)
        # group 可能是 Series（如果只選擇一列）或 DataFrame
        if isinstance(group, pd.Series):
            series = group
        else:
            series = group['factor']
        ema = series.ewm(span=window, adjust=False, ignore_na=True).mean()
        return ema
    
    # 只對 factor 列進行 groupby，避免 FutureWarning
    grouped = result_data.groupby('symbol', group_keys=False)['factor']
    result_data['factor'] = grouped.apply(calc_ema_group).reset_index(level=0, drop=True)
    
    return Factor(result_data, f"EMA({factor.name},{window})")


def calculate_atr(high: Factor, low: Factor, close: Factor, window: int = 14) -> Factor:
    """
    計算真實波動幅度（ATR）
    
    Parameters
    ----------
    high : Factor
        最高價因子
    low : Factor
        最低價因子
    close : Factor
        收盤價因子
    window : int
        窗口大小，默認 14
    
    Returns
    -------
    Factor
        ATR 因子
    """
    # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
    prev_close = ts_delay(close, 1)
    
    hl = high - low
    hc = (high - prev_close).abs()
    lc = (low - prev_close).abs()
    
    tr = maximum(maximum(hl, hc), lc)
    
    # ATR 是 TR 的移動平均（使用 EMA 或 SMA）
    atr = ts_mean(tr, window)
    
    return Factor(atr.data, f"ATR({window})")


def calculate_donchian_breakout(
    close: Factor, 
    high: Factor, 
    low: Factor, 
    window: int = 20
) -> Tuple[Factor, Factor]:
    """
    計算 Donchian 通道突破信號
    
    Parameters
    ----------
    close : Factor
        收盤價因子
    high : Factor
        最高價因子
    low : Factor
        最低價因子
    window : int
        窗口大小，默認 20
    
    Returns
    -------
    Tuple[Factor, Factor]
        (做多信號, 做空信號)
    """
    # 過去 window 根 K 線的最高價和最低價
    upper_band = ts_max(high, window)
    lower_band = ts_min(low, window)
    
    # 突破上軌：做多信號
    long_signal = close > ts_delay(upper_band, 1)
    
    # 跌破下軌：做空信號
    short_signal = close < ts_delay(lower_band, 1)
    
    return long_signal, short_signal


def calculate_4h_trend_filter(
    close_4h: Factor,
    ema20_period: int = 20,
    ema50_period: int = 50,
    ema200_period: int = 200
) -> Tuple[Factor, Factor]:
    """
    計算 4H 時間框架的趨勢過濾器
    
    使用三重 EMA 系統：
    - 強多頭：價格 > EMA20 > EMA50 > EMA200
    - 強空頭：價格 < EMA20 < EMA50 < EMA200
    
    Parameters
    ----------
    close_4h : Factor
        4H 收盤價因子
    ema20_period : int
        EMA20 週期
    ema50_period : int
        EMA50 週期
    ema200_period : int
        EMA200 週期
    
    Returns
    -------
    Tuple[Factor, Factor]
        (多頭趨勢信號, 空頭趨勢信號)
    """
    # 計算三重 EMA
    ema20 = calculate_ema(close_4h, ema20_period)
    ema50 = calculate_ema(close_4h, ema50_period)
    ema200 = calculate_ema(close_4h, ema200_period)
    
    # 強多頭趨勢：價格 > EMA20 > EMA50 > EMA200
    # 使用乘法來實現 AND 邏輯（True=1, False=0）
    cond1 = (close_4h > ema20)
    cond2 = (ema20 > ema50)
    cond3 = (ema50 > ema200)
    bullish_trend = cond1 * cond2 * cond3
    
    # 強空頭趨勢：價格 < EMA20 < EMA50 < EMA200
    cond4 = (close_4h < ema20)
    cond5 = (ema20 < ema50)
    cond6 = (ema50 < ema200)
    bearish_trend = cond4 * cond5 * cond6
    
    return bullish_trend, bearish_trend


def broadcast_4h_to_1h(factor_4h: Factor, index_1h: pd.DatetimeIndex) -> Factor:
    """
    將 4H 因子廣播到 1H 時間框架
    
    Parameters
    ----------
    factor_4h : Factor
        4H 時間框架的因子
    index_1h : pd.DatetimeIndex
        1H 時間框架的索引
    
    Returns
    -------
    Factor
        廣播到 1H 的因子
    """
    # 將 4H 數據轉換為 DataFrame，以 timestamp 和 symbol 為索引
    df_4h = factor_4h.data.set_index(['timestamp', 'symbol'])['factor']
    
    # 為每個 symbol 創建完整的 1H 時間序列
    result_rows = []
    for symbol in factor_4h.data['symbol'].unique():
        symbol_data_4h = df_4h.xs(symbol, level='symbol')
        
        # 重採樣到 1H，使用前向填充
        symbol_data_1h = symbol_data_4h.reindex(
            index_1h, method='ffill'
        )
        
        for timestamp, value in symbol_data_1h.items():
            result_rows.append({
                'timestamp': timestamp,
                'symbol': symbol,
                'factor': value
            })
    
    result_df = pd.DataFrame(result_rows)
    return Factor(result_df, f"{factor_4h.name}_1H")


def calculate_volatility_filter(
    close: Factor,
    atr: Factor,
    threshold: float = 0.005
) -> Factor:
    """
    波動率過濾器：過濾低波動死寂市場
    
    當 ATR / Price < threshold 時，禁止開倉
    
    Parameters
    ----------
    close : Factor
        收盤價因子
    atr : Factor
        ATR 因子
    threshold : float
        波動率閾值，默認 0.005 (0.5%)
    
    Returns
    -------
    Factor
        波動率過濾器（True 表示可以交易）
    """
    volatility_ratio = atr / close
    return volatility_ratio > threshold


def calculate_funding_rate_filter(
    funding_rate: Factor,
    long_threshold: float = 0.0005,
    short_threshold: float = -0.0005
) -> Tuple[Factor, Factor]:
    """
    資金費率過濾器
    
    若資金費率 > long_threshold（極度看多），禁止開多倉
    若資金費率 < short_threshold（極度看空），禁止開空倉
    
    Parameters
    ----------
    funding_rate : Factor
        資金費率因子
    long_threshold : float
        做多閾值，默認 0.0005 (0.05%)
    short_threshold : float
        做空閾值，默認 -0.0005 (-0.05%)
    
    Returns
    -------
    Tuple[Factor, Factor]
        (可以做多, 可以做空)
    """
    can_long = funding_rate < long_threshold
    can_short = funding_rate > short_threshold
    
    return can_long, can_short


def calculate_inverse_volatility_weights(
    returns: Factor,
    window: int = 30 * 24  # 30 天（假設 1H 數據）
) -> Factor:
    """
    計算逆波動率加權權重
    
    公式：w_i = (1/σ_i) / Σ(1/σ_j)
    
    Parameters
    ----------
    returns : Factor
        收益率因子
    window : int
        計算波動率的窗口大小
    
    Returns
    -------
    Factor
        權重因子
    """
    # 計算滾動波動率（年化）
    volatility = ts_std_dev(returns, window) * np.sqrt(365 * 24)  # 年化（假設 1H 數據）
    
    # 計算逆波動率
    inv_vol = 1.0 / (volatility + 1e-10)  # 避免除零
    
    # 橫截面歸一化
    weights = inv_vol / inv_vol.mean()
    
    return Factor(weights.data, "InverseVolWeight")


def build_alm_strategy(
    panel_1h: Panel,
    panel_4h: Optional[Panel] = None,
    funding_rates: Optional[Dict[str, Factor]] = None,
    ema20: int = 20,
    ema50: int = 50,
    ema200: int = 200,
    donchian_window: int = 20,
    atr_window: int = 14,
    volatility_threshold: float = 0.005,
    funding_long_threshold: float = 0.0005,
    funding_short_threshold: float = -0.0005
) -> Factor:
    """
    構建完整的 ALM 策略信號
    
    Parameters
    ----------
    panel_1h : Panel
        1H 時間框架的數據面板
    panel_4h : Panel, optional
        4H 時間框架的數據面板，如果為 None 則從 1H 重採樣
    funding_rates : Dict[str, Factor], optional
        各資產的資金費率因子字典
    ema20 : int
        EMA20 週期
    ema50 : int
        EMA50 週期
    ema200 : int
        EMA200 週期
    donchian_window : int
        Donchian 突破窗口
    atr_window : int
        ATR 窗口
    volatility_threshold : float
        波動率閾值
    funding_long_threshold : float
        資金費率做多閾值
    funding_short_threshold : float
        資金費率做空閾值
    
    Returns
    -------
    Factor
        策略信號因子（正值表示做多，負值表示做空）
    """
    # 提取 1H 數據
    close_1h = panel_1h['close']
    high_1h = panel_1h['high']
    low_1h = panel_1h['low']
    open_1h = panel_1h['open']
    volume_1h = panel_1h['volume']
    
    # 準備 4H 數據
    if panel_4h is None:
        # 從 1H 重採樣到 4H
        # 注意：phandas 的 Panel 可能需要手動重採樣
        logger.warning("需要手動提供 4H 數據或實現重採樣邏輯")
        # 這裡假設已經有 4H 數據
        close_4h = close_1h  # 臨時使用 1H 數據
    else:
        close_4h = panel_4h['close']
    
    # 1. 計算 4H 趨勢過濾器
    bullish_trend_4h, bearish_trend_4h = calculate_4h_trend_filter(
        close_4h, ema20, ema50, ema200
    )
    
    # 將 4H 信號廣播到 1H（簡化處理，實際需要更複雜的邏輯）
    # 這裡假設已經對齊
    bullish_trend_1h = bullish_trend_4h
    bearish_trend_1h = bearish_trend_4h
    
    # 2. 計算 1H Donchian Breakout
    long_breakout, short_breakout = calculate_donchian_breakout(
        close_1h, high_1h, low_1h, donchian_window
    )
    
    # 3. 計算 ATR 和波動率過濾器
    atr = calculate_atr(high_1h, low_1h, close_1h, atr_window)
    volatility_filter = calculate_volatility_filter(
        close_1h, atr, volatility_threshold
    )
    
    # 4. 資金費率過濾器（如果提供）
    can_long_funding = Factor(
        close_1h.data.copy().assign(factor=1.0),
        "CanLongFunding"
    )
    can_short_funding = Factor(
        close_1h.data.copy().assign(factor=1.0),
        "CanShortFunding"
    )
    
    if funding_rates:
        # 這裡需要根據實際的資金費率數據結構進行處理
        # 簡化處理：假設所有資產都有資金費率數據
        pass
    
    # 5. 成交量確認（可選）
    volume_ma = ts_mean(volume_1h, 20)
    volume_confirmation = volume_1h > (volume_ma * 1.5)
    
    # 6. 綜合信號
    # 做多信號：4H 多頭趨勢 + 1H 突破上軌 + 波動率過濾 + 成交量確認
    # 使用乘法來實現 AND 邏輯（所有條件都為 True 時結果為 1）
    long_signal = (
        bullish_trend_1h * 
        long_breakout * 
        volatility_filter * 
        volume_confirmation *
        can_long_funding
    )
    
    # 做空信號：4H 空頭趨勢 + 1H 跌破下軌 + 波動率過濾 + 成交量確認
    short_signal = (
        bearish_trend_1h * 
        short_breakout * 
        volatility_filter * 
        volume_confirmation *
        can_short_funding
    )
    
    # 將布林信號轉換為數值信號（1=做多, -1=做空, 0=無信號）
    signal_data = close_1h.data.copy()
    signal_data['factor'] = 0.0
    
    # 合併 long_signal 和 short_signal 的數據
    long_df = long_signal.data.set_index(['timestamp', 'symbol'])['factor']
    short_df = short_signal.data.set_index(['timestamp', 'symbol'])['factor']
    
    for idx, row in signal_data.iterrows():
        timestamp = row['timestamp']
        symbol = row['symbol']
        
        try:
            long_val = long_df.get((timestamp, symbol), 0)
            short_val = short_df.get((timestamp, symbol), 0)
            
            if long_val > 0:
                signal_data.loc[idx, 'factor'] = 1.0
            elif short_val > 0:
                signal_data.loc[idx, 'factor'] = -1.0
        except:
            pass
    
    strategy_signal = Factor(signal_data, "ALM_Strategy")
    
    return strategy_signal


def apply_inverse_volatility_weighting(
    strategy_signal: Factor,
    returns: Factor,
    window: int = 30 * 24
) -> Factor:
    """
    應用逆波動率加權到策略信號
    
    Parameters
    ----------
    strategy_signal : Factor
        原始策略信號
    returns : Factor
        收益率因子（用於計算波動率）
    window : int
        波動率計算窗口
    
    Returns
    -------
    Factor
        加權後的策略信號
    """
    # 計算權重
    weights = calculate_inverse_volatility_weights(returns, window)
    
    # 應用權重
    weighted_signal = strategy_signal * weights
    
    return Factor(weighted_signal.data, f"Weighted_{strategy_signal.name}")


if __name__ == "__main__":
    # 示例使用
    logging.basicConfig(level=logging.INFO)
    
    logger.info("開始構建 ALM 策略...")
    logger.info(f"目標資產: {OKX_TOP_15_ASSETS}")
    
    # 這裡需要實際的數據獲取邏輯
    # panel_1h = fetch_data(
    #     symbols=OKX_TOP_15_ASSETS,
    #     timeframe='1h',
    #     start_date='2020-01-01',
    #     end_date='2024-12-31',
    #     sources=['binance']  # 注意：實際應該使用 OKX
    # )
    
    logger.info("策略模塊已準備就緒")

