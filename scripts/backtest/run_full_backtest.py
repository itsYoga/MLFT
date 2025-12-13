"""
完整回測腳本
整合數據獲取、策略信號生成、回測執行和績效分析
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from phandas import *
from strategies.alm import (
    build_alm_strategy,
    build_alm_strategy_improved,
    OKX_TOP_15_ASSETS
)
from core.backtest import run_backtest, resample_panel_to_4h
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_alm_backtest(
    symbols: List[str] = None,
    start_date: str = '2020-01-01',
    end_date: str = '2024-12-31',
    initial_capital: float = 100000.0,
    use_inverse_vol_weighting: bool = True,
    strategy_type: str = 'improved',
    csv_file: Optional[str] = None
):
    """
    運行完整的 ALM 策略回測
    
    參數
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
    strategy_type : str
        策略類型：'base', 'optimized', 'improved'
    csv_file : str, optional
        使用 CSV 文件而非下載數據
    """
    logger.info("=" * 80)
    logger.info("ALM 策略回測開始")
    logger.info("=" * 80)
    
    if symbols is None:
        symbols = OKX_TOP_15_ASSETS[:5]  # 使用前 5 個資產
    
    logger.info(f"資產列表: {symbols}")
    logger.info(f"回測期間: {start_date} 至 {end_date}")
    logger.info(f"初始資金: ${initial_capital:,.2f}")
    logger.info(f"策略類型: {strategy_type}")
    
    # 1. 獲取數據
    logger.info("\n[步驟 1/5] 獲取市場數據...")
    
    if csv_file and os.path.exists(csv_file):
        logger.info(f"從文件加載數據: {csv_file}")
        panel_1h = Panel.from_csv(csv_file)
        panel_4h = panel_1h  # 簡化處理
    else:
        logger.info("從交易所獲取 1H 數據...")
        panel_1h = fetch_data(
            symbols=symbols,
            timeframe='1h',
            start_date=start_date,
            end_date=end_date,
            sources=['binance']
        )
        
        logger.info("從交易所獲取 4H 數據...")
        try:
            panel_4h = fetch_data(
                symbols=symbols,
                timeframe='4h',
                start_date=start_date,
                end_date=end_date,
                sources=['binance']
            )
        except:
            logger.info("4H 數據獲取失敗，從 1H 重採樣...")
            panel_4h = resample_panel_to_4h(panel_1h)
    
    logger.info(f"1H 數據範圍: {panel_1h.data['timestamp'].min()} 至 {panel_1h.data['timestamp'].max()}")
    logger.info(f"1H 數據點數: {len(panel_1h.data)}")
    
    # 2. 構建策略信號
    logger.info("\n[步驟 2/5] 構建策略信號...")
    
    if strategy_type == 'improved':
        strategy_signal = build_alm_strategy_improved(
            panel_1h=panel_1h,
            panel_4h=panel_4h,
            use_weighted_scoring=True,
            signal_threshold=0.6,
            enable_smoothing=True,
            smoothing_window=7,
            min_holding_periods=24,
            enable_adaptive_params=True
        )
    else:
        strategy_signal = build_alm_strategy(
            panel_1h=panel_1h,
            panel_4h=panel_4h
        )
    
    logger.info("策略信號已生成")
    
    # 統計信號
    signal_stats = strategy_signal.data.groupby('symbol')['factor'].agg([
        lambda x: (x > 0).sum(),
        lambda x: (x < 0).sum(),
        lambda x: (x == 0).sum()
    ])
    signal_stats.columns = ['做多', '做空', '無信號']
    logger.info("\n信號統計（每個資產）:")
    logger.info(signal_stats.to_string())
    
    # 3. 執行回測
    logger.info("\n[步驟 3/5] 執行回測...")
    
    bt_results = run_backtest(
        strategy_signal=strategy_signal,
        panel_1h=panel_1h,
        transaction_cost=(0.001, 0.001),
        initial_capital=initial_capital,
        use_inverse_vol_weighting=use_inverse_vol_weighting,
        save_results=False
    )
    
    logger.info("回測完成！")
    
    # 4. 計算績效指標
    logger.info("\n[步驟 4/5] 計算績效指標...")
    bt_results.calculate_metrics(risk_free_rate=0.03)
    
    # 5. 打印摘要
    logger.info("\n[步驟 5/5] 結果摘要")
    logger.info("=" * 80)
    bt_results.print_summary()
    
    logger.info("\n" + "=" * 80)
    logger.info("最大回撤期間（Top 5）")
    logger.info("=" * 80)
    bt_results.print_drawdown_periods(top_n=5)
    
    return bt_results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='運行完整 ALM 策略回測')
    parser.add_argument('--symbols', nargs='+', default=None, help='交易資產列表')
    parser.add_argument('--start-date', default='2023-01-01', help='開始日期')
    parser.add_argument('--end-date', default='2024-01-01', help='結束日期')
    parser.add_argument('--strategy', choices=['base', 'improved'], 
                       default='improved', help='策略類型')
    parser.add_argument('--csv', help='使用 CSV 文件')
    parser.add_argument('--capital', type=float, default=100000.0, help='初始資金')
    parser.add_argument('--plot', action='store_true', help='繪製權益曲線')
    args = parser.parse_args()
    
    bt_results = run_alm_backtest(
        symbols=args.symbols,
        start_date=args.start_date,
        end_date=args.end_date,
        initial_capital=args.capital,
        strategy_type=args.strategy,
        csv_file=args.csv
    )
    
    if args.plot and bt_results:
        logger.info("\n繪製權益曲線...")
        bt_results.plot_equity(figsize=(16, 10), show_summary=True, show_benchmark=True)

