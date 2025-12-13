"""
使用本地 CSV 文件進行整合測試
適用於快速測試和離線測試
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from phandas import Panel
from strategies.alm import build_alm_strategy, build_alm_strategy_improved
from core.backtest import run_backtest


def test_with_csv(csv_file='test_4h.csv', strategy_type='base', plot=True):
    """
    使用 CSV 文件測試策略
    
    參數
    ----------
    csv_file : str
        CSV 文件路徑
    strategy_type : str
        策略類型：'base', 'optimized', 'improved'
    plot : bool
        是否繪製權益曲線
    """
    csv_path = os.path.join(project_root, csv_file)
    
    if not os.path.exists(csv_path):
        print(f"錯誤: 找不到文件 {csv_path}")
        return None
    
    print("=" * 80)
    print(f"使用本地數據文件測試策略: {csv_file}")
    print(f"策略類型: {strategy_type}")
    print("=" * 80)
    
    print(f"\n[1/4] 載入數據...")
    try:
        panel = Panel.from_csv(csv_path)
        print(f"  ✓ 載入成功: {len(panel.data)} 條記錄")
        
        symbols = panel.data['symbol'].unique()
        print(f"  資產: {list(symbols)}")
        print(f"  日期範圍: {panel.data['timestamp'].min()} 至 {panel.data['timestamp'].max()}")
        
        required = ['open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required if c not in panel.data.columns]
        if missing:
            print(f"  ✗ 缺少欄位: {missing}")
            return None
            
    except Exception as e:
        print(f"  ✗ 載入失敗: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    print(f"\n[2/4] 構建策略...")
    try:
        if strategy_type == 'improved':
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
        else:
            strategy = build_alm_strategy(
                panel_1h=panel,
                panel_4h=panel
            )
        print(f"  ✓ 策略構建成功")
    except Exception as e:
        print(f"  ✗ 策略構建失敗: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    print(f"\n[3/4] 執行回測...")
    try:
        bt = run_backtest(
            strategy_signal=strategy,
            panel_1h=panel,
            transaction_cost=(0.001, 0.001),
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
    
    print(f"\n[4/4] 結果分析:")
    try:
        bt.print_summary()
    except Exception as e:
        print(f"  print_summary() 失敗: {e}")
    
    # 顯示關鍵指標
    if hasattr(bt, 'metrics') and bt.metrics:
        metrics = bt.metrics
        print("\n關鍵指標:")
        print(f"  總收益率: {metrics.get('total_return', 0):.2%}")
        print(f"  年化收益率: {metrics.get('annual_return', 0):.2%}")
        print(f"  夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"  最大回撤: {metrics.get('max_drawdown', 0):.2%}")
        print(f"  年化波動率: {metrics.get('annual_volatility', 0):.2%}")
    else:
        print("  警告: 無法獲取指標，嘗試 calculate_metrics()...")
        try:
            bt.calculate_metrics()
            metrics = bt.metrics
            print("\n關鍵指標:")
            print(f"  總收益率: {metrics.get('total_return', 0):.2%}")
            print(f"  年化收益率: {metrics.get('annual_return', 0):.2%}")
            print(f"  夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        except Exception as e2:
            print(f"  calculate_metrics() 也失敗: {e2}")
    
    # 計算換手率
    try:
        turnover_df = bt.get_daily_turnover_df()
        if not turnover_df.empty:
            annual_turnover = turnover_df['turnover'].mean() * 365
            print(f"\n年化換手率: {annual_turnover:.2%}")
    except:
        pass
    
    # 繪製權益曲線
    if plot:
        print(f"\n[5/5] 繪製權益曲線...")
        try:
            bt.plot_equity(figsize=(16, 10), show_summary=True, show_benchmark=True)
            print(f"  ✓ 權益曲線已繪製")
        except Exception as e:
            print(f"  ✗ 繪製失敗: {e}")
            import traceback
            traceback.print_exc()
    
    return bt


if __name__ == "__main__":
    import sys
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'test_4h.csv'
    strategy_type = sys.argv[2] if len(sys.argv) > 2 else 'improved'
    plot = '--no-plot' not in sys.argv
    test_with_csv(csv_file, strategy_type=strategy_type, plot=plot)

