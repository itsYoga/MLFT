"""
ALM (Adaptive Liquid Momentum) 策略
"""

from .strategy import (
    OKX_TOP_15_ASSETS,
    calculate_ema,
    calculate_atr,
    calculate_donchian_breakout,
    calculate_4h_trend_filter,
    build_alm_strategy
)

from .strategy_optimized import (
    build_alm_strategy_optimized,
    apply_signal_persistence_filter,
    apply_signal_strength_filter,
    apply_min_holding_period_filter,
    apply_cooldown_filter
)

from .strategy_improved import (
    build_alm_strategy_improved,
    calculate_weighted_signal_score,
    apply_signal_smoothing,
    calculate_stop_loss,
    calculate_take_profit,
    calculate_trailing_stop,
    apply_exit_logic,
    calculate_adaptive_parameters
)

from .strategy_advanced import build_alm_strategy_advanced
from .indicators import (
    efficiency_ratio,
    choppiness_index,
    calculate_adx,
    adaptive_donchian_window,
    signal_strength_score
)
from .regime import detect_regime

# 嘗試導入超保守策略
try:
    from .strategy_ultra_conservative import (
        build_alm_strategy_ultra_conservative,
        apply_ultra_wide_hysteresis
    )
    _has_ultra_conservative = True
except ImportError:
    _has_ultra_conservative = False

__all__ = [
    'OKX_TOP_15_ASSETS',
    'build_alm_strategy',
    'build_alm_strategy_optimized',
    'build_alm_strategy_improved',
    'calculate_ema',
    'calculate_atr',
    'calculate_donchian_breakout',
    'calculate_4h_trend_filter',
    'apply_signal_persistence_filter',
    'apply_signal_strength_filter',
    'apply_min_holding_period_filter',
    'apply_cooldown_filter',
    'calculate_weighted_signal_score',
    'apply_signal_smoothing',
    'calculate_stop_loss',
    'calculate_take_profit',
    'calculate_trailing_stop',
    'apply_exit_logic',
    'calculate_adaptive_parameters',
    'build_alm_strategy_advanced',
    'efficiency_ratio',
    'choppiness_index',
    'calculate_adx',
    'adaptive_donchian_window',
    'signal_strength_score',
    'detect_regime',
]

# 如果超保守策略可用，添加到 __all__
if _has_ultra_conservative:
    __all__.extend([
        'build_alm_strategy_ultra_conservative',
        'apply_ultra_wide_hysteresis'
    ])

