"""
使用本地 CSV 文件測試策略
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from phandas import Panel
from strategies.alm import build_alm_strategy
from core.backtest import run_backtest


def test_with_csv(csv_file='test_4h.csv', plot=True):
    """Test strategy using CSV file"""
    csv_path = os.path.join(project_root, csv_file)
    
    if not os.path.exists(csv_path):
        print(f"Error: File not found {csv_path}")
        return
    
    print("=" * 80)
    print(f"Testing with local data file: {csv_file}")
    print("=" * 80)
    
    print(f"\n[1/4] Loading data...")
    try:
        panel = Panel.from_csv(csv_path)
        print(f"  ✓ Loaded: {len(panel.data)} records")
        
        # Display data info
        symbols = panel.data['symbol'].unique()
        print(f"  Symbols: {list(symbols)}")
        print(f"  Date range: {panel.data['timestamp'].min()} to {panel.data['timestamp'].max()}")
        
        # Check required columns
        required = ['open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required if c not in panel.data.columns]
        if missing:
            print(f"  ✗ Missing columns: {missing}")
            return
        
    except Exception as e:
        print(f"  ✗ Load failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n[2/4] Building strategy...")
    try:
        # Use same data for 1H and 4H (simplified)
        strategy = build_alm_strategy(
            panel_1h=panel,
            panel_4h=panel
        )
        print(f"  ✓ Strategy built successfully")
    except Exception as e:
        print(f"  ✗ Strategy build failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n[3/4] Running backtest...")
    try:
        bt = run_backtest(
            strategy_signal=strategy,
            panel_1h=panel,
            transaction_cost=(0.001, 0.001),
            initial_capital=100000.0,
            use_inverse_vol_weighting=True,
            save_results=False
        )
        print(f"  ✓ Backtest completed")
    except Exception as e:
        print(f"  ✗ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n[4/4] Results:")
    try:
        bt.print_summary()
    except Exception as e:
        print(f"  print_summary() failed: {e}")
    
    # Display key metrics
    if hasattr(bt, 'metrics') and bt.metrics:
        metrics = bt.metrics
        print("\nKey Metrics:")
        print(f"  Total Return: {metrics.get('total_return', 0):.2%}")
        print(f"  Annual Return: {metrics.get('annual_return', 0):.2%}")
        print(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"  Max Drawdown: {metrics.get('max_drawdown', 0):.2%}")
        print(f"  Annual Volatility: {metrics.get('annual_volatility', 0):.2%}")
    else:
        print("  Warning: Cannot get metrics, trying calculate_metrics()...")
        try:
            bt.calculate_metrics()
            metrics = bt.metrics
            print("\nKey Metrics:")
            print(f"  Total Return: {metrics.get('total_return', 0):.2%}")
            print(f"  Annual Return: {metrics.get('annual_return', 0):.2%}")
            print(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        except Exception as e2:
            print(f"  calculate_metrics() also failed: {e2}")
    
    # Plot equity curve (this is the image/plot feature)
    if plot:
        print(f"\n[5/5] Plotting equity curve...")
        try:
            bt.plot_equity(figsize=(16, 10), show_summary=True, show_benchmark=True)
            print(f"  ✓ Equity curve plotted")
        except Exception as e:
            print(f"  ✗ Plot failed: {e}")
            import traceback
            traceback.print_exc()
    
    return bt


if __name__ == "__main__":
    import sys
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'test_4h.csv'
    plot = '--no-plot' not in sys.argv
    test_with_csv(csv_file, plot=plot)

