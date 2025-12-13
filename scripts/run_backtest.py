"""
統一回測腳本 - 支持多個策略
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from phandas import *
from core.backtest import run_backtest, resample_panel_to_4h
from strategies.alm import build_alm_strategy, build_alm_strategy_optimized, OKX_TOP_15_ASSETS


def main():
    parser = argparse.ArgumentParser(description='運行策略回測')
    parser.add_argument('--strategy', type=str, default='alm', choices=['alm', 'alm_optimized'],
                       help='策略名稱')
    parser.add_argument('--symbols', type=str, nargs='+', default=None,
                       help='交易資產列表')
    parser.add_argument('--start-date', type=str, default='2023-01-01',
                       help='開始日期')
    parser.add_argument('--end-date', type=str, default='2024-01-01',
                       help='結束日期')
    parser.add_argument('--capital', type=float, default=100000.0,
                       help='初始資金')
    parser.add_argument('--cost', type=float, default=0.001,
                       help='交易成本')
    parser.add_argument('--optimized', action='store_true',
                       help='使用優化策略（降低換手率）')
    
    args = parser.parse_args()
    
    # 確定資產列表
    symbols = args.symbols if args.symbols else OKX_TOP_15_ASSETS[:5]
    
    print(f"Strategy: {args.strategy}")
    print(f"Symbols: {symbols}")
    print(f"Period: {args.start_date} to {args.end_date}")
    print(f"Transaction Cost: {args.cost*100:.2f}%")
    print()
    
    # Fetch data
    print("Fetching data...")
    panel_1h = fetch_data(
        symbols=symbols,
        timeframe='1h',
        start_date=args.start_date,
        end_date=args.end_date,
        sources=['binance']
    )
    
    try:
        panel_4h = fetch_data(
            symbols=symbols,
            timeframe='4h',
            start_date=args.start_date,
            end_date=args.end_date,
            sources=['binance']
        )
    except:
        print("從 1H 重採樣到 4H...")
        panel_4h = resample_panel_to_4h(panel_1h)
    
    # Build strategy
    print("Building strategy signal...")
    if args.optimized or args.strategy == 'alm_optimized':
        strategy_signal = build_alm_strategy_optimized(
            panel_1h=panel_1h,
            panel_4h=panel_4h,
            enable_persistence_filter=True,
            enable_strength_filter=True,
            enable_min_holding=True,
            enable_cooldown=True
        )
    else:
        strategy_signal = build_alm_strategy(
            panel_1h=panel_1h,
            panel_4h=panel_4h
        )
    
    # Run backtest
    print("Running backtest...")
    bt_results = run_backtest(
        strategy_signal=strategy_signal,
        panel_1h=panel_1h,
        transaction_cost=(args.cost, args.cost),
        initial_capital=args.capital,
        use_inverse_vol_weighting=True
    )
    
    # Display results
    print()
    bt_results.print_summary()
    print()
    bt_results.print_drawdown_periods(top_n=5)
    
    # Plot equity curve (this generates the chart/image)
    print("\nPlotting equity curve...")
    bt_results.plot_equity(figsize=(16, 10), show_summary=True, show_benchmark=True)


if __name__ == "__main__":
    main()

