"""
超保守策略測試 - 驗證換手率是否降低到 < 500%
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from phandas import Panel
from strategies.alm import build_alm_strategy_improved
from strategies.alm.strategy_ultra_conservative import build_alm_strategy_ultra_conservative
from core.backtest import run_backtest
import pandas as pd
import numpy as np


def test_ultra_conservative_strategy(csv_file='test_4h.csv', plot=False):
    """
    測試超保守策略配置
    
    目標指標：
    - 換手率 < 500% 年化
    - 夏普比率 > 1.0
    - 年化收益率 > 15%
    """
    csv_path = os.path.join(project_root, csv_file)
    if not os.path.exists(csv_path):
        print(f"錯誤: 找不到文件 {csv_path}")
        return None
    
    print("=" * 80)
    print("超保守策略測試 - 極致降低換手率")
    print("=" * 80)
    
    # 載入數據
    print(f"\n[1/5] 載入數據...")
    panel = Panel.from_csv(csv_path)
    print(f"  ✓ 載入成功: {len(panel.data)} 條記錄")
    
    symbols = panel.data['symbol'].unique()
    print(f"  資產: {list(symbols)}")
    print(f"  日期範圍: {panel.data['timestamp'].min()} 至 {panel.data['timestamp'].max()}")
    
    results = {}
    
    # 測試配置 1: 當前改進版（基準）
    print(f"\n[2/5] 測試當前改進版策略（基準）...")
    try:
        strategy_current = build_alm_strategy_improved(
            panel_1h=panel,
            panel_4h=panel,
            use_weighted_scoring=True,
            signal_threshold=0.6,
            enable_smoothing=True,
            smoothing_window=7,
            min_holding_periods=24,
            enable_adaptive_params=True
        )
        
        bt_current = run_backtest(
            strategy_signal=strategy_current,
            panel_1h=panel,
            transaction_cost=(0.001, 0.001),  # 0.1% 單邊
            initial_capital=100000.0,
            use_inverse_vol_weighting=True,
            save_results=False
        )
        
        turnover_df = bt_current.get_daily_turnover_df()
        # turnover 可能是小數形式（0.1826 = 18.26%）或百分比形式（18.26）
        # 檢查第一個值來判斷格式
        if not turnover_df.empty:
            sample_turnover = turnover_df['turnover'].iloc[0]
            if sample_turnover < 1.0:
                # 小數形式，需要轉換為百分比
                annual_turnover = turnover_df['turnover'].mean() * 365 * 100
            else:
                # 已經是百分比形式
                annual_turnover = turnover_df['turnover'].mean() * 365
        else:
            annual_turnover = 0
        transaction_cost_pct = annual_turnover * 0.002  # 雙邊成本（0.1% * 2 = 0.2%）
        
        results['current'] = {
            'bt': bt_current,
            'metrics': bt_current.metrics,
            'turnover': annual_turnover,
            'transaction_cost': transaction_cost_pct
        }
        
        print(f"  年化換手率: {annual_turnover:.2f}%")
        print(f"  年化交易成本: {transaction_cost_pct:.2f}%")
        print(f"  年化收益率: {bt_current.metrics.get('annual_return', 0):.2%}")
        
    except Exception as e:
        print(f"  ✗ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        results['current'] = None
    
    # 測試配置 2: 超保守版（極致參數）
    print(f"\n[3/5] 測試超保守版策略（極致參數）...")
    print("  參數:")
    print("    entry_threshold=0.75 (極高)")
    print("    exit_threshold=0.25 (極低)")
    print("    smoothing_window=15 (極長)")
    print("    min_holding_periods=72 (3天)")
    
    try:
        strategy_ultra = build_alm_strategy_ultra_conservative(
            panel_1h=panel,
            panel_4h=panel,
            signal_entry_threshold=0.75,
            signal_exit_threshold=0.25,
            smoothing_window=15,
            min_holding_periods=72,
            enable_adaptive_params=True,
            base_window=30
        )
        
        bt_ultra = run_backtest(
            strategy_signal=strategy_ultra,
            panel_1h=panel,
            transaction_cost=(0.001, 0.001),  # 0.1% 單邊
            initial_capital=100000.0,
            use_inverse_vol_weighting=True,
            save_results=False
        )
        
        turnover_df = bt_ultra.get_daily_turnover_df()
        if not turnover_df.empty:
            sample_turnover = turnover_df['turnover'].iloc[0]
            if sample_turnover < 1.0:
                annual_turnover = turnover_df['turnover'].mean() * 365 * 100
            else:
                annual_turnover = turnover_df['turnover'].mean() * 365
        else:
            annual_turnover = 0
        transaction_cost_pct = annual_turnover * 0.002  # 雙邊成本
        
        results['ultra'] = {
            'bt': bt_ultra,
            'metrics': bt_ultra.metrics,
            'turnover': annual_turnover,
            'transaction_cost': transaction_cost_pct
        }
        
        print(f"  年化換手率: {annual_turnover:.2f}%")
        print(f"  年化交易成本: {transaction_cost_pct:.2f}%")
        print(f"  年化收益率: {bt_ultra.metrics.get('annual_return', 0):.2%}")
        
    except Exception as e:
        print(f"  ✗ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        results['ultra'] = None
    
    # 測試配置 3: 中等保守（平衡）
    print(f"\n[4/5] 測試中等保守配置（平衡）...")
    print("  參數:")
    print("    entry_threshold=0.70")
    print("    exit_threshold=0.30")
    print("    smoothing_window=10")
    print("    min_holding_periods=48 (2天)")
    
    try:
        strategy_medium = build_alm_strategy_ultra_conservative(
            panel_1h=panel,
            panel_4h=panel,
            signal_entry_threshold=0.70,
            signal_exit_threshold=0.30,
            smoothing_window=10,
            min_holding_periods=48,
            enable_adaptive_params=True,
            base_window=25
        )
        
        bt_medium = run_backtest(
            strategy_signal=strategy_medium,
            panel_1h=panel,
            transaction_cost=(0.001, 0.001),
            initial_capital=100000.0,
            use_inverse_vol_weighting=True,
            save_results=False
        )
        
        turnover_df = bt_medium.get_daily_turnover_df()
        if not turnover_df.empty:
            sample_turnover = turnover_df['turnover'].iloc[0]
            if sample_turnover < 1.0:
                annual_turnover = turnover_df['turnover'].mean() * 365 * 100
            else:
                annual_turnover = turnover_df['turnover'].mean() * 365
        else:
            annual_turnover = 0
        transaction_cost_pct = annual_turnover * 0.002  # 雙邊成本
        
        results['medium'] = {
            'bt': bt_medium,
            'metrics': bt_medium.metrics,
            'turnover': annual_turnover,
            'transaction_cost': transaction_cost_pct
        }
        
        print(f"  年化換手率: {annual_turnover:.2f}%")
        print(f"  年化交易成本: {transaction_cost_pct:.2f}%")
        print(f"  年化收益率: {bt_medium.metrics.get('annual_return', 0):.2%}")
        
    except Exception as e:
        print(f"  ✗ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        results['medium'] = None
    
    # 對比總結
    print(f"\n[5/5] 對比總結")
    print("=" * 80)
    
    comparison_data = []
    
    for name, r in results.items():
        if r:
            m = r['metrics']
            comparison_data.append({
                '配置': {
                    'current': '當前改進版',
                    'medium': '中等保守',
                    'ultra': '超保守'
                }.get(name, name),
                '年化收益率': f"{m.get('annual_return', 0):.2%}",
                '夏普比率': f"{m.get('sharpe_ratio', 0):.2f}",
                '最大回撤': f"{m.get('max_drawdown', 0):.2%}",
                '年化換手率': f"{r['turnover']:.2f}%",
                '年化交易成本': f"{r['transaction_cost']:.2f}%",
                '淨年化收益': f"{m.get('annual_return', 0) - r['transaction_cost']:.2%}"
            })
    
    if comparison_data:
        df = pd.DataFrame(comparison_data)
        print("\n" + df.to_string(index=False))
        
        # 評估是否達到目標
        print("\n" + "=" * 80)
        print("目標評估")
        print("=" * 80)
        
        for name, r in results.items():
            if r:
                config_name = {
                    'current': '當前改進版',
                    'medium': '中等保守',
                    'ultra': '超保守'
                }.get(name, name)
                
                m = r['metrics']
                turnover = r['turnover']
                sharpe = m.get('sharpe_ratio', 0)
                annual_ret = m.get('annual_return', 0)
                net_ret = annual_ret - r['transaction_cost']
                
                print(f"\n{config_name}:")
                print(f"  換手率目標 (< 500%): {'✓' if turnover < 500 else '✗'} {turnover:.2f}%")
                print(f"  夏普比率目標 (> 1.0): {'✓' if sharpe > 1.0 else '✗'} {sharpe:.2f}")
                print(f"  淨年化收益目標 (> 15%): {'✓' if net_ret > 0.15 else '✗'} {net_ret:.2%}")
    
    # 繪製對比圖
    if plot and results.get('current') and results.get('ultra'):
        print(f"\n繪製權益曲線對比...")
        try:
            import matplotlib.pyplot as plt
            
            fig, axes = plt.subplots(2, 1, figsize=(16, 12))
            
            # 權益曲線（欄位名稱是 'total_value'）
            current_history = results['current']['bt'].portfolio.get_history_df()
            ultra_history = results['ultra']['bt'].portfolio.get_history_df()
            
            # 檢查可用的欄位名稱
            equity_col = 'total_value' if 'total_value' in current_history.columns else 'equity'
            if equity_col not in current_history.columns:
                # 如果都沒有，使用第一個數值欄位
                numeric_cols = current_history.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    equity_col = numeric_cols[0]
                else:
                    raise ValueError(f"找不到權益欄位，可用欄位: {current_history.columns.tolist()}")
            
            current_equity = current_history[equity_col]
            ultra_equity = ultra_history[equity_col]
            
            axes[0].plot(current_equity.index, current_equity.values, 
                        label='當前改進版', linewidth=2)
            axes[0].plot(ultra_equity.index, ultra_equity.values, 
                        label='超保守版', linewidth=2)
            axes[0].set_title('權益曲線對比', fontsize=14, fontweight='bold')
            axes[0].set_xlabel('時間')
            axes[0].set_ylabel('權益 ($)')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)
            
            # 回撤對比
            current_dd = (current_equity / current_equity.expanding().max() - 1) * 100
            ultra_dd = (ultra_equity / ultra_equity.expanding().max() - 1) * 100
            
            axes[1].fill_between(current_dd.index, current_dd.values, 0, 
                                alpha=0.3, label='當前改進版')
            axes[1].fill_between(ultra_dd.index, ultra_dd.values, 0, 
                                alpha=0.3, label='超保守版')
            axes[1].set_title('回撤對比', fontsize=14, fontweight='bold')
            axes[1].set_xlabel('時間')
            axes[1].set_ylabel('回撤 (%)')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            output_path = os.path.join(project_root, 'data', 'ultra_conservative_comparison.png')
            plt.savefig(output_path, dpi=150)
            print(f"  ✓ 對比圖已保存至: {output_path}")
            
        except Exception as e:
            print(f"  ✗ 繪圖失敗: {e}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='超保守策略測試')
    parser.add_argument('--csv', default='test_4h.csv', help='CSV 數據文件')
    parser.add_argument('--plot', action='store_true', help='繪製對比圖')
    args = parser.parse_args()
    
    results = test_ultra_conservative_strategy(csv_file=args.csv, plot=args.plot)

