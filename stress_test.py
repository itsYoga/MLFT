"""
壓力測試腳本 - 測試策略在不同交易成本下的表現
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from phandas import *
from strategies.alm import build_alm_strategy_optimized
from core.backtest import run_backtest, resample_panel_to_4h
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def stress_test_transaction_costs(
    symbols: List[str] = None,
    start_date: str = '2023-01-01',
    end_date: str = '2024-01-01',
    initial_capital: float = 100000.0,
    cost_scenarios: List[float] = None,
    use_optimized_strategy: bool = True
) -> pd.DataFrame:
    """
    交易成本壓力測試
    
    Parameters
    ----------
    symbols : List[str]
        交易資產列表
    start_date : str
        開始日期
    end_date : str
        結束日期
    initial_capital : float
        初始資金
    cost_scenarios : List[float]
        交易成本場景列表（例如 [0.0003, 0.0005, 0.001, 0.002]）
    use_optimized_strategy : bool
        是否使用優化版策略（降低換手率）
    
    Returns
    -------
    pd.DataFrame
        壓力測試結果
    """
    if symbols is None:
        from strategies.alm import OKX_TOP_15_ASSETS
        symbols = OKX_TOP_15_ASSETS[:5]  # 使用前 5 個資產加快測試
    
    if cost_scenarios is None:
        cost_scenarios = [
            0.0003,  # 0.03% - 基礎場景
            0.0005,  # 0.05% - 保守估計
            0.001,   # 0.10% - 高成本場景
            0.0015,  # 0.15% - 極高成本
            0.002    # 0.20% - 極端場景
        ]
    
    logger.info("=" * 80)
    logger.info("交易成本壓力測試")
    logger.info("=" * 80)
    logger.info(f"測試資產: {symbols}")
    logger.info(f"回測期間: {start_date} 至 {end_date}")
    logger.info(f"成本場景: {[f'{c*100:.2f}%' for c in cost_scenarios]}")
    logger.info(f"使用優化策略: {use_optimized_strategy}")
    logger.info("")
    
    results = []
    
    for i, cost in enumerate(cost_scenarios, 1):
        logger.info(f"[場景 {i}/{len(cost_scenarios)}] 測試交易成本: {cost*100:.2f}%")
        
        try:
            # 獲取數據（只獲取一次，後續重用）
            if i == 1:
                from core.backtest import resample_panel_to_4h
                from phandas import fetch_data, Panel
                
                logger.info("  獲取市場數據...")
                panel_1h = fetch_data(
                    symbols=symbols,
                    timeframe='1h',
                    start_date=start_date,
                    end_date=end_date,
                    sources=['binance']
                )
                
                try:
                    panel_4h = fetch_data(
                        symbols=symbols,
                        timeframe='4h',
                        start_date=start_date,
                        end_date=end_date,
                        sources=['binance']
                    )
                except:
                    logger.info("  從 1H 重採樣到 4H...")
                    panel_4h = resample_panel_to_4h(panel_1h)
            else:
                logger.info("  重用已獲取的數據...")
            
            # 構建策略信號
            if use_optimized_strategy:
                logger.info("  構建優化版策略信號...")
                strategy_signal = build_alm_strategy_optimized(
                    panel_1h=panel_1h,
                    panel_4h=panel_4h,
                    enable_persistence_filter=True,
                    persistence_periods=4,
                    enable_strength_filter=True,
                    strength_threshold=0.5,
                    enable_min_holding=True,
                    min_holding_hours=8,
                    enable_cooldown=True,
                    cooldown_hours=4
                )
            else:
                from strategies.alm import build_alm_strategy
                logger.info("  構建基礎策略信號...")
                strategy_signal = build_alm_strategy(
                    panel_1h=panel_1h,
                    panel_4h=panel_4h
                )
            
            # 計算收益率（用於逆波動率加權）
            close_1h = panel_1h['close']
            returns = close_1h / ts_delay(close_1h, 1) - 1
            
            # 應用逆波動率加權
            from strategies.alm.strategy import apply_inverse_volatility_weighting
            strategy_signal = apply_inverse_volatility_weighting(
                strategy_signal,
                returns,
                window=30 * 24
            )
            
            # 執行回測
            logger.info(f"  執行回測（交易成本: {cost*100:.2f}%）...")
            entry_price = panel_1h['open']
            
            bt_results = backtest(
                entry_price_factor=entry_price,
                strategy_factor=strategy_signal,
                transaction_cost=(cost, cost),
                initial_capital=initial_capital,
                full_rebalance=False,
                neutralization="market",
                auto_run=True
            )
            
            bt_results.calculate_metrics()
            metrics = bt_results.metrics
            
            # 計算換手率
            turnover_df = bt_results.get_daily_turnover_df()
            avg_turnover = turnover_df['turnover'].mean() * 365 if not turnover_df.empty else 0
            
            # 記錄結果
            result = {
                'transaction_cost_pct': cost * 100,
                'total_return': metrics.get('total_return', 0),
                'annual_return': metrics.get('annual_return', 0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'sortino_ratio': metrics.get('sortino_ratio', 0),
                'max_drawdown': metrics.get('max_drawdown', 0),
                'calmar_ratio': metrics.get('calmar_ratio', 0),
                'annual_turnover': avg_turnover,
                'var_95': metrics.get('var_95', 0),
                'cvar': metrics.get('cvar', 0),
                'linearity': metrics.get('linearity', 0)
            }
            
            results.append(result)
            
            logger.info(f"  ✓ 完成 - 總收益: {result['total_return']:.2%}, "
                       f"年化收益: {result['annual_return']:.2%}, "
                       f"換手率: {result['annual_turnover']:.2%}")
            logger.info("")
        
        except Exception as e:
            logger.error(f"  ✗ 場景 {i} 失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue
    
    # 生成結果表格
    df_results = pd.DataFrame(results)
    
    logger.info("=" * 80)
    logger.info("壓力測試結果摘要")
    logger.info("=" * 80)
    logger.info("\n" + df_results.to_string(index=False))
    
    return df_results


def compare_strategies(
    symbols: List[str] = None,
    start_date: str = '2023-01-01',
    end_date: str = '2024-01-01',
    transaction_cost: float = 0.001
) -> Dict:
    """
    對比基礎策略和優化策略的表現
    """
    if symbols is None:
        from strategies.alm import OKX_TOP_15_ASSETS
        symbols = OKX_TOP_15_ASSETS[:5]
    
    logger.info("=" * 80)
    logger.info("策略對比：基礎 vs 優化")
    logger.info("=" * 80)
    
    from core.backtest import resample_panel_to_4h
    from phandas import fetch_data
    
    # 獲取數據
    panel_1h = fetch_data(
        symbols=symbols,
        timeframe='1h',
        start_date=start_date,
        end_date=end_date,
        sources=['binance']
    )
    
    try:
        panel_4h = fetch_data(
            symbols=symbols,
            timeframe='4h',
            start_date=start_date,
            end_date=end_date,
            sources=['binance']
        )
    except:
        panel_4h = resample_panel_to_4h(panel_1h)
    
    results = {}
    
    # 測試基礎策略
    logger.info("\n[1/2] 測試基礎策略...")
    from strategies.alm import build_alm_strategy
    from strategies.alm.strategy import apply_inverse_volatility_weighting
    base_signal = build_alm_strategy(panel_1h=panel_1h, panel_4h=panel_4h)
    close_1h = panel_1h['close']
    returns = close_1h / ts_delay(close_1h, 1) - 1
    base_signal = apply_inverse_volatility_weighting(base_signal, returns)
    
    bt_base = backtest(
        entry_price_factor=panel_1h['open'],
        strategy_factor=base_signal,
        transaction_cost=(transaction_cost, transaction_cost),
        auto_run=True
    )
    bt_base.calculate_metrics()
    
    turnover_base = bt_base.get_daily_turnover_df()
    results['base'] = {
        **bt_base.metrics,
        'annual_turnover': turnover_base['turnover'].mean() * 365 if not turnover_base.empty else 0
    }
    
    # 測試優化策略
    logger.info("\n[2/2] 測試優化策略...")
    opt_signal = build_alm_strategy_optimized(
        panel_1h=panel_1h,
        panel_4h=panel_4h,
        enable_persistence_filter=True,
        enable_strength_filter=True,
        enable_min_holding=True,
        enable_cooldown=True
    )
    opt_signal = apply_inverse_volatility_weighting(opt_signal, returns)
    
    bt_opt = backtest(
        entry_price_factor=panel_1h['open'],
        strategy_factor=opt_signal,
        transaction_cost=(transaction_cost, transaction_cost),
        auto_run=True
    )
    bt_opt.calculate_metrics()
    
    turnover_opt = bt_opt.get_daily_turnover_df()
    results['optimized'] = {
        **bt_opt.metrics,
        'annual_turnover': turnover_opt['turnover'].mean() * 365 if not turnover_opt.empty else 0
    }
    
    # 打印對比
    logger.info("\n" + "=" * 80)
    logger.info("對比結果")
    logger.info("=" * 80)
    
    metrics_to_compare = [
        'total_return', 'annual_return', 'sharpe_ratio', 
        'max_drawdown', 'annual_turnover', 'calmar_ratio'
    ]
    
    for metric in metrics_to_compare:
        base_val = results['base'].get(metric, 0)
        opt_val = results['optimized'].get(metric, 0)
        
        if isinstance(base_val, float) and isinstance(opt_val, float):
            if 'turnover' in metric or 'drawdown' in metric:
                improvement = (base_val - opt_val) / abs(base_val) * 100 if base_val != 0 else 0
            else:
                improvement = (opt_val - base_val) / abs(base_val) * 100 if base_val != 0 else 0
            
            logger.info(f"{metric:20s}: "
                       f"基礎={base_val:10.4f} | "
                       f"優化={opt_val:10.4f} | "
                       f"變化={improvement:+6.2f}%")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'compare':
        # 對比模式
        compare_strategies()
    else:
        # 壓力測試模式
        results_df = stress_test_transaction_costs(
            symbols=None,  # 使用默認
            start_date='2023-01-01',
            end_date='2024-01-01',
            use_optimized_strategy=True
        )
        
        # 保存結果
        results_df.to_csv('stress_test_results.csv', index=False)
        logger.info(f"\n結果已保存至: stress_test_results.csv")

