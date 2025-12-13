"""
策略測試模板 - 通用測試函數
用於測試各種策略版本
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from phandas import *
from core.backtest import run_backtest, resample_panel_to_4h


def test_strategy(
    strategy_name: str,
    build_strategy_func,
    symbols: list = None,
    start_date: str = '2023-01-01',
    end_date: str = '2024-01-01',
    transaction_cost: float = 0.001,
    **strategy_kwargs
):
    """
    通用策略測試函數
    
    參數
    ----------
    strategy_name : str
        策略名稱
    build_strategy_func : callable
        構建策略信號的函數
    symbols : list
        交易資產列表
    start_date : str
        開始日期
    end_date : str
        結束日期
    transaction_cost : float
        交易成本
    **strategy_kwargs
        傳遞給策略函數的額外參數
    """
    print(f"=" * 80)
    print(f"測試策略: {strategy_name}")
    print(f"=" * 80)
    
    if symbols is None:
        from strategies.alm import OKX_TOP_15_ASSETS
        symbols = OKX_TOP_15_ASSETS[:5]
    
    # 獲取數據
    print(f"\n[1/4] 獲取數據...", flush=True)
    print(f"  資產: {symbols}", flush=True)
    print(f"  期間: {start_date} 至 {end_date}", flush=True)
    print(f"  從 Binance 獲取 1H 數據（可能需要一些時間）...", flush=True)
    import sys
    sys.stdout.flush()
    
    try:
        panel_1h = fetch_data(
            symbols=symbols,
            timeframe='1h',
            start_date=start_date,
            end_date=end_date,
            sources=['binance']
        )
        print(f"  ✓ 1H 數據獲取成功: {len(panel_1h.data)} 條記錄", flush=True)
    except Exception as e:
        print(f"  ✗ 1H 數據獲取失敗: {e}")
        raise
    
    print(f"  獲取 4H 數據...", flush=True)
    try:
        panel_4h = fetch_data(
            symbols=symbols,
            timeframe='4h',
            start_date=start_date,
            end_date=end_date,
            sources=['binance']
        )
        print(f"  ✓ 4H 數據獲取成功: {len(panel_4h.data)} 條記錄", flush=True)
    except Exception as e:
        print(f"  ⚠ 4H 數據獲取失敗，從 1H 重採樣: {e}", flush=True)
        panel_4h = resample_panel_to_4h(panel_1h)
        print(f"  ✓ 4H 數據重採樣成功: {len(panel_4h.data)} 條記錄", flush=True)
    
    # 構建策略
    print(f"[2/4] 構建策略信號...")
    strategy_signal = build_strategy_func(
        panel_1h=panel_1h,
        panel_4h=panel_4h,
        **strategy_kwargs
    )
    
    # 執行回測
    print(f"[3/4] 執行回測...")
    bt_results = run_backtest(
        strategy_signal=strategy_signal,
        panel_1h=panel_1h,
        transaction_cost=(transaction_cost, transaction_cost),
        initial_capital=100000.0,
        use_inverse_vol_weighting=True
    )
    
    # 顯示結果
    print(f"[4/4] 分析結果...")
    print()
    bt_results.print_summary()
    print()
    
    # 計算換手率
    turnover_df = bt_results.get_daily_turnover_df()
    if not turnover_df.empty:
        annual_turnover = turnover_df['turnover'].mean() * 365
        print(f"年化換手率: {annual_turnover:.2%}")
    
    return bt_results

