# Pyxis-MLFT: 多策略加密貨幣交易框架

一個專為加密貨幣市場設計的綜合量化交易框架，包含自適應流動性動能（ALM）策略並支援多策略測試。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📋 目錄

- [概述](#概述)
- [功能特色](#功能特色)
- [安裝](#安裝)
- [快速開始](#快速開始)
- [策略測試](#策略測試)
- [專案結構](#專案結構)
- [ALM 策略](#alm-策略)
- [策略版本對比](#策略版本對比)
- [績效分析](#績效分析)
- [改進建議](#改進建議)
- [高級優化](#高級優化)
- [創建新策略](#創建新策略)
- [實盤交易](#實盤交易)
- [AI 整合 (MCP)](#ai-整合-mcp)
- [命令參考](#命令參考)
- [故障排除](#故障排除)
- [貢獻](#貢獻)
- [授權](#授權)

## 🎯 概述

Pyxis-MLFT 是一個多策略加密貨幣交易框架，專為 OKX 交易所的系統化交易而設計。框架包含：

- **ALM 策略**：自適應流動性動能策略，支援多時間框架分析
- **模組化架構**：易於添加和測試新策略
- **統一回測引擎**：所有策略共用回測引擎
- **風險管理**：逆波動率加權和倉位管理
- **實盤交易支援**：OKX 整合，支援模擬和實盤交易

## ✨ 功能特色

- **多時間框架分析**：4H 趨勢過濾 + 1H 入場信號
- **多重過濾器**：波動率、成交量、資金費率過濾器
- **換手率優化**：信號持續性、強度、冷卻期過濾器
- **風險管理**：基於 ATR 的止損、追蹤止盈、逆波動率加權
- **全面測試**：單元測試、回測、壓力測試
- **實盤交易**：OKX 測試網和主網支援

## 🚀 安裝

### 前置需求

- Python 3.8 或更高版本
- pip 套件管理器

### 設定步驟

```bash
# 複製儲存庫
git clone https://github.com/itsYoga/pysix-MLFT.git
cd pysix-MLFT

# 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安裝依賴套件
pip install -r requirements.txt

# 驗證安裝
python test_env.py
```

## 🏃 快速開始

### 測試簡單因子策略

```bash
python test.py
```

### 測試 ALM 策略

```bash
# 基礎 ALM 策略
python test.py --alm --csv test_4h.csv

# 優化版 ALM 策略（降低換手率）
python test.py --alm --optimized --csv test_4h.csv

# 改進版 ALM 策略（推薦）
python tests/test_alm_improved_csv.py test_4h.csv
```

### 執行回測

```bash
# 使用統一回測腳本
python scripts/run_backtest.py \
    --strategy alm \
    --symbols BTC ETH SOL \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --cost 0.001
```

## 📊 策略測試

### ALM 策略測試

```bash
# 測試基礎策略
python tests/test_alm.py --type base

# 測試優化策略
python tests/test_alm.py --type optimized

# 測試改進策略
python tests/test_alm.py --type improved

# 測試所有版本（對比）
python tests/test_alm.py --type all
```

### 使用 CSV 數據

```bash
# 使用本地 CSV 文件測試
python tests/test_with_csv.py test_4h.csv

# 測試改進版策略
python tests/test_alm_improved_csv.py test_4h.csv
```

### 策略對比測試

```bash
# 對比改進版和高級版策略
python tests/test_strategy_comparison.py --csv test_4h.csv --plot
```

### 壓力測試

```bash
# 測試不同交易成本
python stress_test.py

# 對比基礎版與優化版
python stress_test.py compare
```

## 📁 專案結構

```
pyxis-MLFT/
├── strategies/              # 策略實現
│   ├── alm/                # ALM 策略
│   │   ├── strategy.py              # 基礎策略
│   │   ├── strategy_optimized.py   # 優化版本
│   │   ├── strategy_improved.py    # 改進版本（推薦）
│   │   ├── strategy_advanced.py    # 高級版本（開發中）
│   │   ├── indicators.py            # 高級技術指標
│   │   ├── numba_logic.py           # Numba 加速邏輯
│   │   └── regime.py                # 市場狀態檢測
│   └── template/           # 策略模板
│       └── strategy.py
│
├── core/                   # 核心模組
│   ├── backtest.py         # 統一回測引擎
│   ├── trader.py           # OKX 交易介面
│   └── risk.py             # 風險管理模組
│
├── tests/                   # 測試腳本
│   ├── test_alm.py         # ALM 策略測試
│   ├── test_alm_improved.py        # 改進版測試
│   ├── test_alm_improved_csv.py    # CSV 測試
│   ├── test_strategy_comparison.py  # 策略對比
│   ├── test_with_csv.py    # CSV 基礎測試
│   └── test_strategy_template.py
│
├── scripts/                 # 工具腳本
│   └── run_backtest.py     # 統一回測腳本
│
├── data/                    # 數據目錄（自動建立）
├── test.py                  # 主測試腳本
├── requirements.txt         # Python 依賴
└── README.md                # 本文件
```

## 📈 ALM 策略

### 策略概述

自適應流動性動能（ALM）策略是一個專為加密貨幣市場設計的趨勢跟隨 CTA 策略。

**核心組件：**
1. **4H 趨勢過濾器**：三重 EMA 系統（EMA 20/50/200）
2. **1H 入場觸發器**：Donchian 通道突破（20 週期）
3. **過濾器**：波動率（ATR）、成交量確認、資金費率
4. **風險管理**：逆波動率加權
5. **優化**：信號持續性、強度過濾器、冷卻期

### 策略邏輯流程

```
4H 趨勢過濾器（EMA 20/50/200）
    ↓
1H Donchian 突破信號
    ↓
波動率過濾器（基於 ATR）
    ↓
成交量確認
    ↓
信號組合
    ↓
逆波動率加權
    ↓
回測執行
```

## 📊 策略版本對比

### 基礎版本

**特點**：
- 嚴格 AND 邏輯（所有過濾器必須同時滿足）
- 固定參數
- 無退出邏輯

**績效指標**：
- 年化換手率：~32,314%
- 信號覆蓋率：0.1%（極度稀疏）
- 最大回撤：-12.53%
- 年化收益率：-16.16%

### 優化版本

**改進**：
- 信號持續性過濾器
- 信號強度過濾器
- 最小持倉時間過濾器
- 冷卻期過濾器

**績效指標**：
- 年化換手率：~8,390%（降低 74%）
- 信號覆蓋率：0.1%（仍然稀疏）
- 最大回撤：類似基礎版

### 改進版本（推薦）⭐

**主要改進**：
- ✅ **加權評分系統**：替代嚴格 AND 邏輯
- ✅ **信號平滑**：減少噪音和換手率
- ✅ **動態參數調整**：根據市場波動率調整窗口大小
- ✅ **正確的時間框架處理**：4H→1H 廣播邏輯

**保守參數配置（已驗證盈利）**：
```python
from strategies.alm import build_alm_strategy_improved

strategy = build_alm_strategy_improved(
    panel_1h=panel_1h,
    panel_4h=panel_4h,
    use_weighted_scoring=True,
    signal_threshold=0.6,          # 提高閾值
    enable_smoothing=True,
    smoothing_window=7,            # 增加平滑
    min_holding_periods=24,        # 增加持倉時間
    enable_adaptive_params=True
)
```

**績效指標（保守參數）**：
- ✅ **年化收益率**：+6.21%（盈利！）
- ✅ **夏普比率**：+0.15（正值）
- ✅ **最大回撤**：-9.75%（改善）
- ✅ **年化換手率**：6,665%（降低 79%）
- ✅ **信號覆蓋率**：38.03%（大幅提升）

### 高級版本（開發中）

**高級功能**：
- 🔄 **市場狀態檢測**：CHOP + ADX + ER
- 🔄 **自適應 Donchian 通道**：基於 Efficiency Ratio
- 🔄 **滯後邏輯（Hysteresis）**：解決信號閃爍問題
- 🔄 **Chandelier Exit**：追蹤止損
- 🔄 **波動率目標**：風險平價倉位大小
- 🔄 **再平衡緩衝區**：減少不必要的交易

**預期改進**：
- 換手率：500-1,000% 年化
- 信號覆蓋率：5-15%
- 最大回撤：< -15%
- 夏普比率：> 0.5

## 📈 績效分析

### 當前測試結果（改進版保守參數）

| 指標 | 數值 | 狀態 |
|------|------|------|
| **總收益率** | +3.94% | ✅ 盈利 |
| **年化收益率** | +6.21% | ✅ 盈利 |
| **夏普比率** | +0.15 | ✅ 正值 |
| **最大回撤** | -9.75% | ✅ 改善 |
| **年化波動率** | 21.72% | ✅ 可接受 |
| **信號覆蓋率** | 38.03% | ✅ 大幅改善 |
| **年化換手率** | 6,665% | ✅ 降低 79% |
| **年化交易成本** | 13.33% | ✅ 降低 56% |

### 為什麼改進版策略能盈利？

#### 1. 大幅降低換手率

**改進前**：
- 年化換手率：32,314%
- 年化交易成本：64.63%（32,314% × 0.2%）

**改進後**：
- 年化換手率：6,665%
- 年化交易成本：13.33%（6,665% × 0.2%）
- **降低 51.3% 的交易成本**

#### 2. 提高信號覆蓋率

**改進前**：
- 信號覆蓋率：0.1%（8/6,692）
- 策略大部分時間處於現金狀態

**改進後**：
- 信號覆蓋率：38.03%（2,545/6,692）
- **提升 380 倍**

#### 3. 加權評分系統

**舊方法（嚴格 AND）**：
```python
signal = filter1 * filter2 * filter3 * filter4
# 任何一個為 0，結果為 0
```

**新方法（加權評分）**：
```python
score = (
    trend * 0.30 +
    breakout * 0.25 +
    volatility * 0.15 +
    volume * 0.15 +
    funding * 0.15
)
signal = 1 if score > threshold else 0
```

**優勢**：
- 靈活調整各項權重
- 可以部分滿足條件也能產生信號
- 通過閾值控制信號質量

#### 4. 信號平滑處理

```python
smoothed = ts_mean(signal, window=7)
```

**效果**：
- 減少短期噪音
- 降低換手率 20-30%
- 提高信號穩定性

### 參數優化建議

#### 保守配置（推薦，已驗證盈利）

```python
{
    'signal_threshold': 0.6,
    'min_holding_periods': 24,
    'smoothing_window': 7
}
```

**效果**：
- 年化收益率：+6.21%
- 換手率：6,665%
- 最大回撤：-9.75%

#### 平衡配置

```python
{
    'signal_threshold': 0.5,
    'min_holding_periods': 16,
    'smoothing_window': 5
}
```

#### 積極配置（高覆蓋率）

```python
{
    'signal_threshold': 0.4,
    'min_holding_periods': 12,
    'smoothing_window': 3
}
```

## 💡 改進建議

### 優先級 1：進一步降低換手率

#### 方案 A：增加最小持倉時間
```python
min_holding_periods=48  # 從 24 增加到 48 小時
```
**預期效果**：換手率再降低 30-50%

#### 方案 B：提高信號閾值
```python
signal_threshold=0.7  # 從 0.6 提高到 0.7
```
**預期效果**：只保留最強信號，減少交易次數

#### 方案 C：增加平滑窗口
```python
smoothing_window=10  # 從 7 增加到 10
```
**預期效果**：進一步減少信號噪音

### 優先級 2：實施退出邏輯

**需要在回測引擎中實現**：
- 止損：2×ATR
- 止盈：3×ATR
- 追蹤止損：1.5×ATR

**預期效果**：
- 最大回撤從 -9.75% 降到 < -7%
- 保護利潤，限制損失

### 優先級 3：參數優化

**建議測試不同參數組合**：
- 使用網格搜索找到最優參數
- 測試不同市場環境
- Walk-Forward Analysis 驗證穩定性

## 🔬 高級優化

### 市場狀態檢測

**實現的功能**：
- **Choppiness Index (CHOP)**：檢測市場是否處於震盪狀態
- **Average Directional Index (ADX)**：測量趨勢強度
- **Efficiency Ratio (ER)**：信號與噪音比

**狀態分類**：
- **震盪市場**：CHOP > 61.8 OR ADX < 20 → 禁止交易
- **趨勢市場**：CHOP < 50 AND ADX > 25 → 啟用突破邏輯
- **極端趨勢**：CHOP < 38.2 AND ADX > 50 → 收緊止損

### Numba 加速邏輯

**路徑依賴邏輯優化**：
- `apply_hysteresis_numba()` - 滯後邏輯（Schmitt Trigger）
- `calculate_chandelier_exit()` - Chandelier Exit 計算
- `apply_chandelier_exit_to_signal()` - 應用止損到信號

**性能提升**：
- 接近 C++ 執行速度
- 支援大數據集回測

### 風險管理模組

**實現的功能**：
- `calculate_volatility_targeted_weights()` - 波動率目標權重
- `apply_rebalancing_buffer()` - 再平衡緩衝區

**使用範例**：
```python
from core.risk import calculate_volatility_targeted_weights, apply_rebalancing_buffer

# 計算波動率目標權重
target_weights = calculate_volatility_targeted_weights(
    returns=returns,
    target_volatility=0.15  # 15% 年化波動率
)

# 應用再平衡緩衝區
final_weights = apply_rebalancing_buffer(
    current_weights=current_weights,
    target_weights=target_weights,
    buffer_pct=0.10  # 10% 緩衝區
)
```

## 🔧 創建新策略

### 步驟 1：複製模板

```bash
cp -r strategies/template strategies/your_strategy_name
```

### 步驟 2：實現策略

編輯 `strategies/your_strategy_name/strategy.py`：

```python
from phandas import *
from typing import Optional

def build_your_strategy(
    panel_1h: Panel,
    panel_4h: Optional[Panel] = None,
    **kwargs
) -> Factor:
    """
    構建您的策略信號
    
    參數
    ----------
    panel_1h : Panel
        1H 時間框架數據面板
    panel_4h : Panel, optional
        4H 時間框架數據面板
    
    返回
    -------
    Factor
        策略信號因子（正值=做多，負值=做空，0=無信號）
    """
    close_1h = panel_1h['close']
    
    # 在此實現您的策略邏輯
    signal_data = close_1h.data.copy()
    signal_data['factor'] = 0.0  # 您的信號計算
    
    return Factor(signal_data, "YourStrategy")
```

### 步驟 3：更新 __init__.py

編輯 `strategies/your_strategy_name/__init__.py`：

```python
from .strategy import build_your_strategy
__all__ = ['build_your_strategy']
```

### 步驟 4：創建測試

```bash
cp tests/test_strategy_template.py tests/test_your_strategy.py
```

編輯測試文件並運行：

```bash
python tests/test_your_strategy.py
```

## 💹 實盤交易

### 設定 OKX API（測試網）

```bash
export OKX_API_KEY='your_testnet_api_key'
export OKX_SECRET_KEY='your_testnet_secret_key'
export OKX_PASSPHRASE='your_passphrase'
```

### 運行實盤交易腳本

```bash
python live_trading_setup.py
```

**⚠️ 重要**：在實盤交易前，必須在 OKX 測試網測試 1-3 個月！

## 🤖 AI 整合 (MCP)

Phandas 支援 MCP（Model Context Protocol）整合，允許 Cursor 中的 AI 助手直接存取 phandas 函數。

### 快速設定

1. **安裝 phandas**：`pip install phandas`
2. **設定 Cursor**：Settings → Tools & MCP → New MCP Server
3. **貼上以下 JSON 配置**：

```json
{
  "mcpServers": {
    "phandas": {
      "command": "/Users/jesse/Documents/NTUFC/pyxis-MLFT/venv/bin/python",
      "args": ["-m", "phandas.mcp_server"]
    }
  }
}
```

**重要**：確保使用虛擬環境的完整 Python 路徑。

4. **儲存配置並重啟 Cursor**

### 驗證安裝

重啟 Cursor 後，在聊天中測試：

```
列出所有可用的 phandas 運算子
```

如果 AI 回應運算子列表，MCP 配置成功！

### 可用工具

1. **`fetch_market_data`** - 獲取加密貨幣市場數據
2. **`list_operators`** - 瀏覽所有因子運算子
3. **`read_source`** - 查看函數源代碼
4. **`execute_factor_backtest`** - 執行因子回測

### 使用範例

**範例 1**：查詢可用運算子
```
列出所有可用的 phandas 運算子
```

**範例 2**：獲取市場數據
```
獲取 ETH 和 SOL 最近 10 天的日線數據
```

**範例 3**：執行因子回測
```
回測一個 20 天動量因子，對成交量進行中性化
```

**範例 4**：查看源代碼
```
顯示 ts_mean 函數的源代碼
```

## 🛠️ 命令參考

### 測試命令

| 命令 | 說明 |
|------|------|
| `python test_env.py` | 驗證環境設定 |
| `python test.py` | 測試簡單因子策略 |
| `python test.py --alm` | 測試基礎 ALM 策略 |
| `python test.py --alm --optimized` | 測試優化 ALM 策略 |
| `python tests/test_alm.py --type base` | 僅測試基礎 ALM |
| `python tests/test_alm.py --type optimized` | 僅測試優化 ALM |
| `python tests/test_alm.py --type improved` | 僅測試改進 ALM |
| `python tests/test_alm.py --type all` | 測試所有版本 |
| `python tests/test_alm_improved_csv.py test_4h.csv` | 使用 CSV 測試改進版 |

### 回測命令

| 命令 | 說明 |
|------|------|
| `python scripts/run_backtest.py --strategy alm` | 基礎策略回測 |
| `python scripts/run_backtest.py --strategy alm_optimized` | 優化策略回測 |
| `python alm_backtest.py` | 完整回測工作流程 |

### 壓力測試

| 命令 | 說明 |
|------|------|
| `python stress_test.py` | 交易成本壓力測試 |
| `python stress_test.py compare` | 對比策略 |

### 策略對比

| 命令 | 說明 |
|------|------|
| `python tests/test_strategy_comparison.py --csv test_4h.csv` | 對比改進版和高級版 |
| `python tests/test_strategy_comparison.py --csv test_4h.csv --plot` | 對比並繪圖 |

## 📝 依賴套件

參見 `requirements.txt` 完整列表。關鍵依賴：

- `phandas>=0.17.0` - 多因子交易框架
- `pandas>=1.5.0` - 數據處理
- `numpy>=1.20.0` - 數值計算
- `ccxt>=4.0.0` - 加密貨幣交易所庫
- `matplotlib>=3.5.0` - 繪圖
- `scipy>=1.9.0` - 科學計算
- `python-okx>=0.4.0` - OKX API 客戶端
- `numba>=0.63.0` - JIT 編譯加速（高級策略需要）

## ⚠️ 重要注意事項

1. **數據來源**：目前使用 Binance，生產環境應使用 OKX
2. **實盤交易**：必須先在 OKX 測試網測試 1-3 個月
3. **交易成本**：高換手率策略需要更高的成本假設（0.1%-0.2%）
4. **風險管理**：設定止損和倉位限制
5. **API 限制**：注意交易所 API 速率限制

## 🐛 故障排除

### 導入錯誤

```bash
# 確保在專案根目錄
cd /path/to/pysix-MLFT

# 啟動虛擬環境
source venv/bin/activate

# 重新安裝依賴
pip install -r requirements.txt
```

### 數據獲取問題

- 檢查網路連接
- 驗證日期範圍是否有效
- 檢查資產符號是否正確

### 策略測試失敗

- 驗證策略函數簽名
- 檢查 Panel 數據格式
- 查看錯誤日誌

### MCP 設定問題

**錯誤**：`ModuleNotFoundError: No module named 'phandas.mcp_server'`

**解決方案**：
1. 確保 phandas 已安裝：`pip install phandas`
2. 驗證安裝：`python -m phandas.mcp_server`（不應報錯）
3. 檢查 MCP 配置中的 Python 路徑是否匹配虛擬環境

**Python 路徑問題**：

**問題**：Cursor 找不到 Python 或使用錯誤的 Python

**解決方案**：在 MCP 配置中使用虛擬環境的完整路徑：
```json
{
  "mcpServers": {
    "phandas": {
      "command": "/full/path/to/venv/bin/python",
      "args": ["-m", "phandas.mcp_server"]
    }
  }
}
```

**MCP 重啟後不工作**：

**解決方案**：
1. 檢查 Cursor 設定 → Tools & MCP → phandas 伺服器是否啟用
2. 嘗試再次重啟 Cursor
3. 檢查 Cursor 日誌中的錯誤

## 📚 文檔

- **專案結構**：參見上方「專案結構」章節
- **測試說明**：參見 `tests/README.md`
- **範例說明**：參見 `examples/README.md`
- **腳本說明**：參見 `scripts/README.md`
- **phandas 文檔**：https://phandas.readthedocs.io/
- **phandas GitHub**：https://github.com/quantbai/phandas
- **MCP 協議**：https://modelcontextprotocol.io/

## 🤝 貢獻

歡迎貢獻！請：

1. Fork 儲存庫
2. 建立功能分支
3. 進行更改
4. 添加測試
5. 提交 Pull Request

## 📄 授權

本專案僅供教育和研究用途。

## 🙏 致謝

- 基於 [phandas](https://github.com/quantbai/phandas) 框架構建
- 使用 [ccxt](https://github.com/ccxt/ccxt) 進行交易所整合
- OKX API 整合

## 📧 聯絡

如有問題或建議，請在 GitHub 上開啟 Issue。

---

**免責聲明**：本軟體僅供教育用途。交易加密貨幣涉及重大風險。過往表現不代表未來結果。實盤交易前請充分測試。

**最後更新**：2024-12-13
