"""
Test script - Can test both simple factor strategy and ALM strategy
Usage:
    python test.py                    # Test simple factor strategy
    python test.py --alm              # Test ALM strategy
    python test.py --alm --optimized  # Test optimized ALM strategy
    python test.py --csv test_4h.csv # Use CSV file instead of downloading
"""

import sys
import os
from phandas import *

# Add project root to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Parse command line arguments
use_alm = '--alm' in sys.argv
use_optimized = '--optimized' in sys.argv
use_csv = False
csv_file = None

for i, arg in enumerate(sys.argv):
    if arg == '--csv' and i + 1 < len(sys.argv):
        use_csv = True
        csv_file = sys.argv[i + 1]

# 1. Load or download data
if use_csv and csv_file:
    print(f"Loading data from CSV: {csv_file}")
    panel = Panel.from_csv(csv_file)
    print(f"Loaded {len(panel.data)} records")
else:
    print("Downloading data from Binance...")
    panel = fetch_data(
        symbols=['BTC', 'ETH', 'SOL', 'ARB', 'OP', 'POL', 'SUI'],
        start_date='2023-01-01',
        sources=['binance'],
        timeframe='1d'  # ALM uses 1H/4H, but for quick test we use 1d
    )
    print(f"Downloaded {len(panel.data)} records")
    
    # Save to CSV for future use
    panel.to_csv('test_4h.csv')
    print("Data saved to test_4h.csv")

# 2. Choose strategy
if use_alm:
    print("\n" + "="*80)
    print("Testing ALM Strategy" + (" (Optimized)" if use_optimized else " (Base)"))
    print("="*80)
    
    # Import ALM strategy
    from strategies.alm import build_alm_strategy, build_alm_strategy_optimized
    from core.backtest import run_backtest, resample_panel_to_4h
    
    # ALM needs 1H and 4H data
    # For simplicity, we'll use the same data for both (or resample)
    panel_1h = panel
    panel_4h = resample_panel_to_4h(panel_1h) if panel_1h.data['timestamp'].dtype == 'object' else panel
    
    # Build strategy
    if use_optimized:
        print("\nBuilding optimized ALM strategy...")
        # Use moderate parameters (balance between turnover reduction and signal generation)
        strategy = build_alm_strategy_optimized(
            panel_1h=panel_1h,
            panel_4h=panel_4h,
            enable_persistence_filter=True,
            persistence_periods=4,        # Moderate: 4 periods
            enable_strength_filter=True,
            strength_threshold=0.5,      # Moderate: 0.5 threshold
            enable_min_holding=True,
            min_holding_hours=8,        # Moderate: 8 hours
            enable_cooldown=True,
            cooldown_hours=4            # Moderate: 4 hours
        )
        
        # Check signal coverage
        signal_values = strategy.data['factor'].abs()
        non_zero = (signal_values > 1e-6).sum()
        total = len(signal_values)
        if total > 0:
            coverage = 100 * non_zero / total
            print(f"  Signal coverage: {non_zero}/{total} ({coverage:.1f}%)")
            if non_zero == 0:
                print("  WARNING: No signals! Try reducing filters or check data compatibility.")
    else:
        print("\nBuilding base ALM strategy...")
        strategy = build_alm_strategy(
            panel_1h=panel_1h,
            panel_4h=panel_4h
        )
    
    # Run backtest
    print("\nRunning backtest...")
    bt_results = run_backtest(
        strategy_signal=strategy,
        panel_1h=panel_1h,
        transaction_cost=(0.001, 0.001),
        initial_capital=100000.0,
        use_inverse_vol_weighting=True,
        save_results=False
    )
    
    print("\nResults:")
    try:
        bt_results.print_summary()
    except Exception as e:
        print(f"  print_summary() failed: {e}")
    
    # Calculate and display turnover
    try:
        turnover_df = bt_results.get_daily_turnover_df()
        if not turnover_df.empty:
            annual_turnover = turnover_df['turnover'].mean() * 365
            print(f"\n{'='*80}")
            print(f"Annual Turnover: {annual_turnover:.2%}")
            print(f"{'='*80}")
        else:
            print("\nWarning: Turnover data is empty")
    except Exception as e:
        print(f"\nWarning: Could not calculate turnover: {e}")
    
    # Display key metrics
    if hasattr(bt_results, 'metrics') and bt_results.metrics:
        metrics = bt_results.metrics
        print("\nKey Metrics:")
        print(f"  Total Return: {metrics.get('total_return', 0):.2%}")
        print(f"  Annual Return: {metrics.get('annual_return', 0):.2%}")
        print(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"  Max Drawdown: {metrics.get('max_drawdown', 0):.2%}")

else:
    print("\n" + "="*80)
    print("Testing Simple Factor Strategy")
    print("="*80)
    
    # Extract data
    open_price = panel['open']
    close = panel['close']
    high = panel['high']
    low = panel['low']
    volume = panel['volume']
    
    # Calculate simple factor: Relative Low with Volume Adjustment
    print("\nCalculating factor...")
    n = 30
    relative_low = (close - ts_min(high, n)) / (ts_max(low, n) - ts_min(high, n))
    vol_ma = ts_mean(volume, n)
    vol_deviation = volume / vol_ma
    factor = relative_low * (1 + 0.5*(1 - vol_deviation))
    
    # Run backtest
    print("Running backtest...")
    bt_results = backtest(
        entry_price_factor=open_price,
        strategy_factor=factor,
        transaction_cost=(0.0003, 0.0003),
        full_rebalance=False,
    )
    
    print("\nResults:")
    bt_results.print_summary()

# Plot equity curve
print("\nPlotting equity curve...")
bt_results.plot_equity(figsize=(16, 10), show_summary=True, show_benchmark=True)