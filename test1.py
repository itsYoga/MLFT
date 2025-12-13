"""
使用 ALM 策略進行回測
"""

import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from phandas import *
from strategies.alm import build_alm_strategy_ultra_conservative, build_alm_strategy_improved
from core.backtest import run_backtest

# 1. 獲取數據
print("=" * 80)
print("ALM 策略回測")
print("=" * 80)

print("\n[1/4] 獲取數據...")
panel = fetch_data(
    symbols=['BTC', 'ETH', 'SOL', 'ARB', 'OP', 'POL', 'SUI'],
    start_date='2023-01-01',
    sources=['binance'],
    timeframe='1d'  # 日線數據
)

print(f"  ✓ 數據獲取成功: {len(panel.data)} 條記錄")
print(f"  資產: {panel.data['symbol'].unique().tolist()}")
print(f"  日期範圍: {panel.data['timestamp'].min()} 至 {panel.data['timestamp'].max()}")

# 保存到 CSV（避免重複下載）
panel.to_csv('test_4h.csv')
print("  ✓ 數據已保存至 test_4h.csv")

# 如果需要使用已保存的數據，取消下面的註釋：
# panel = Panel.from_csv('test_4h.csv')

# 2. 構建策略
print("\n[2/4] 構建策略...")
print("  使用超保守配置（推薦）...")

# 使用超保守策略（已驗證盈利）
strategy_signal = build_alm_strategy_ultra_conservative(
    panel_1h=panel,
    panel_4h=panel,  # 使用相同數據（簡化處理）
    signal_entry_threshold=0.75,    # 極高入場閾值
    signal_exit_threshold=0.25,      # 極低出場閾值（寬遲滯）
    smoothing_window=15,             # 極長平滑窗口
    min_holding_periods=72,          # 3天最小持倉
    enable_adaptive_params=True,
    base_window=30
)

print("  ✓ 策略構建成功")

# 統計信號
signal_data = strategy_signal.data
total = len(signal_data)
long_signals = (signal_data['factor'] > 0).sum()
short_signals = (signal_data['factor'] < 0).sum()
coverage = (long_signals + short_signals) / total * 100

print(f"\n  信號統計:")
print(f"    覆蓋率: {coverage:.2f}%")
print(f"    做多: {long_signals} ({long_signals/total*100:.2f}%)")
print(f"    做空: {short_signals} ({short_signals/total*100:.2f}%)")

# 3. 執行回測
print("\n[3/4] 執行回測...")

bt_results = run_backtest(
    strategy_signal=strategy_signal,
    panel_1h=panel,
    transaction_cost=(0.001, 0.001),  # 0.1% 單邊
    initial_capital=100000.0,
    use_inverse_vol_weighting=True,
    save_results=False
)

print("  ✓ 回測完成")

# 4. 顯示結果
print("\n[4/4] 結果分析...")
print()
bt_results.print_summary()
print()

# 計算換手率
try:
    turnover_df = bt_results.get_daily_turnover_df()
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
        
        metrics = bt_results.metrics
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

# 5. 繪製權益曲線
print("\n繪製權益曲線...")
bt_results.plot_equity(figsize=(16, 10), show_summary=True, show_benchmark=True)
print("  ✓ 權益曲線已繪製")
