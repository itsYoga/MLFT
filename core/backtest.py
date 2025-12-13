"""
統一回測模塊 - 支持多個策略
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, List, Optional
from phandas import *
import logging

logger = logging.getLogger(__name__)


def resample_panel_to_4h(panel_1h: Panel) -> Panel:
    """Resample 1H Panel to 4H Panel"""
    df_1h = panel_1h.data.copy()
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
    df_1h = df_1h.set_index('timestamp')
    
    resampled_dfs = []
    for symbol in df_1h['symbol'].unique():
        symbol_data = df_1h[df_1h['symbol'] == symbol].copy()
        resampled = symbol_data.resample('4H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'symbol': 'first'
        })
        resampled_dfs.append(resampled)
    
    df_4h = pd.concat(resampled_dfs).reset_index()
    df_4h = df_4h.sort_values(['symbol', 'timestamp']).reset_index(drop=True)
    return Panel(df_4h)


def run_backtest(
    strategy_signal: Factor,
    panel_1h: Panel,
    transaction_cost: tuple = (0.001, 0.001),
    initial_capital: float = 100000.0,
    use_inverse_vol_weighting: bool = True,
    save_results: bool = True,
    output_dir: str = 'data'
) -> 'Backtester':
    """
    Unified backtest function
    
    Parameters
    ----------
    strategy_signal : Factor
        Strategy signal factor
    panel_1h : Panel
        1H data panel
    transaction_cost : tuple
        Transaction cost (buy, sell)
    initial_capital : float
        Initial capital
    use_inverse_vol_weighting : bool
        Whether to use inverse volatility weighting
    save_results : bool
        Whether to save results
    output_dir : str
        Output directory
    
    Returns
    -------
    Backtester
        Backtest results
    """
    entry_price = panel_1h['open']
    
    # Apply inverse volatility weighting (optional)
    if use_inverse_vol_weighting:
        close_1h = panel_1h['close']
        returns = close_1h / ts_delay(close_1h, 1) - 1
        
        from strategies.alm.strategy import apply_inverse_volatility_weighting
        strategy_signal = apply_inverse_volatility_weighting(
            strategy_signal, returns, window=30 * 24
        )
    
    # Run backtest
    bt_results = backtest(
        entry_price_factor=entry_price,
        strategy_factor=strategy_signal,
        transaction_cost=transaction_cost,
        initial_capital=initial_capital,
        full_rebalance=False,
        neutralization="market",
        auto_run=True
    )
    
    bt_results.calculate_metrics()
    
    if save_results:
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, f"{strategy_signal.name}_report.txt")
        generate_performance_report(bt_results, report_path)
    
    return bt_results


def generate_performance_report(bt_results: 'Backtester', output_path: Optional[str] = None) -> str:
    """Generate performance report"""
    metrics = bt_results.metrics
    history_df = bt_results.portfolio.get_history_df()
    
    report_lines = [
        "=" * 80,
        f"Strategy: {bt_results.strategy_factor.name}",
        "=" * 80,
        "",
        f"Backtest Period: {history_df.index[0].strftime('%Y-%m-%d')} to {history_df.index[-1].strftime('%Y-%m-%d')}",
        "",
        "Return Metrics",
        f"Total Return: {metrics.get('total_return', 0):.2%}",
        f"Annual Return: {metrics.get('annual_return', 0):.2%}",
        "",
        "Risk Metrics",
        f"Annual Volatility: {metrics.get('annual_volatility', 0):.2%}",
        f"Max Drawdown: {metrics.get('max_drawdown', 0):.2%}",
        f"VaR (95%): {metrics.get('var_95', 0):.2%}",
        "",
        "Risk-Adjusted Returns",
        f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}",
        f"Sortino Ratio: {metrics.get('sortino_ratio', 0):.2f}",
        f"Calmar Ratio: {metrics.get('calmar_ratio', 0):.2f}",
    ]
    
    report = "\n".join(report_lines)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Report saved to: {output_path}")
    
    return report

