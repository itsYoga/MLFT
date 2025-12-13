# Pyxis-MLFT: Multi-Strategy Cryptocurrency Trading Framework

A comprehensive quantitative trading framework for cryptocurrency markets, featuring the Adaptive Liquid Momentum (ALM) strategy and support for multiple strategy testing.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Strategy Testing](#strategy-testing)
- [Project Structure](#project-structure)
- [ALM Strategy](#alm-strategy)
- [Creating New Strategies](#creating-new-strategies)
- [Live Trading](#live-trading)
- [Performance Analysis](#performance-analysis)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

Pyxis-MLFT is a multi-strategy cryptocurrency trading framework designed for systematic trading on OKX exchange. The framework includes:

- **ALM Strategy**: Adaptive Liquid Momentum strategy with multi-timeframe analysis
- **Modular Architecture**: Easy to add and test new strategies
- **Unified Backtesting**: Common backtest engine for all strategies
- **Risk Management**: Inverse volatility weighting and position management
- **Live Trading Support**: OKX integration for paper and live trading

## ✨ Features

- **Multi-Timeframe Analysis**: 4H trend filtering + 1H entry signals
- **Multiple Filters**: Volatility, volume, funding rate filters
- **Turnover Optimization**: Signal persistence, strength, and cooldown filters
- **Risk Management**: ATR-based stops, trailing stops, inverse volatility weighting
- **Comprehensive Testing**: Unit tests, backtests, stress tests
- **Live Trading**: OKX testnet and mainnet support

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

```bash
# Clone the repository
git clone https://github.com/itsYoga/pysix-MLFT.git
cd pysix-MLFT

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python test_env.py
```

## 🏃 Quick Start

### Test Simple Factor Strategy

```bash
python test.py
```

### Test ALM Strategy

```bash
# Base ALM strategy
python test.py --alm --csv test_4h.csv

# Optimized ALM strategy (lower turnover)
python test.py --alm --optimized --csv test_4h.csv
```

### Run Backtest

```bash
# Using unified backtest script
python scripts/run_backtest.py \
    --strategy alm \
    --symbols BTC ETH SOL \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --cost 0.001
```

## 📊 Strategy Testing

### ALM Strategy Tests

```bash
# Test base strategy
python tests/test_alm.py --type base

# Test optimized strategy
python tests/test_alm.py --type optimized

# Test both (comparison)
python tests/test_alm.py --type both
```

### Using CSV Data

```bash
# Test with local CSV file
python tests/test_with_csv.py test_4h.csv
```

### Stress Testing

```bash
# Test with different transaction costs
python stress_test.py

# Compare base vs optimized
python stress_test.py compare
```

## 📁 Project Structure

```
pysix-MLFT/
├── strategies/              # Strategy implementations
│   ├── alm/                # ALM strategy
│   │   ├── strategy.py              # Base strategy
│   │   └── strategy_optimized.py    # Optimized version
│   └── template/           # Strategy template
│       └── strategy.py
│
├── core/                   # Core modules
│   ├── backtest.py         # Unified backtest engine
│   └── trader.py           # OKX trading interface
│
├── tests/                   # Test scripts
│   ├── test_alm.py         # ALM strategy tests
│   ├── test_with_csv.py    # CSV-based testing
│   └── test_strategy_template.py
│
├── scripts/                 # Utility scripts
│   └── run_backtest.py     # Unified backtest script
│
├── data/                    # Data directory (auto-created)
├── test.py                  # Main test script
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── STRATEGY_ANALYSIS.md     # Detailed strategy analysis
```

## 📈 ALM Strategy

### Strategy Overview

The Adaptive Liquid Momentum (ALM) strategy is a trend-following CTA strategy designed for cryptocurrency markets.

**Core Components:**
1. **4H Trend Filter**: Triple EMA system (EMA 20/50/200)
2. **1H Entry Trigger**: Donchian Channel breakout (20-period)
3. **Filters**: Volatility (ATR), volume confirmation, funding rate
4. **Risk Management**: Inverse volatility weighting
5. **Optimization**: Signal persistence, strength filters, cooldown periods

### Strategy Logic

```
4H Trend Filter (EMA 20/50/200)
    ↓
1H Donchian Breakout Signal
    ↓
Volatility Filter (ATR-based)
    ↓
Volume Confirmation
    ↓
Signal Combination
    ↓
Inverse Volatility Weighting
    ↓
Backtest Execution
```

### Performance Metrics

**Base Strategy:**
- Annual Turnover: ~32,314%
- Signal Coverage: High
- Drawdown: -12.53%

**Optimized Strategy:**
- Annual Turnover: ~8,390% (74% reduction)
- Signal Coverage: 0.1% (very sparse)
- Drawdown: Similar to base

**Note**: Current backtest shows negative returns. See `STRATEGY_ANALYSIS.md` for detailed analysis and improvement suggestions.

### Strategy Parameters

```python
# Base strategy
build_alm_strategy(
    panel_1h=panel_1h,
    panel_4h=panel_4h,
    ema20=20,
    ema50=50,
    ema200=200,
    donchian_window=20,
    atr_window=14,
    volatility_threshold=0.005
)

# Optimized strategy
build_alm_strategy_optimized(
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
```

## 🔧 Creating New Strategies

### Step 1: Copy Template

```bash
cp -r strategies/template strategies/your_strategy_name
```

### Step 2: Implement Strategy

Edit `strategies/your_strategy_name/strategy.py`:

```python
from phandas import *
from typing import Optional

def build_your_strategy(
    panel_1h: Panel,
    panel_4h: Optional[Panel] = None,
    **kwargs
) -> Factor:
    """
    Build your strategy signal
    
    Parameters
    ----------
    panel_1h : Panel
        1H timeframe data panel
    panel_4h : Panel, optional
        4H timeframe data panel
    
    Returns
    -------
    Factor
        Strategy signal factor (positive=long, negative=short, 0=no signal)
    """
    close_1h = panel_1h['close']
    
    # Implement your strategy logic here
    signal_data = close_1h.data.copy()
    signal_data['factor'] = 0.0  # Your signal calculation
    
    return Factor(signal_data, "YourStrategy")
```

### Step 3: Update __init__.py

Edit `strategies/your_strategy_name/__init__.py`:

```python
from .strategy import build_your_strategy
__all__ = ['build_your_strategy']
```

### Step 4: Create Test

```bash
cp tests/test_strategy_template.py tests/test_your_strategy.py
```

Edit the test file and run:

```bash
python tests/test_your_strategy.py
```

## 💹 Live Trading

### Setup OKX API (Testnet)

```bash
export OKX_API_KEY='your_testnet_api_key'
export OKX_SECRET_KEY='your_testnet_secret_key'
export OKX_PASSPHRASE='your_passphrase'
```

### Run Live Trading Script

```bash
python live_trading_setup.py
```

**⚠️ Important**: Always test on OKX testnet for 1-3 months before live trading!

## 📊 Performance Analysis

See `STRATEGY_ANALYSIS.md` for:
- Detailed strategy explanation
- Code structure analysis
- Performance issues and root causes
- Improvement recommendations
- Testing suggestions

## 🛠️ Command Reference

### Testing Commands

| Command | Description |
|---------|------------|
| `python test_env.py` | Verify environment setup |
| `python test.py` | Test simple factor strategy |
| `python test.py --alm` | Test base ALM strategy |
| `python test.py --alm --optimized` | Test optimized ALM strategy |
| `python tests/test_alm.py --type base` | Test base ALM only |
| `python tests/test_alm.py --type optimized` | Test optimized ALM only |

### Backtest Commands

| Command | Description |
|---------|------------|
| `python scripts/run_backtest.py --strategy alm` | Base strategy backtest |
| `python scripts/run_backtest.py --strategy alm_optimized` | Optimized strategy backtest |
| `python alm_backtest.py` | Full backtest workflow |

### Stress Testing

| Command | Description |
|---------|------------|
| `python stress_test.py` | Transaction cost stress test |
| `python stress_test.py compare` | Compare strategies |

## 📝 Requirements

See `requirements.txt` for full list. Key dependencies:

- `phandas>=0.17.0` - Multi-factor trading framework
- `pandas>=1.5.0` - Data manipulation
- `numpy>=1.20.0` - Numerical computing
- `ccxt>=4.0.0` - Cryptocurrency exchange library
- `matplotlib>=3.5.0` - Plotting
- `python-okx>=0.4.0` - OKX API client

## ⚠️ Important Notes

1. **Data Source**: Currently uses Binance, should use OKX for production
2. **Live Trading**: Must test on OKX testnet for 1-3 months first
3. **Transaction Costs**: High turnover strategies need higher cost assumptions (0.1%-0.2%)
4. **Risk Management**: Set stop-losses and position limits
5. **API Limits**: Be aware of exchange API rate limits

## 🐛 Troubleshooting

### Import Errors

```bash
# Ensure you're in project root
cd /path/to/pysix-MLFT

# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Data Fetching Issues

- Check internet connection
- Verify date ranges are valid
- Check asset symbols are correct

### Strategy Test Failures

- Verify strategy function signature
- Check Panel data format
- Review error logs

## 📚 Documentation

- **Strategy Analysis**: See `STRATEGY_ANALYSIS.md` for detailed strategy explanation
- **phandas Docs**: https://phandas.readthedocs.io/
- **phandas GitHub**: https://github.com/quantbai/phandas

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is for educational and research purposes only.

## 🙏 Acknowledgments

- Built on [phandas](https://github.com/quantbai/phandas) framework
- Uses [ccxt](https://github.com/ccxt/ccxt) for exchange integration
- OKX API integration

## 📧 Contact

For questions or issues, please open an issue on GitHub.

---

**Disclaimer**: This software is for educational purposes only. Trading cryptocurrencies involves substantial risk. Past performance does not guarantee future results. Always test thoroughly before live trading.
