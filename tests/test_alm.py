"""
ALM 策略測試
"""

import sys
import os

# 添加項目根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 導入測試函數和策略
from tests.test_strategy_template import test_strategy
from strategies.alm import build_alm_strategy, build_alm_strategy_optimized


def test_alm_base():
    """Test base ALM strategy"""
    return test_strategy(
        strategy_name="ALM Base",
        build_strategy_func=build_alm_strategy,
        symbols=['BTC', 'ETH', 'SOL'],
        start_date='2023-01-01',
        end_date='2024-01-01',
        transaction_cost=0.001
    )


def test_alm_optimized():
    """Test optimized ALM strategy"""
    return test_strategy(
        strategy_name="ALM Optimized",
        build_strategy_func=build_alm_strategy_optimized,
        symbols=['BTC', 'ETH', 'SOL'],
        start_date='2023-01-01',
        end_date='2024-01-01',
        transaction_cost=0.001,
        enable_persistence_filter=True,
        persistence_periods=4,
        enable_strength_filter=True,
        strength_threshold=0.5,
        enable_min_holding=True,
        min_holding_hours=8,
        enable_cooldown=True,
        cooldown_hours=4
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', choices=['base', 'optimized', 'both'], default='both')
    parser.add_argument('--plot', action='store_true', help='Plot equity curve')
    args = parser.parse_args()
    
    if args.type in ['base', 'both']:
        print("\n" + "="*80)
        print("Testing Base ALM Strategy")
        print("="*80)
        bt = test_alm_base()
        if args.plot and bt:
            print("\nPlotting equity curve...")
            bt.plot_equity()
    
    if args.type in ['optimized', 'both']:
        print("\n" + "="*80)
        print("Testing Optimized ALM Strategy")
        print("="*80)
        bt = test_alm_optimized()
        if args.plot and bt:
            print("\nPlotting equity curve...")
            bt.plot_equity()

