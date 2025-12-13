# 範例目錄

## 📁 文件說明

### `example_alm.py`
完整的 ALM 策略使用範例，包含：
- 範例 1：基本回測
- 範例 2：改進版策略（推薦）

**運行方式**：
```bash
# 運行範例 2（推薦）
python examples/example_alm.py 2

# 運行範例 1
python examples/example_alm.py 1
```

### `example_quick_test.py`
快速測試範例，使用本地 CSV 數據。

**運行方式**：
```bash
python examples/example_quick_test.py --csv test_4h.csv --strategy improved
```

## 🎯 使用建議

1. **初學者**：從 `example_alm.py` 開始
2. **快速測試**：使用 `example_quick_test.py`
3. **完整回測**：使用 `scripts/backtest/run_full_backtest.py`

