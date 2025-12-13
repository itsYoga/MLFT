# 測試目錄說明

## 📁 目錄結構

```
tests/
├── unit/                    # 單元測試
│   └── test_alm_strategies.py    # ALM 策略單元測試
│
├── integration/             # 整合測試
│   ├── test_strategy_template.py  # 通用測試模板
│   └── test_with_csv.py          # CSV 數據測試
│
└── performance/             # 性能測試
    ├── test_strategy_comparison.py  # 策略對比測試
    └── test_stress.py              # 壓力測試
```

## 🧪 測試類型

### 單元測試 (`unit/`)
測試單個策略函數的功能正確性。

**運行方式**：
```bash
# 測試改進版策略（推薦）
python tests/unit/test_alm_strategies.py --type improved

# 測試所有版本
python tests/unit/test_alm_strategies.py --type all --plot
```

### 整合測試 (`integration/`)
測試策略與回測引擎的整合。

**運行方式**：
```bash
# 使用 CSV 數據測試
python tests/integration/test_with_csv.py test_4h.csv improved

# 使用通用模板測試
python tests/integration/test_strategy_template.py
```

### 性能測試 (`performance/`)
測試策略在不同條件下的性能表現。

**運行方式**：
```bash
# 策略對比測試
python tests/performance/test_strategy_comparison.py --csv test_4h.csv --plot

# 壓力測試（不同交易成本）
python tests/performance/test_stress.py --csv test_4h.csv --strategy improved
```

## 📝 測試文件說明

### `unit/test_alm_strategies.py`
- 測試基礎版、優化版、改進版策略
- 支援單獨測試或對比測試
- 可選繪製權益曲線

### `integration/test_with_csv.py`
- 使用本地 CSV 文件快速測試
- 支援不同策略類型
- 適合離線測試和快速驗證

### `integration/test_strategy_template.py`
- 通用測試模板
- 可被其他測試文件導入使用
- 提供統一的測試框架

### `performance/test_strategy_comparison.py`
- 對比不同策略版本的性能
- 生成對比報告
- 可選繪製對比圖表

### `performance/test_stress.py`
- 測試策略在不同交易成本下的表現
- 壓力測試場景
- 生成成本敏感性報告

## 🚀 快速開始

### 1. 環境測試
```bash
python scripts/utils/test_env.py
```

### 2. 快速測試（使用 CSV）
```bash
python tests/integration/test_with_csv.py test_4h.csv improved
```

### 3. 完整測試
```bash
python tests/unit/test_alm_strategies.py --type improved --plot
```

### 4. 性能對比
```bash
python tests/performance/test_strategy_comparison.py --csv test_4h.csv
```

## 📊 測試數據

測試使用 `test_4h.csv` 文件（位於專案根目錄）。

如果沒有此文件，可以：
1. 運行範例腳本自動下載
2. 手動下載數據並保存為 CSV
3. 使用 `fetch_data()` 函數獲取數據

## ⚠️ 注意事項

1. **數據文件**：確保 `test_4h.csv` 存在於專案根目錄
2. **虛擬環境**：確保已啟動虛擬環境
3. **依賴套件**：確保所有依賴已安裝（`pip install -r requirements.txt`）
4. **網路連接**：如果使用線上數據，需要網路連接

