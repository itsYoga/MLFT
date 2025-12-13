"""
策略測試模板 - 複製此文件創建新策略測試
"""

import sys
import os

# 添加項目根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    
    Parameters
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
    print(f"Testing Strategy: {strategy_name}")
    print(f"=" * 80)
    
    if symbols is None:
        from strategies.alm import OKX_TOP_15_ASSETS
        symbols = OKX_TOP_15_ASSETS[:5]
    
    # Fetch data
    print(f"\n[1/4] Fetching data...", flush=True)
    print(f"  Symbols: {symbols}", flush=True)
    print(f"  Period: {start_date} to {end_date}", flush=True)
    print(f"  Fetching 1H data from Binance (this may take some time)...", flush=True)
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
        print(f"  ✓ 1H data fetched: {len(panel_1h.data)} records", flush=True)
    except Exception as e:
        print(f"  ✗ 1H data fetch failed: {e}")
        raise
    
    print(f"  Fetching 4H data...", flush=True)
    try:
        panel_4h = fetch_data(
            symbols=symbols,
            timeframe='4h',
            start_date=start_date,
            end_date=end_date,
            sources=['binance']
        )
        print(f"  ✓ 4H data fetched: {len(panel_4h.data)} records", flush=True)
    except Exception as e:
        print(f"  ⚠ 4H data fetch failed, resampling from 1H: {e}", flush=True)
        panel_4h = resample_panel_to_4h(panel_1h)
        print(f"  ✓ 4H data resampled: {len(panel_4h.data)} records", flush=True)
    
    # Build strategy
    print(f"[2/4] Building strategy signal...")
    strategy_signal = build_strategy_func(
        panel_1h=panel_1h,
        panel_4h=panel_4h,
        **strategy_kwargs
    )
    
    # Run backtest
    print(f"[3/4] Running backtest...")
    bt_results = run_backtest(
        strategy_signal=strategy_signal,
        panel_1h=panel_1h,
        transaction_cost=(transaction_cost, transaction_cost),
        initial_capital=100000.0,
        use_inverse_vol_weighting=True
    )
    
    # Display results
    print(f"[4/4] Analyzing results...")
    print()
    bt_results.print_summary()
    print()
    
    # Calculate turnover
    turnover_df = bt_results.get_daily_turnover_df()
    if not turnover_df.empty:
        annual_turnover = turnover_df['turnover'].mean() * 365
        print(f"Annual Turnover: {annual_turnover:.2%}")
    
    return bt_results


if __name__ == "__main__":
    # 示例：測試 ALM 策略
    from strategies.alm import build_alm_strategy
    
    bt_results = test_strategy(
        strategy_name="ALM Base",
        build_strategy_func=build_alm_strategy,
        symbols=['BTC', 'ETH', 'SOL'],
        start_date='2023-01-01',
        end_date='2024-01-01',
        transaction_cost=0.001
    )

