"""
策略性能對比測試
對比不同策略版本的性能表現
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from phandas import Panel
from strategies.alm import build_alm_strategy_improved, build_alm_strategy_advanced
from core.backtest import run_backtest
import pandas as pd


def test_strategy_comparison(csv_file='test_4h.csv', plot=False):
    """對比測試兩個策略版本"""
    
    print("=" * 80)
    print("策略對比測試：改進版（保守參數）vs 高級版")
    print("=" * 80)
    
    # 載入數據
    csv_path = os.path.join(project_root, csv_file)
    if not os.path.exists(csv_path):
        print(f"錯誤: 找不到文件 {csv_path}")
        return None
    
    print(f"\n[1/5] 載入數據...")
    panel = Panel.from_csv(csv_path)
    print(f"  ✓ 載入成功: {len(panel.data)} 條記錄")
    
    symbols = panel.data['symbol'].unique()
    print(f"  資產: {list(symbols)}")
    print(f"  日期範圍: {panel.data['timestamp'].min()} 至 {panel.data['timestamp'].max()}")
    
    results = {}
    
    # 測試 1: 改進版策略（保守參數）
    print(f"\n[2/5] 測試改進版策略（保守參數）...")
    print("  參數:")
    print("    signal_threshold=0.6")
    print("    smoothing_window=7")
    print("    min_holding_periods=24")
    print("    enable_adaptive_params=True")
    
    try:
        strategy_improved = build_alm_strategy_improved(
            panel_1h=panel,
            panel_4h=panel,
            use_weighted_scoring=True,
            signal_threshold=0.6,
            enable_smoothing=True,
            smoothing_window=7,
            min_holding_periods=24,
            enable_adaptive_params=True
        )
        
        # 統計信號
        signal_data = strategy_improved.data
        total = len(signal_data)
        long_signals = (signal_data['factor'] > 0).sum()
        short_signals = (signal_data['factor'] < 0).sum()
        coverage = (long_signals + short_signals) / total * 100
        
        print(f"\n  信號統計:")
        print(f"    覆蓋率: {coverage:.2f}%")
        print(f"    做多: {long_signals} ({long_signals/total*100:.2f}%)")
        print(f"    做空: {short_signals} ({short_signals/total*100:.2f}%)")
        
        # 回測
        bt_improved = run_backtest(
            strategy_signal=strategy_improved,
            panel_1h=panel,
            transaction_cost=(0.001, 0.001),
            initial_capital=100000.0,
            use_inverse_vol_weighting=True,
            save_results=False
        )
        
        # 計算換手率
        try:
            turnover_df = bt_improved.get_daily_turnover_df()
            annual_turnover = turnover_df['turnover'].mean() * 365 if not turnover_df.empty else 0
        except:
            annual_turnover = 0
        
        metrics = bt_improved.metrics
        transaction_cost_pct = annual_turnover * 0.002
        
        print(f"\n  績效指標:")
        print(f"    總收益率: {metrics.get('total_return', 0):.2%}")
        print(f"    年化收益率: {metrics.get('annual_return', 0):.2%}")
        print(f"    夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"    最大回撤: {metrics.get('max_drawdown', 0):.2%}")
        print(f"    年化換手率: {annual_turnover:.2%}")
        print(f"    年化交易成本: {transaction_cost_pct:.2%}")
        
        results['improved'] = {
            'strategy': strategy_improved,
            'bt': bt_improved,
            'metrics': metrics,
            'coverage': coverage,
            'turnover': annual_turnover,
            'transaction_cost': transaction_cost_pct,
            'long_signals': long_signals,
            'short_signals': short_signals
        }
        
        print(f"  ✓ 改進版策略測試完成")
        
    except Exception as e:
        print(f"  ✗ 改進版策略測試失敗: {e}")
        import traceback
        traceback.print_exc()
        results['improved'] = None
    
    # 測試 2: 高級版策略（如果可用）
    print(f"\n[3/5] 測試高級版策略...")
    print("  注意: 高級版策略仍在開發中，可能無法運行")
    
    try:
        strategy_advanced = build_alm_strategy_advanced(
            panel_1h=panel,
            panel_daily=panel,
            base_window=20,
            chandelier_k=2.5,
            target_volatility=0.15,
            rebalance_buffer=0.10,
            signal_threshold=0.3,
            enable_chandelier=True,
            enable_vol_targeting=True
        )
        
        signal_data = strategy_advanced.data
        total = len(signal_data)
        long_signals = (signal_data['factor'] > 0).sum()
        short_signals = (signal_data['factor'] < 0).sum()
        coverage = (long_signals + short_signals) / total * 100
        
        print(f"\n  信號統計:")
        print(f"    覆蓋率: {coverage:.2f}%")
        
        bt_advanced = run_backtest(
            strategy_signal=strategy_advanced,
            panel_1h=panel,
            transaction_cost=(0.001, 0.001),
            initial_capital=100000.0,
            use_inverse_vol_weighting=True,
            save_results=False
        )
        
        try:
            turnover_df = bt_advanced.get_daily_turnover_df()
            annual_turnover = turnover_df['turnover'].mean() * 365 if not turnover_df.empty else 0
        except:
            annual_turnover = 0
        
        metrics = bt_advanced.metrics
        transaction_cost_pct = annual_turnover * 0.002
        
        print(f"\n  績效指標:")
        print(f"    年化收益率: {metrics.get('annual_return', 0):.2%}")
        print(f"    夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"    最大回撤: {metrics.get('max_drawdown', 0):.2%}")
        print(f"    年化換手率: {annual_turnover:.2%}")
        
        results['advanced'] = {
            'strategy': strategy_advanced,
            'bt': bt_advanced,
            'metrics': metrics,
            'coverage': coverage,
            'turnover': annual_turnover,
            'transaction_cost': transaction_cost_pct
        }
        
        print(f"  ✓ 高級版策略測試完成")
        
    except Exception as e:
        print(f"  ⚠ 高級版策略測試失敗（預期）: {e}")
        results['advanced'] = None
    
    # 對比總結
    print(f"\n[4/5] 對比總結")
    print("=" * 80)
    
    comparison_data = []
    
    if results.get('improved'):
        r = results['improved']
        comparison_data.append({
            '策略版本': '改進版（保守參數）',
            '信號覆蓋率': f"{r['coverage']:.2f}%",
            '年化收益率': f"{r['metrics'].get('annual_return', 0):.2%}",
            '夏普比率': f"{r['metrics'].get('sharpe_ratio', 0):.2f}",
            '最大回撤': f"{r['metrics'].get('max_drawdown', 0):.2%}",
            '年化換手率': f"{r['turnover']:.2f}%",
            '交易成本': f"{r['transaction_cost']:.2f}%"
        })
    
    if results.get('advanced'):
        r = results['advanced']
        comparison_data.append({
            '策略版本': '高級版',
            '信號覆蓋率': f"{r['coverage']:.2f}%",
            '年化收益率': f"{r['metrics'].get('annual_return', 0):.2%}",
            '夏普比率': f"{r['metrics'].get('sharpe_ratio', 0):.2f}",
            '最大回撤': f"{r['metrics'].get('max_drawdown', 0):.2%}",
            '年化換手率': f"{r['turnover']:.2f}%",
            '交易成本': f"{r['transaction_cost']:.2f}%"
        })
    
    if comparison_data:
        df = pd.DataFrame(comparison_data)
        print("\n" + df.to_string(index=False))
    
    # 繪製對比圖（如果請求）
    if plot and results.get('improved'):
        print(f"\n[5/5] 繪製權益曲線...")
        try:
            results['improved']['bt'].plot_equity()
        except Exception as e:
            print(f"  ✗ 繪圖失敗: {e}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='對比測試策略')
    parser.add_argument('--csv', default='test_4h.csv', help='CSV 數據文件')
    parser.add_argument('--plot', action='store_true', help='繪製對比圖')
    args = parser.parse_args()
    
    results = test_strategy_comparison(csv_file=args.csv, plot=args.plot)

