"""
ALM 策略完整回測腳本
整合數據獲取、策略信號生成、回測執行和績效分析
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, List, Optional
from phandas import *
from strategies.alm import (
    build_alm_strategy,
    apply_inverse_volatility_weighting,
    calculate_atr,
    OKX_TOP_15_ASSETS,
    get_asset_cluster,
    SLIPPAGE_MAP
)
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def resample_panel_to_4h(panel_1h: Panel) -> Panel:
    """
    將 1H Panel 重採樣為 4H Panel
    
    注意：如果可以直接獲取 4H 數據，建議使用 fetch_data(timeframe='4h')
    
    Parameters
    ----------
    panel_1h : Panel
        1H 時間框架的 Panel
    
    Returns
    -------
    Panel
        4H 時間框架的 Panel
    """
    df_1h = panel_1h.data.copy()
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
    df_1h = df_1h.set_index('timestamp')
    
    # 對每個 symbol 重採樣
    resampled_dfs = []
    
    for symbol in df_1h['symbol'].unique():
        symbol_data = df_1h[df_1h['symbol'] == symbol].copy()
        
        # 重採樣到 4H
        resampled = symbol_data.resample('4H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'symbol': 'first'
        })
        
        resampled_dfs.append(resampled)
    
    df_4h = pd.concat(resampled_dfs).reset_index()
    df_4h = df_4h.sort_values(['symbol', 'timestamp']).reset_index(drop=True)
    
    return Panel(df_4h)


def calculate_dynamic_slippage(
    symbol: str,
    base_slippage: float = 0.001
) -> float:
    """
    計算動態滑點（基於資產流動性）
    
    Parameters
    ----------
    symbol : str
        資產符號
    base_slippage : float
        基礎滑點率
    
    Returns
    -------
    float
        滑點率
    """
    cluster = get_asset_cluster(symbol)
    return SLIPPAGE_MAP.get(cluster, base_slippage)


def run_alm_backtest(
    symbols: List[str] = OKX_TOP_15_ASSETS,
    start_date: str = '2020-01-01',
    end_date: str = '2024-12-31',
    initial_capital: float = 100000.0,
    use_inverse_vol_weighting: bool = True,
    save_data: bool = True,
    data_path_1h: Optional[str] = None,
    data_path_4h: Optional[str] = None
) -> Backtester:
    """
    運行完整的 ALM 策略回測
    
    Parameters
    ----------
    symbols : List[str]
        交易資產列表
    start_date : str
        開始日期
    end_date : str
        結束日期
    initial_capital : float
        初始資金
    use_inverse_vol_weighting : bool
        是否使用逆波動率加權
    save_data : bool
        是否保存數據
    data_path_1h : str, optional
        1H 數據保存路徑
    data_path_4h : str, optional
        4H 數據保存路徑
    
    Returns
    -------
    Backtester
        回測結果對象
    """
    logger.info("=" * 80)
    logger.info("ALM 策略回測開始")
    logger.info("=" * 80)
    logger.info(f"資產列表: {symbols}")
    logger.info(f"回測期間: {start_date} 至 {end_date}")
    logger.info(f"初始資金: ${initial_capital:,.2f}")
    
    # 1. 獲取數據
    logger.info("\n[步驟 1/6] 獲取市場數據...")
    
    if data_path_1h and os.path.exists(data_path_1h):
        logger.info(f"從文件加載 1H 數據: {data_path_1h}")
        panel_1h = Panel.from_csv(data_path_1h)
    else:
        logger.info("從交易所獲取 1H 數據...")
        panel_1h = fetch_data(
            symbols=symbols,
            timeframe='1h',
            start_date=start_date,
            end_date=end_date,
            sources=['binance']  # 注意：實際應使用 OKX
        )
        
        if save_data and data_path_1h:
            panel_1h.to_csv(data_path_1h)
            logger.info(f"1H 數據已保存至: {data_path_1h}")
    
    logger.info(f"1H 數據範圍: {panel_1h.data['timestamp'].min()} 至 {panel_1h.data['timestamp'].max()}")
    logger.info(f"1H 數據點數: {len(panel_1h.data)}")
    
    # 2. 獲取 4H 數據
    logger.info("\n[步驟 2/6] 獲取 4H 時間框架數據...")
    
    if data_path_4h and os.path.exists(data_path_4h):
        logger.info(f"從文件加載 4H 數據: {data_path_4h}")
        panel_4h = Panel.from_csv(data_path_4h)
    else:
        # 優先嘗試直接獲取 4H 數據（phandas 支持）
        try:
            logger.info("直接從交易所獲取 4H 數據...")
            panel_4h = fetch_data(
                symbols=symbols,
                timeframe='4h',  # phandas 支持 '4h' 時間框架
                start_date=start_date,
                end_date=end_date,
                sources=['binance']  # 注意：實際應使用 OKX
            )
            logger.info("成功獲取 4H 數據")
        except Exception as e:
            logger.warning(f"無法直接獲取 4H 數據: {e}")
            logger.info("從 1H 數據重採樣到 4H...")
            panel_4h = resample_panel_to_4h(panel_1h)
        
        if save_data and data_path_4h:
            panel_4h.to_csv(data_path_4h)
            logger.info(f"4H 數據已保存至: {data_path_4h}")
    
    logger.info(f"4H 數據範圍: {panel_4h.data['timestamp'].min()} 至 {panel_4h.data['timestamp'].max()}")
    logger.info(f"4H 數據點數: {len(panel_4h.data)}")
    
    # 3. 構建策略信號
    logger.info("\n[步驟 3/6] 構建策略信號...")
    
    strategy_signal = build_alm_strategy(
        panel_1h=panel_1h,
        panel_4h=panel_4h,
        funding_rates=None,  # 資金費率數據需要單獨獲取
        ema20=20,
        ema50=50,
        ema200=200,
        donchian_window=20,
        atr_window=14,
        volatility_threshold=0.005,
        funding_long_threshold=0.0005,
        funding_short_threshold=-0.0005
    )
    
    logger.info("策略信號已生成")
    
    # 統計信號
    signal_stats = strategy_signal.data.groupby('symbol')['factor'].agg([
        lambda x: (x > 0).sum(),  # 做多信號數
        lambda x: (x < 0).sum(),  # 做空信號數
        lambda x: (x == 0).sum()  # 無信號數
    ])
    signal_stats.columns = ['Long', 'Short', 'Neutral']
    logger.info("\n信號統計（每個資產）:")
    logger.info(signal_stats.to_string())
    
    # 4. 應用逆波動率加權（可選）
    if use_inverse_vol_weighting:
        logger.info("\n[步驟 4/6] 應用逆波動率加權...")
        
        close_1h = panel_1h['close']
        returns = close_1h / ts_delay(close_1h, 1) - 1
        
        strategy_signal = apply_inverse_volatility_weighting(
            strategy_signal=strategy_signal,
            returns=returns,
            window=30 * 24  # 30 天
        )
        
        logger.info("逆波動率加權已應用")
    
    # 5. 準備回測價格因子
    logger.info("\n[步驟 5/6] 準備回測參數...")
    
    entry_price = panel_1h['open']  # 使用開盤價作為入場價格
    
    # 計算動態交易成本（手續費 + 滑點）
    # 這裡簡化處理，使用平均滑點
    avg_slippage = np.mean(list(SLIPPAGE_MAP.values()))
    taker_fee = 0.001  # 0.1% (OKX 普通用戶)
    
    total_cost = taker_fee + avg_slippage
    transaction_cost = (total_cost, total_cost)  # (買入成本, 賣出成本)
    
    logger.info(f"交易成本: {transaction_cost[0]:.4%} (手續費 {taker_fee:.4%} + 滑點 {avg_slippage:.4%})")
    
    # 6. 執行回測
    logger.info("\n[步驟 6/6] 執行回測...")
    
    bt_results = backtest(
        entry_price_factor=entry_price,
        strategy_factor=strategy_signal,
        transaction_cost=transaction_cost,
        initial_capital=initial_capital,
        full_rebalance=False,  # 增量調整而非完全再平衡
        neutralization="market",  # 市場中性
        auto_run=True
    )
    
    logger.info("回測完成！")
    
    # 7. 計算績效指標
    logger.info("\n計算績效指標...")
    bt_results.calculate_metrics(risk_free_rate=0.03)
    
    # 8. 打印摘要
    logger.info("\n" + "=" * 80)
    logger.info("回測結果摘要")
    logger.info("=" * 80)
    bt_results.print_summary()
    
    logger.info("\n" + "=" * 80)
    logger.info("最大回撤期間（Top 5）")
    logger.info("=" * 80)
    bt_results.print_drawdown_periods(top_n=5)
    
    return bt_results


def generate_performance_report(
    bt_results: Backtester,
    output_path: Optional[str] = None
) -> str:
    """
    生成詳細的績效報告
    
    Parameters
    ----------
    bt_results : Backtester
        回測結果對象
    output_path : str, optional
        報告保存路徑
    
    Returns
    -------
    str
        報告內容
    """
    metrics = bt_results.metrics
    history_df = bt_results.portfolio.get_history_df()
    
    report_lines = [
        "=" * 80,
        "ALM 策略績效報告",
        "=" * 80,
        "",
        f"策略名稱: {bt_results.strategy_factor.name}",
        f"回測期間: {history_df.index[0].strftime('%Y-%m-%d')} 至 {history_df.index[-1].strftime('%Y-%m-%d')}",
        "",
        "【收益指標】",
        f"總收益率: {metrics.get('total_return', 0):.2%}",
        f"年化收益率: {metrics.get('annual_return', 0):.2%}",
        "",
        "【風險指標】",
        f"年化波動率: {metrics.get('annual_volatility', 0):.2%}",
        f"最大回撤: {metrics.get('max_drawdown', 0):.2%}",
        f"VaR (95%): {metrics.get('var_95', 0):.2%}",
        f"CVaR: {metrics.get('cvar', 0):.2%}",
        "",
        "【風險調整後收益】",
        f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}",
        f"索提諾比率: {metrics.get('sortino_ratio', 0):.2f}",
        f"卡爾瑪比率: {metrics.get('calmar_ratio', 0):.2f}",
        f"線性度: {metrics.get('linearity', 0):.4f}",
        "",
        "【回撤分析】",
    ]
    
    drawdown_periods = metrics.get('drawdown_periods', [])
    if drawdown_periods:
        report_lines.append("Top 5 最大回撤期間:")
        for i, period in enumerate(drawdown_periods[:5], 1):
            report_lines.append(
                f"  {i}. {period['start']} → {period['end']} | "
                f"深度: {period['depth']:.2%} | "
                f"持續: {period['duration_days']} 天"
            )
    else:
        report_lines.append("  無顯著回撤期間")
    
    report_lines.extend([
        "",
        "=" * 80,
        "報告結束",
        "=" * 80
    ])
    
    report = "\n".join(report_lines)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"績效報告已保存至: {output_path}")
    
    return report


if __name__ == "__main__":
    import os
    
    # 設置數據保存路徑
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    
    data_path_1h = os.path.join(data_dir, "alm_data_1h.csv")
    data_path_4h = os.path.join(data_dir, "alm_data_4h.csv")
    
    # 運行回測
    bt_results = run_alm_backtest(
        symbols=OKX_TOP_15_ASSETS,
        start_date='2020-01-01',
        end_date='2024-12-31',
        initial_capital=100000.0,
        use_inverse_vol_weighting=True,
        save_data=True,
        data_path_1h=data_path_1h,
        data_path_4h=data_path_4h
    )
    
    # 生成報告
    report_path = os.path.join(data_dir, "alm_performance_report.txt")
    report = generate_performance_report(bt_results, output_path=report_path)
    print("\n" + report)
    
    # Plot equity curve (this generates the chart/image)
    logger.info("\nPlotting equity curve...")
    bt_results.plot_equity(figsize=(16, 10), show_summary=True, show_benchmark=True)

