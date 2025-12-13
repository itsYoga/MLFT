"""
ALM 策略使用範例
演示如何使用策略模塊進行回測和分析
"""

import logging
from phandas import *
from strategies.alm import (
    OKX_TOP_15_ASSETS,
    build_alm_strategy,
    calculate_4h_trend_filter,
    calculate_donchian_breakout,
    calculate_atr
)
from core.backtest import run_backtest, generate_performance_report

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_basic_backtest():
    """範例 1：基本回測"""
    logger.info("=" * 80)
    logger.info("範例 1：基本回測")
    logger.info("=" * 80)
    
    # 使用前 5 個資產進行快速測試
    test_symbols = OKX_TOP_15_ASSETS[:5]
    
    bt_results = run_alm_backtest(
        symbols=test_symbols,
        start_date='2023-01-01',  # 縮短回測期間以加快速度
        end_date='2024-01-01',
        initial_capital=100000.0,
        use_inverse_vol_weighting=True,
        save_data=True
    )
    
    # 查看結果
    bt_results.print_summary()
    
    return bt_results


def example_2_custom_strategy():
    """範例 2：自定義策略參數"""
    logger.info("=" * 80)
    logger.info("範例 2：自定義策略參數")
    logger.info("=" * 80)
    
    # 獲取數據
    panel_1h = fetch_data(
        symbols=['BTC', 'ETH'],
        timeframe='1h',
        start_date='2023-01-01',
        end_date='2024-01-01',
        sources=['binance']
    )
    
    # 重採樣到 4H
    from core.backtest import resample_panel_to_4h
    panel_4h = resample_panel_to_4h(panel_1h)
    
    # 構建自定義策略
    strategy_signal = build_alm_strategy(
        panel_1h=panel_1h,
        panel_4h=panel_4h,
        ema20=15,  # 更快的 EMA
        ema50=40,
        ema200=180,
        donchian_window=15,  # 更短的突破窗口
        atr_window=10,
        volatility_threshold=0.003  # 更低的波動率閾值
    )
    
    # 統計信號
    signal_stats = strategy_signal.data.groupby('symbol')['factor'].agg([
        lambda x: (x > 0).sum(),
        lambda x: (x < 0).sum(),
        lambda x: (x == 0).sum()
    ])
    signal_stats.columns = ['Long', 'Short', 'Neutral']
    
    logger.info("\n自定義策略信號統計:")
    logger.info(signal_stats.to_string())
    
    return strategy_signal


def example_3_individual_components():
    """範例 3：單獨使用策略組件"""
    logger.info("=" * 80)
    logger.info("範例 3：單獨使用策略組件")
    logger.info("=" * 80)
    
    # 獲取數據
    panel_1h = fetch_data(
        symbols=['BTC'],
        timeframe='1h',
        start_date='2023-01-01',
        end_date='2024-01-01',
        sources=['binance']
    )
    
    close_1h = panel_1h['close']
    high_1h = panel_1h['high']
    low_1h = panel_1h['low']
    
    # 1. 計算 ATR
    atr = calculate_atr(high_1h, low_1h, close_1h, window=14)
    logger.info("ATR 計算完成")
    
    # 2. 計算 Donchian Breakout
    long_signal, short_signal = calculate_donchian_breakout(
        close_1h, high_1h, low_1h, window=20
    )
    logger.info("Donchian Breakout 計算完成")
    
    # 統計突破信號
    long_count = (long_signal.data['factor'] > 0).sum()
    short_count = (short_signal.data['factor'] > 0).sum()
    
    logger.info(f"做多突破信號數: {long_count}")
    logger.info(f"做空突破信號數: {short_count}")
    
    return atr, long_signal, short_signal


def example_4_performance_analysis():
    """範例 4：詳細績效分析"""
    logger.info("=" * 80)
    logger.info("範例 4：詳細績效分析")
    logger.info("=" * 80)
    
    # 運行回測
    bt_results = run_alm_backtest(
        symbols=OKX_TOP_15_ASSETS[:3],  # 使用前 3 個資產
        start_date='2023-01-01',
        end_date='2024-01-01',
        initial_capital=100000.0,
        use_inverse_vol_weighting=True
    )
    
    # 生成詳細報告
    report = generate_performance_report(bt_results)
    logger.info("\n" + report)
    
    # 獲取交易日誌
    trade_log = bt_results.portfolio.get_trade_log_df()
    if not trade_log.empty:
        logger.info(f"\n總交易次數: {len(trade_log)}")
        logger.info(f"總交易成本: ${trade_log['cost'].sum():.2f}")
    
    # 獲取權益曲線
    equity_curve = bt_results.portfolio.get_history_df()
    logger.info(f"\n最終權益: ${equity_curve['total_value'].iloc[-1]:,.2f}")
    logger.info(f"最大權益: ${equity_curve['total_value'].max():,.2f}")
    
    return bt_results


if __name__ == "__main__":
    import sys
    
    # 選擇要運行的範例
    if len(sys.argv) > 1:
        example_num = int(sys.argv[1])
    else:
        example_num = 1
    
    examples = {
        1: example_1_basic_backtest,
        2: example_2_custom_strategy,
        3: example_3_individual_components,
        4: example_4_performance_analysis
    }
    
    if example_num in examples:
        logger.info(f"\n運行範例 {example_num}...\n")
        result = examples[example_num]()
        logger.info(f"\n範例 {example_num} 完成！")
    else:
        logger.error(f"無效的範例編號: {example_num}")
        logger.info("可用範例: 1, 2, 3, 4")
        logger.info("\n使用方法:")
        logger.info("  python example_alm.py 1  # 基本回測")
        logger.info("  python example_alm.py 2  # 自定義策略")
        logger.info("  python example_alm.py 3  # 單獨組件")
        logger.info("  python example_alm.py 4  # 績效分析")

