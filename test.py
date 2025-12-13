"""
快速測試腳本 - 測試 ALM 策略
"""

import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from phandas import Panel
from strategies.alm import build_alm_strategy_improved, build_alm_strategy_ultra_conservative
from core.backtest import run_backtest
import argparse


def test_strategy(strategy_type='improved', csv_file='test_4h.csv', plot=False):
    """
    測試策略
    
    參數
    ----------
    strategy_type : str
        策略類型：'improved' 或 'ultra_conservative'
    csv_file : str
        CSV 數據文件
    plot : bool
        是否繪製權益曲線
    """
    print("=" * 80)
    print(f"測試 ALM 策略 - {strategy_type}")
    print("=" * 80)
    
    # 載入數據
    csv_path = os.path.join(project_root, csv_file)
    if not os.path.exists(csv_path):
        print(f"錯誤: 找不到文件 {csv_path}")
        print("請先運行數據獲取或確保 test_4h.csv 存在")
        return None
    
    print(f"\n[1/4] 載入數據...")
    panel = Panel.from_csv(csv_path)
    print(f"  ✓ 載入成功: {len(panel.data)} 條記錄")
    
    symbols = panel.data['symbol'].unique()
    print(f"  資產: {list(symbols)}")
    print(f"  日期範圍: {panel.data['timestamp'].min()} 至 {panel.data['timestamp'].max()}")
    
    # 構建策略
    print(f"\n[2/4] 構建策略...")
    try:
        if strategy_type == 'ultra_conservative':
            print("  使用超保守配置（推薦）...")
            strategy = build_alm_strategy_ultra_conservative(
                panel_1h=panel,
                panel_4h=panel,
                signal_entry_threshold=0.75,
                signal_exit_threshold=0.25,
                smoothing_window=15,
                min_holding_periods=72,
                enable_adaptive_params=True,
                base_window=30
            )
        else:
            print("  使用改進版配置（保守參數）...")
            strategy = build_alm_strategy_improved(
                panel_1h=panel,
                panel_4h=panel,
                use_weighted_scoring=True,
                signal_threshold=0.6,
                enable_smoothing=True,
                smoothing_window=7,
                min_holding_periods=24,
                enable_adaptive_params=True
            )
        print(f"  ✓ 策略構建成功")
    except Exception as e:
        print(f"  ✗ 策略構建失敗: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 執行回測
    print(f"\n[3/4] 執行回測...")
    try:
        bt = run_backtest(
            strategy_signal=strategy,
            panel_1h=panel,
            transaction_cost=(0.001, 0.001),  # 0.1% 單邊
            initial_capital=100000.0,
            use_inverse_vol_weighting=True,
            save_results=False
        )
        print(f"  ✓ 回測完成")
    except Exception as e:
        print(f"  ✗ 回測失敗: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 顯示結果
    print(f"\n[4/4] 結果分析...")
    print()
    bt.print_summary()
    print()
    
    # 計算換手率
    try:
        turnover_df = bt.get_daily_turnover_df()
        if not turnover_df.empty:
            sample_turnover = turnover_df['turnover'].iloc[0]
            if sample_turnover < 1.0:
                annual_turnover = turnover_df['turnover'].mean() * 365 * 100
            else:
                annual_turnover = turnover_df['turnover'].mean() * 365
            transaction_cost_pct = annual_turnover * 0.002  # 雙邊成本
            
            print("關鍵指標:")
            print(f"  年化換手率: {annual_turnover:.2f}%")
            print(f"  年化交易成本: {transaction_cost_pct:.2f}%")
            
            metrics = bt.metrics
            net_return = metrics.get('annual_return', 0) - transaction_cost_pct
            print(f"  淨年化收益: {net_return:.2%}")
            print()
            
            # 評估
            print("目標評估:")
            print(f"  換手率目標 (< 500%): {'✓' if annual_turnover < 500 else '✗'} {annual_turnover:.2f}%")
            print(f"  夏普比率目標 (> 1.0): {'✓' if metrics.get('sharpe_ratio', 0) > 1.0 else '✗'} {metrics.get('sharpe_ratio', 0):.2f}")
            print(f"  淨年化收益目標 (> 15%): {'✓' if net_return > 0.15 else '✗'} {net_return:.2%}")
    except Exception as e:
        print(f"  警告: 無法計算換手率: {e}")
    
    # 繪製權益曲線
    if plot:
        print(f"\n繪製權益曲線...")
        try:
            bt.plot_equity(figsize=(16, 10), show_summary=True, show_benchmark=True)
            print(f"  ✓ 權益曲線已繪製")
        except Exception as e:
            print(f"  ✗ 繪圖失敗: {e}")
    
    return bt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='測試 ALM 策略')
    parser.add_argument('--type', choices=['improved', 'ultra_conservative'], 
                       default='ultra_conservative',
                       help='策略類型：improved（改進版）或 ultra_conservative（超保守，推薦）')
    parser.add_argument('--csv', default='test_4h.csv', help='CSV 數據文件')
    parser.add_argument('--plot', action='store_true', help='繪製權益曲線')
    args = parser.parse_args()
    
    test_strategy(
        strategy_type=args.type,
        csv_file=args.csv,
        plot=args.plot
    )

