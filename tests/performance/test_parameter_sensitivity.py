"""
測試不同參數配置的改進版策略
"""

import sys
import os
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from phandas import Panel
from strategies.alm import build_alm_strategy_improved
from core.backtest import run_backtest

def test_config(config_name, **params):
    """測試特定參數配置"""
    print(f"\n{'='*80}")
    print(f"測試配置: {config_name}")
    print(f"{'='*80}")
    print(f"參數: {params}")
    
    csv_path = os.path.join(project_root, 'test_4h.csv')
    panel = Panel.from_csv(csv_path)
    
    try:
        strategy = build_alm_strategy_improved(
            panel_1h=panel,
            panel_4h=panel,
            use_weighted_scoring=True,
            enable_smoothing=True,
            enable_adaptive_params=True,
            **params
        )
        
        # 統計信號
        signal_data = strategy.data
        total = len(signal_data)
        long_signals = (signal_data['factor'] > 0).sum()
        short_signals = (signal_data['factor'] < 0).sum()
        coverage = (long_signals + short_signals) / total * 100
        
        print(f"\n信號統計:")
        print(f"  覆蓋率: {coverage:.2f}%")
        print(f"  做多: {long_signals} ({long_signals/total*100:.2f}%)")
        print(f"  做空: {short_signals} ({short_signals/total*100:.2f}%)")
        
        # 回測
        bt = run_backtest(
            strategy_signal=strategy,
            panel_1h=panel,
            transaction_cost=(0.001, 0.001),
            initial_capital=100000.0,
            use_inverse_vol_weighting=True,
            save_results=False
        )
        
        # 計算換手率
        try:
            turnover_df = bt.get_daily_turnover_df()
            annual_turnover = turnover_df['turnover'].mean() * 365 if not turnover_df.empty else 0
        except:
            annual_turnover = 0
        
        metrics = bt.metrics
        print(f"\n績效指標:")
        print(f"  總收益率: {metrics.get('total_return', 0):.2%}")
        print(f"  年化收益率: {metrics.get('annual_return', 0):.2%}")
        print(f"  夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"  最大回撤: {metrics.get('max_drawdown', 0):.2%}")
        print(f"  年化換手率: {annual_turnover:.2%}")
        
        # 計算交易成本
        transaction_cost_pct = annual_turnover * 0.002  # 0.1% 買入 + 0.1% 賣出
        print(f"  年化交易成本: {transaction_cost_pct:.2%}")
        
        return {
            'config': config_name,
            'coverage': coverage,
            'annual_return': metrics.get('annual_return', 0),
            'sharpe': metrics.get('sharpe_ratio', 0),
            'max_dd': metrics.get('max_drawdown', 0),
            'turnover': annual_turnover,
            'transaction_cost': transaction_cost_pct
        }
    except Exception as e:
        print(f"  ✗ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = []
    
    # 配置 1：當前配置（基準）
    results.append(test_config(
        "當前配置（基準）",
        signal_threshold=0.4,
        min_holding_periods=8,
        smoothing_window=3
    ))
    
    # 配置 2：保守（低換手率）
    results.append(test_config(
        "保守配置（低換手率）",
        signal_threshold=0.6,
        min_holding_periods=24,
        smoothing_window=7
    ))
    
    # 配置 3：平衡
    results.append(test_config(
        "平衡配置",
        signal_threshold=0.5,
        min_holding_periods=16,
        smoothing_window=5
    ))
    
    # 配置 4：中等保守
    results.append(test_config(
        "中等保守",
        signal_threshold=0.5,
        min_holding_periods=24,
        smoothing_window=5
    ))
    
    # 總結
    print(f"\n{'='*80}")
    print("配置對比總結")
    print(f"{'='*80}")
    print(f"{'配置':<20} {'覆蓋率':<10} {'年化收益':<12} {'夏普':<8} {'最大回撤':<12} {'換手率':<12} {'交易成本':<12}")
    print("-" * 80)
    
    for r in results:
        if r:
            print(f"{r['config']:<20} {r['coverage']:>8.2f}% {r['annual_return']:>10.2%} "
                  f"{r['sharpe']:>7.2f} {r['max_dd']:>10.2%} {r['turnover']:>10.2%} "
                  f"{r['transaction_cost']:>10.2%}")
