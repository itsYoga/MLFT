# 腳本目錄說明

## 📁 目錄結構

```
scripts/
├── backtest/                # 回測腳本
│   └── run_full_backtest.py    # 完整回測腳本
│
├── utils/                   # 工具腳本
│   └── test_env.py              # 環境測試
│
└── run_backtest.py         # 統一回測腳本（舊版，保留兼容性）
```

## 🚀 主要腳本

### `backtest/run_full_backtest.py`
完整的 ALM 策略回測腳本。

**功能**：
- 數據獲取或載入
- 策略信號生成
- 回測執行
- 績效分析
- 結果報告

**運行方式**：
```bash
# 使用 CSV 數據
python scripts/backtest/run_full_backtest.py --csv test_4h.csv --strategy improved

# 從交易所獲取數據
python scripts/backtest/run_full_backtest.py --symbols BTC ETH SOL --strategy improved

# 繪製權益曲線
python scripts/backtest/run_full_backtest.py --csv test_4h.csv --strategy improved --plot
```

### `utils/test_env.py`
環境測試腳本，驗證所有依賴和模塊是否正常工作。

**運行方式**：
```bash
python scripts/utils/test_env.py
```

### `run_backtest.py`
統一回測腳本（保留用於兼容性）。

**運行方式**：
```bash
python scripts/run_backtest.py --strategy alm --symbols BTC ETH SOL
```

