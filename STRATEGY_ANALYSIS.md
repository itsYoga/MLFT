# ALM Strategy Detailed Analysis and Code Explanation

## Executive Summary

The Adaptive Liquid Momentum (ALM) strategy is a multi-timeframe trend-following CTA strategy designed for cryptocurrency markets. Current backtest results show:
- **Total Return: -10.68%**
- **Annual Return: -16.16%**
- **Sharpe Ratio: -2.15**
- **Max Drawdown: -12.53%**
- **Annual Turnover: 32,314.54%** (Base) / **8,389.72%** (Optimized)

The strategy is losing money despite having lower drawdown than benchmark. This document provides a comprehensive analysis of the strategy logic, code structure, and potential issues.

---

## 1. Strategy Overview

### 1.1 Core Concept

ALM is a **trend-following** strategy that combines:
- **Multi-timeframe analysis**: 4H for trend direction, 1H for entry timing
- **Breakout signals**: Donchian Channel breakout for entry triggers
- **Multiple filters**: Volatility, volume, and funding rate filters
- **Risk management**: Inverse volatility weighting for portfolio construction

### 1.2 Strategy Logic Flow

```
1. 4H Trend Filter (EMA 20/50/200)
   ↓
2. 1H Donchian Breakout Signal
   ↓
3. Volatility Filter (ATR-based)
   ↓
4. Volume Confirmation
   ↓
5. Funding Rate Filter (if available)
   ↓
6. Signal Combination (AND logic)
   ↓
7. Inverse Volatility Weighting
   ↓
8. Backtest Execution
```

---

## 2. Detailed Code Structure

### 2.1 Main Strategy File: `strategies/alm/strategy.py`

#### 2.1.1 Trend Filter (`calculate_4h_trend_filter`)

**Purpose**: Identify strong bullish/bearish trends using triple EMA system.

**Logic**:
```python
# Bullish: Price > EMA20 > EMA50 > EMA200
bullish_trend = (close_4h > ema20) * (ema20 > ema50) * (ema50 > ema200)

# Bearish: Price < EMA20 < EMA50 < EMA200
bearish_trend = (close_4h < ema20) * (ema20 < ema50) * (ema50 < ema200)
```

**Issues**:
- Very strict condition: All three EMAs must be perfectly aligned
- In sideways markets, this generates zero signals
- No partial trend recognition (e.g., price above EMA200 but EMAs not aligned)

#### 2.1.2 Donchian Breakout (`calculate_donchian_breakout`)

**Purpose**: Generate entry signals when price breaks above/below recent highs/lows.

**Logic**:
```python
upper_band = ts_max(high, window)  # 20-period high
lower_band = ts_min(low, window)    # 20-period low

long_signal = close > ts_delay(upper_band, 1)   # Breakout above
short_signal = close < ts_delay(lower_band, 1)  # Breakout below
```

**Issues**:
- **Whipsaw-prone**: In choppy markets, generates many false breakouts
- **No confirmation**: Single-bar breakout can be noise
- **Fixed window**: 20 periods may not be optimal for all assets/timeframes

#### 2.1.3 Volatility Filter (`calculate_volatility_filter`)

**Purpose**: Avoid trading in low-volatility "dead" markets.

**Logic**:
```python
volatility_ratio = atr / close
volatility_filter = volatility_ratio > threshold  # Default: 0.005 (0.5%)
```

**Issues**:
- **Too restrictive**: 0.5% threshold filters out many valid trading opportunities
- **No upper bound**: Doesn't filter extremely high volatility (risk management)

#### 2.1.4 Volume Confirmation

**Purpose**: Confirm breakouts with volume.

**Logic**:
```python
volume_ma = ts_mean(volume, 20)
volume_confirmation = volume > (volume_ma * 1.5)  # 1.5x average
```

**Issues**:
- **Fixed multiplier**: 1.5x may be too high/low depending on market conditions
- **No volume quality check**: Doesn't distinguish between buying/selling volume

#### 2.1.5 Signal Combination (`build_alm_strategy`)

**Logic**:
```python
long_signal = (
    bullish_trend_1h *      # 4H trend filter
    long_breakout *         # Donchian breakout
    volatility_filter *     # ATR filter
    volume_confirmation *   # Volume filter
    can_long_funding        # Funding rate filter
)
```

**Critical Issues**:
1. **All conditions must be True**: Using multiplication (`*`) means ALL filters must pass
   - If ANY filter fails, signal = 0
   - This creates extremely sparse signals
   - In backtest: Only 0.1% signal coverage (8/6692 signals)

2. **No signal persistence**: Signals are binary (1 or 0), no holding logic
   - When signal disappears, position is immediately closed
   - Causes extreme turnover (32,314% annually)

3. **No exit logic**: Strategy only generates entry signals
   - No stop-loss, take-profit, or trailing stop
   - Positions held until signal reverses (causes large drawdowns)

### 2.2 Optimized Strategy: `strategies/alm/strategy_optimized.py`

#### 2.2.1 Signal Persistence Filter

**Purpose**: Require signals to persist for N periods before acting.

**Logic**:
```python
# Signal must persist for 4 periods before becoming active
if signal appears and persists >= min_periods:
    activate signal
```

**Effect**: Reduces turnover from 32,314% to 8,390% (74% reduction)

**Remaining Issues**:
- Still very high turnover (8,390% = ~23x per day)
- Signal coverage drops to 0.1% (too few signals)

#### 2.2.2 Signal Strength Filter

**Purpose**: Only trade strong signals (absolute value > threshold).

**Logic**:
```python
filtered_signal = np.where(
    np.abs(signal) >= strength_threshold,  # Default: 0.5
    signal,
    0.0
)
```

**Issues**:
- Binary threshold: Signals just below threshold are completely ignored
- No gradual scaling: Could use soft threshold instead

#### 2.2.3 Minimum Holding Period

**Purpose**: Prevent rapid position reversals.

**Logic**:
```python
# Once position opened, must hold for min_holding_hours (default: 8)
if position_age < min_holding_hours:
    prevent_close
```

**Issues**:
- Fixed period: Doesn't adapt to market conditions
- May hold losing positions too long

#### 2.2.4 Cooldown Period

**Purpose**: Wait after closing position before reopening.

**Logic**:
```python
# After closing position, wait cooldown_hours (default: 4) before new entry
if time_since_close < cooldown_hours:
    prevent_entry
```

**Effect**: Helps reduce whipsaw but may miss valid re-entry opportunities

### 2.3 Backtest Engine: `core/backtest.py`

#### 2.3.1 Inverse Volatility Weighting

**Purpose**: Allocate capital based on inverse volatility (risk parity).

**Logic**:
```python
volatility = ts_std_dev(returns, window) * sqrt(365*24)  # Annualized
inv_vol = 1.0 / (volatility + 1e-10)
weights = inv_vol / inv_vol.mean()  # Cross-sectional normalization
weighted_signal = strategy_signal * weights
```

**Issues**:
- **Frequent rebalancing**: Weights change every period → high turnover
- **No transaction cost consideration**: Rebalances even when weights change slightly
- **Window size**: 30*24 = 720 hours may be too short for stable volatility estimates

#### 2.3.2 Backtest Execution

**Configuration**:
```python
backtest(
    entry_price_factor=open,           # Entry at open price
    strategy_factor=strategy_signal,   # Signal factor
    transaction_cost=(0.001, 0.001),   # 0.1% per trade
    full_rebalance=False,              # Incremental rebalancing
    neutralization="market",            # Market-neutral
    auto_run=True
)
```

**Issues**:
- **Entry at open**: Assumes perfect execution (no slippage)
- **Transaction cost**: 0.1% may be too low for high-turnover strategy
- **Market neutralization**: May reduce returns in trending markets
- **No slippage model**: Doesn't account for liquidity impact

---

## 3. Why the Strategy is Losing Money

### 3.1 Primary Issues

#### Issue 1: Extreme Signal Sparsity
- **Problem**: Only 0.1% signal coverage (8 signals out of 6,692 periods)
- **Impact**: Strategy is mostly in cash, missing trading opportunities
- **Root Cause**: Too many strict filters combined with AND logic

#### Issue 2: Excessive Turnover
- **Problem**: 32,314% annual turnover = ~88x per day
- **Impact**: Transaction costs eat profits
  - At 0.1% per trade: 32,314% * 0.1% = 32.3% annual cost
  - Strategy needs >32% annual return just to break even
- **Root Cause**: 
  - No signal persistence in base strategy
  - Inverse volatility weighting causes frequent rebalancing
  - Binary signals (1/0) cause immediate position changes

#### Issue 3: No Exit Strategy
- **Problem**: Positions held until signal reverses
- **Impact**: Large drawdowns when trends reverse
- **Root Cause**: Strategy only generates entry signals, no stop-loss/take-profit

#### Issue 4: Whipsaw in Choppy Markets
- **Problem**: Donchian breakout generates false signals in sideways markets
- **Impact**: Multiple small losses from false breakouts
- **Root Cause**: No trend strength confirmation, fixed window size

#### Issue 5: Over-Filtering
- **Problem**: All filters must pass (AND logic)
- **Impact**: Very few signals, missing valid opportunities
- **Root Cause**: No weighted/scoring system, binary filters

### 3.2 Secondary Issues

#### Issue 6: Timeframe Mismatch
- **Problem**: Using daily data (`timeframe='1d'`) but strategy designed for 1H/4H
- **Impact**: 
  - EMA periods (20/50/200) too long for daily data
  - Donchian window (20) too short for daily data
  - Signal generation logic may not work correctly

#### Issue 7: Market Neutralization
- **Problem**: `neutralization="market"` removes market beta
- **Impact**: In trending markets, strategy can't capture beta returns
- **Root Cause**: Designed for relative performance, not absolute returns

#### Issue 8: No Position Sizing
- **Problem**: All positions same size (after volatility weighting)
- **Impact**: No Kelly criterion or risk-based sizing
- **Root Cause**: Simple inverse volatility weighting, no confidence scaling

---

## 4. Code Quality Issues

### 4.1 Data Handling

**Issue**: 4H to 1H broadcasting is simplified
```python
# Current: Assumes data already aligned
bullish_trend_1h = bullish_trend_4h  # Line 431-432

# Should be:
bullish_trend_1h = broadcast_4h_to_1h(bullish_trend_4h, panel_1h.index)
```

**Impact**: Signals may not align correctly with 1H data

### 4.2 Error Handling

**Issue**: Minimal error handling in signal combination
```python
try:
    long_val = long_df.get((timestamp, symbol), 0)
    short_val = short_df.get((timestamp, symbol), 0)
except:
    pass  # Silent failure
```

**Impact**: Missing signals may go unnoticed

### 4.3 Funding Rate Filter

**Issue**: Funding rate filter not implemented
```python
if funding_rates:
    pass  # Not implemented
```

**Impact**: Missing important contrarian signal

### 4.4 Performance

**Issue**: Inefficient DataFrame operations in loops
```python
for idx, row in signal_data.iterrows():  # Slow!
    # Signal combination logic
```

**Impact**: Slow execution for large datasets

---

## 5. Recommended Improvements

### 5.1 Immediate Fixes (High Priority)

#### Fix 1: Reduce Filter Strictness
**Current**: All filters must pass (AND logic)
**Proposed**: Use weighted scoring system
```python
# Instead of: signal = filter1 * filter2 * filter3
# Use: signal_score = (w1*filter1 + w2*filter2 + w3*filter3) / sum(weights)
# Then: signal = 1 if score > threshold, else 0
```

**Expected Impact**: Increase signal coverage from 0.1% to 5-10%

#### Fix 2: Add Exit Logic
**Proposed**: Implement stop-loss and take-profit
```python
# Stop-loss: Close if loss > 2 * ATR
# Take-profit: Close if profit > 3 * ATR
# Trailing stop: Move stop to breakeven after 1.5 * ATR profit
```

**Expected Impact**: Reduce drawdowns, improve risk-adjusted returns

#### Fix 3: Fix Timeframe Handling
**Proposed**: Properly resample and broadcast 4H to 1H
```python
# Use broadcast_4h_to_1h() function instead of direct assignment
bullish_trend_1h = broadcast_4h_to_1h(bullish_trend_4h, panel_1h.data['timestamp'])
```

**Expected Impact**: Correct signal alignment

#### Fix 4: Reduce Turnover
**Proposed**: 
- Increase minimum holding period to 24 hours
- Add signal smoothing (moving average of signals)
- Reduce rebalancing frequency for volatility weights

**Expected Impact**: Reduce turnover from 8,390% to <1,000%

### 5.2 Medium-Term Improvements

#### Improvement 1: Adaptive Parameters
- Adjust Donchian window based on volatility regime
- Adjust EMA periods based on market conditions
- Dynamic threshold adjustment

#### Improvement 2: Better Entry Logic
- Require confirmation: 2-3 consecutive bars in same direction
- Add momentum filter: Price change rate
- Volume profile analysis: Support/resistance levels

#### Improvement 3: Position Management
- Kelly criterion for position sizing
- Confidence-based sizing (stronger signals = larger positions)
- Correlation-based diversification

#### Improvement 4: Market Regime Detection
- Identify trending vs. choppy markets
- Adjust strategy parameters accordingly
- Reduce trading in unfavorable regimes

### 5.3 Long-Term Enhancements

#### Enhancement 1: Machine Learning Integration
- Use ML to predict signal quality
- Adaptive filter weights
- Regime classification

#### Enhancement 2: Multi-Asset Optimization
- Cross-asset momentum signals
- Correlation-based filtering
- Sector rotation logic

#### Enhancement 3: Advanced Risk Management
- Dynamic stop-loss based on volatility
- Portfolio-level risk limits
- Drawdown-based position reduction

---

## 6. Testing Recommendations

### 6.1 Parameter Sensitivity Analysis
Test different combinations of:
- EMA periods: (10/30/100), (20/50/200), (30/60/250)
- Donchian window: 10, 20, 30, 40
- Volatility threshold: 0.003, 0.005, 0.01
- Volume multiplier: 1.2, 1.5, 2.0

### 6.2 Market Regime Testing
- Test in trending markets (2020-2021)
- Test in choppy markets (2022)
- Test in recovery markets (2023-2024)

### 6.3 Transaction Cost Sensitivity
- Test with 0.05%, 0.1%, 0.2%, 0.5% transaction costs
- Add slippage model (0.1-0.5% depending on liquidity)

### 6.4 Walk-Forward Analysis
- Use rolling window optimization
- Test out-of-sample performance
- Avoid overfitting

---

## 7. Code Structure Summary

```
pyxis-MLFT/
├── strategies/
│   └── alm/
│       ├── __init__.py              # Exports
│       ├── strategy.py              # Base ALM strategy
│       └── strategy_optimized.py   # Optimized version with filters
├── core/
│   ├── backtest.py                  # Unified backtest engine
│   └── trader.py                    # Live trading interface
├── tests/
│   ├── test_alm.py                  # ALM strategy tests
│   └── test_with_csv.py             # CSV-based testing
└── test.py                          # Main test script
```

### Key Functions:

1. **`build_alm_strategy()`** (`strategy.py:361`)
   - Main strategy builder
   - Combines all filters
   - Returns Factor with signals

2. **`build_alm_strategy_optimized()`** (`strategy_optimized.py:269`)
   - Adds turnover reduction filters
   - Applies persistence, strength, holding, cooldown filters

3. **`run_backtest()`** (`core/backtest.py:39`)
   - Executes backtest
   - Applies inverse volatility weighting
   - Returns Backtester object

4. **`calculate_4h_trend_filter()`** (`strategy.py:179`)
   - Triple EMA trend detection
   - Returns bullish/bearish signals

5. **`calculate_donchian_breakout()`** (`strategy.py:141`)
   - Breakout signal generation
   - Returns long/short signals

---

## 8. Critical Questions for Improvement

1. **Why is signal coverage only 0.1%?**
   - Are filters too strict?
   - Is data timeframe correct?
   - Are signals being generated but filtered out?

2. **Why is turnover so high even with optimizations?**
   - Is inverse volatility weighting causing frequent rebalancing?
   - Are signals flipping too quickly?
   - Is there a bug in position management?

3. **Why negative returns despite lower drawdown?**
   - Are transaction costs too high?
   - Are signals low quality?
   - Is market regime unfavorable?

4. **What is the optimal balance between signal quality and quantity?**
   - Should we relax filters to get more signals?
   - Or tighten filters further to improve quality?

5. **Is the strategy logic fundamentally flawed?**
   - Trend-following may not work in current market
   - Multi-timeframe approach may be too complex
   - Breakout strategy may be outdated

---

## 9. Next Steps

1. **Debug signal generation**: Add logging to see why signals are sparse
2. **Fix timeframe handling**: Properly implement 4H→1H broadcasting
3. **Add exit logic**: Implement stop-loss and take-profit
4. **Reduce turnover**: Increase holding periods, add signal smoothing
5. **Test parameter sensitivity**: Find optimal filter combinations
6. **Add regime detection**: Adjust strategy based on market conditions
7. **Improve risk management**: Better position sizing and portfolio limits

---

## 10. Conclusion

The ALM strategy has a solid theoretical foundation but suffers from implementation issues:
- **Over-filtering** leads to sparse signals
- **No exit logic** causes large drawdowns
- **High turnover** erodes profits through transaction costs
- **Timeframe mismatch** may cause signal misalignment

**Priority fixes**:
1. Reduce filter strictness (use scoring instead of AND logic)
2. Add proper exit logic (stop-loss, take-profit)
3. Fix timeframe handling (proper 4H→1H broadcasting)
4. Reduce turnover (longer holding periods, less frequent rebalancing)

With these fixes, the strategy should improve significantly. However, trend-following strategies inherently struggle in choppy markets, so regime detection and adaptive parameters are crucial for long-term success.

