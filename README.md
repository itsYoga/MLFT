# MLFT - Multi-Strategy Trading Framework

A modular cryptocurrency trading framework for OKX exchange with backtesting and live trading support.

## Features

- **Backtesting Engine**: Unified backtest module supporting custom strategies
- **OKX Trading Interface**: Full support for perpetual swaps with portfolio rebalancing
- **Risk Management**: Volatility targeting and rebalancing buffers
- **Multi-timeframe Support**: Data resampling from 1H to 4H

## Installation

```bash
# Clone repository
git clone https://github.com/itsYoga/MLFT.git
cd MLFT

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Project Structure

```
MLFT/
├── core/                   # Core modules
│   ├── backtest.py         # Unified backtest engine
│   ├── trader.py           # OKX trading interface
│   └── risk.py             # Risk management module
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Core Modules

### Backtesting (core/backtest.py)

```python
from core.backtest import run_backtest, resample_panel_to_4h

# Resample 1H data to 4H
panel_4h = resample_panel_to_4h(panel_1h)

# Run backtest with your strategy signal
results = run_backtest(
    strategy_signal=your_signal,
    panel_1h=panel_1h,
    transaction_cost=(0.001, 0.001),
    initial_capital=100000.0
)
```

### Trading (core/trader.py)

```python
from core.trader import OKXTrader, rebalance

# Initialize trader
trader = OKXTrader(
    api_key='your_api_key',
    secret_key='your_secret_key',
    passphrase='your_passphrase',
    use_testnet=True  # Use testnet first
)

# Validate account configuration
validation = trader.validate_account_config()

# Get account balance
balance = trader.get_account_balance_info()

# Rebalance portfolio
target_weights = {'BTC': 0.3, 'ETH': 0.2, 'SOL': 0.1}
result = rebalance(
    target_weights=target_weights,
    trader=trader,
    budget=balance['total_equity']
)
```

### Risk Management (core/risk.py)

```python
from core.risk import calculate_volatility_targeted_weights, apply_rebalancing_buffer

# Calculate volatility-targeted weights
target_weights = calculate_volatility_targeted_weights(
    returns=returns_factor,
    target_volatility=0.15
)

# Apply rebalancing buffer
final_weights = apply_rebalancing_buffer(
    current_weights=current,
    target_weights=target,
    buffer_pct=0.10
)
```

## Dependencies

Key dependencies (see requirements.txt for full list):

- `phandas>=0.17.0` - Multi-factor trading framework
- `pandas>=1.5.0` - Data processing
- `numpy>=1.20.0` - Numerical computing
- `python-okx>=0.4.0` - OKX API client

## Live Trading

Before live trading:
1. Test on OKX testnet for at least 1-3 months
2. Set appropriate position limits
3. Configure stop-loss settings
4. Only trade with funds you can afford to lose

Set API credentials:
```bash
export OKX_API_KEY='your_api_key'
export OKX_SECRET_KEY='your_secret_key'
export OKX_PASSPHRASE='your_passphrase'
```

## License

This project is for educational and research purposes only.

## Disclaimer

Trading cryptocurrencies involves significant risk. Past performance does not guarantee future results. Test thoroughly before live trading.
