"""
ALM 策略測試 - 使用本地數據文件
如果數據獲取失敗，可以使用此版本測試已保存的數據
"""

import sys
import os

# 添加項目根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from phandas import Panel
from strategies.alm import build_alm_strategy
from core.backtest import run_backtest, resample_panel_to_4h


def test_with_local_data():
    """使用本地 CSV 文件測試"""
    print("=" * 80)
    print("ALM 策略測試 - 使用本地數據")
    print("=" * 80)
    
    # 檢查數據文件
    data_files = {
        '1h': 'test_4h.csv',  # 注意：這個文件名是 4h 但可能包含 1h 數據
        '4h': 'test_4h.csv'
    }
    
    # 檢查項目根目錄的 CSV 文件
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_files = [f for f in os.listdir(root_dir) if f.endswith('.csv')]
    
    print(f"\n找到的 CSV 文件: {csv_files}")
    
    if not csv_files:
        print("\n錯誤: 沒有找到 CSV 數據文件")
        print("請先運行以下命令獲取數據:")
        print("  python -c \"from phandas import fetch_data; panel = fetch_data(['BTC'], '1h', '2024-01-01', '2024-01-02', ['binance']); panel.to_csv('test_data.csv')\"")
        return None
    
    # 嘗試加載第一個 CSV 文件
    csv_file = csv_files[0]
    csv_path = os.path.join(root_dir, csv_file)
    
    print(f"\n[1/4] 加載本地數據: {csv_file}")
    try:
        panel = Panel.from_csv(csv_path)
        print(f"  ✓ 數據加載成功: {len(panel.data)} 條記錄")
        print(f"  時間範圍: {panel.data['timestamp'].min()} 至 {panel.data['timestamp'].max()}")
        print(f"  資產: {panel.data['symbol'].unique().tolist()}")
    except Exception as e:
        print(f"  ✗ 數據加載失敗: {e}")
        return None
    
    # 檢查數據列
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in panel.data.columns]
    if missing_cols:
        print(f"  ⚠ 缺少必要的列: {missing_cols}")
        print(f"  可用列: {panel.data.columns.tolist()}")
        return None
    
    # 分離 1H 和 4H 數據（如果只有一個文件，都使用它）
    panel_1h = panel
    panel_4h = panel  # 簡化：使用相同數據
    
    # 如果數據看起來是 4H 的，嘗試重採樣為 1H（簡化處理）
    # 實際應該檢查時間間隔
    
    print(f"\n[2/4] 構建策略信號...")
    try:
        strategy_signal = build_alm_strategy(
            panel_1h=panel_1h,
            panel_4h=panel_4h
        )
        print(f"  ✓ 策略信號生成成功")
    except Exception as e:
        print(f"  ✗ 策略構建失敗: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    print(f"\n[3/4] 執行回測...")
    try:
        bt_results = run_backtest(
            strategy_signal=strategy_signal,
            panel_1h=panel_1h,
            transaction_cost=(0.001, 0.001),
            initial_capital=100000.0,
            use_inverse_vol_weighting=True,
            save_results=False  # 不保存結果
        )
        print(f"  ✓ 回測完成")
    except Exception as e:
        print(f"  ✗ 回測失敗: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    print(f"\n[4/4] 結果分析...")
    print()
    bt_results.print_summary()
    print()
    
    # 計算換手率
    try:
        turnover_df = bt_results.get_daily_turnover_df()
        if not turnover_df.empty:
            annual_turnover = turnover_df['turnover'].mean() * 365
            print(f"年化換手率: {annual_turnover:.2%}")
    except:
        pass
    
    return bt_results


if __name__ == "__main__":
    test_with_local_data()

