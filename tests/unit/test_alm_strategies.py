"""
ALM 策略單元測試
測試所有策略版本（基礎版、優化版、改進版）
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tests.integration.test_strategy_template import test_strategy
from strategies.alm import build_alm_strategy, build_alm_strategy_optimized, build_alm_strategy_improved


def test_alm_base():
    """測試基礎 ALM 策略"""
    return test_strategy(
        strategy_name="ALM Base",
        build_strategy_func=build_alm_strategy,
        symbols=['BTC', 'ETH', 'SOL'],
        start_date='2023-01-01',
        end_date='2024-01-01',
        transaction_cost=0.001
    )


def test_alm_optimized():
    """測試優化版 ALM 策略"""
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


def test_alm_improved():
    """測試改進版 ALM 策略（推薦配置）"""
    return test_strategy(
        strategy_name="ALM Improved",
        build_strategy_func=build_alm_strategy_improved,
        symbols=['BTC', 'ETH', 'SOL'],
        start_date='2023-01-01',
        end_date='2024-01-01',
        transaction_cost=0.001,
        use_weighted_scoring=True,
        signal_threshold=0.6,  # 保守參數（已驗證盈利）
        enable_smoothing=True,
        smoothing_window=7,
        min_holding_periods=24,
        enable_adaptive_params=True
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='測試 ALM 策略')
    parser.add_argument('--type', choices=['base', 'optimized', 'improved', 'both', 'all'], 
                       default='improved',
                       help='策略版本：base, optimized, improved, both (base+optimized), all (全部)')
    parser.add_argument('--plot', action='store_true', help='繪製權益曲線')
    args = parser.parse_args()
    
    results = {}
    
    if args.type in ['base', 'both', 'all']:
        print("\n" + "="*80)
        print("測試基礎 ALM 策略")
        print("="*80)
        bt = test_alm_base()
        if args.plot and bt:
            print("\n繪製權益曲線...")
            bt.plot_equity()
        results['base'] = bt
    
    if args.type in ['optimized', 'both', 'all']:
        print("\n" + "="*80)
        print("測試優化版 ALM 策略")
        print("="*80)
        bt = test_alm_optimized()
        if args.plot and bt:
            print("\n繪製權益曲線...")
            bt.plot_equity()
        results['optimized'] = bt
    
    if args.type in ['improved', 'all']:
        print("\n" + "="*80)
        print("測試改進版 ALM 策略（推薦）")
        print("="*80)
        bt = test_alm_improved()
        if args.plot and bt:
            print("\n繪製權益曲線...")
            bt.plot_equity()
        results['improved'] = bt
    
    return results

