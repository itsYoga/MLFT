# 實盤交易指南

## ⚠️ 重要警告

**在實盤交易前，您必須：**

1. ✅ 在測試網測試至少 1-3 個月
2. ✅ 充分理解策略風險和可能虧損
3. ✅ 設置適當的倉位限制和風險管理
4. ✅ 準備好承擔可能的虧損
5. ✅ 確保有足夠的資金應對回撤

**實盤交易有風險，可能導致資金損失！**

---

## 🚀 快速開始

### 1. 設置 API 憑證

#### 測試網（推薦先使用）

```bash
# 在 OKX 測試網創建 API Key
# https://www.okx.com/web3/build/docs/waapi/waapi-quick-start

export OKX_API_KEY='your_testnet_api_key'
export OKX_SECRET_KEY='your_testnet_secret_key'
export OKX_PASSPHRASE='your_passphrase'
```

#### 實盤（危險！）

```bash
# 在 OKX 實盤創建 API Key
# 確保只給予必要的權限（交易、查詢）

export OKX_API_KEY='your_mainnet_api_key'
export OKX_SECRET_KEY='your_mainnet_secret_key'
export OKX_PASSPHRASE='your_passphrase'
```

### 2. 配置賬戶

**必須設置**：
- 賬戶模式：FUTURES(2) 或 CROSS_MARGIN(3)
- 倉位模式：net_mode（單向持倉）
- API 權限：交易、查詢

### 3. 運行實盤交易

#### 測試網（推薦）

```bash
# 使用測試網，每 4 小時重新平衡一次
python live_trading.py --testnet --interval 4

# 只執行一次（測試）
python live_trading.py --testnet --once

# 限制最大迭代次數（測試）
python live_trading.py --testnet --interval 4 --max-iterations 10
```

#### 實盤（危險！）

```bash
# 使用實盤（需要確認）
python live_trading.py --mainnet --interval 4

# 更保守的設置
python live_trading.py --mainnet \
    --interval 6 \
    --max-position 0.15 \
    --leverage 1.0
```

---

## 📋 參數說明

### 基本參數

| 參數 | 說明 | 默認值 | 建議值 |
|------|------|--------|--------|
| `--testnet` | 使用測試網 | True | ✅ 先使用 |
| `--mainnet` | 使用實盤 | False | ⚠️ 危險 |
| `--once` | 只執行一次 | False | 測試時使用 |
| `--interval` | 重新平衡間隔（小時） | 4 | 4-6 小時 |
| `--max-iterations` | 最大迭代次數 | 無限 | 測試時設置 |

### 風險控制參數

| 參數 | 說明 | 默認值 | 建議值 |
|------|------|--------|--------|
| `--max-position` | 單一資產最大倉位 | 0.20 (20%) | 0.15-0.20 |
| `--leverage` | 總槓桿倍數 | 1.0 (無槓桿) | 1.0-2.0 |

---

## 🔧 使用範例

### 範例 1：測試網測試（推薦）

```bash
# 設置環境變量
export OKX_API_KEY='your_testnet_api_key'
export OKX_SECRET_KEY='your_testnet_secret_key'
export OKX_PASSPHRASE='your_passphrase'

# 運行測試（只執行一次）
python live_trading.py --testnet --once

# 持續運行（每 4 小時重新平衡）
python live_trading.py --testnet --interval 4
```

### 範例 2：實盤運行（保守配置）

```bash
# 設置環境變量（實盤）
export OKX_API_KEY='your_mainnet_api_key'
export OKX_SECRET_KEY='your_mainnet_secret_key'
export OKX_PASSPHRASE='your_passphrase'

# 保守配置：
# - 每 6 小時重新平衡
# - 單一資產最大 15% 倉位
# - 無槓桿
python live_trading.py --mainnet \
    --interval 6 \
    --max-position 0.15 \
    --leverage 1.0
```

### 範例 3：使用 systemd 持續運行（Linux）

創建服務文件 `/etc/systemd/system/alm-trader.service`：

```ini
[Unit]
Description=ALM Strategy Live Trader
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/pyxis-MLFT
Environment="OKX_API_KEY=your_api_key"
Environment="OKX_SECRET_KEY=your_secret_key"
Environment="OKX_PASSPHRASE=your_passphrase"
ExecStart=/path/to/venv/bin/python live_trading.py --testnet --interval 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

啟動服務：
```bash
sudo systemctl enable alm-trader
sudo systemctl start alm-trader
sudo systemctl status alm-trader
```

---

## 📊 監控和日誌

### 日誌文件

所有日誌會保存到 `live_trading.log`：

```bash
# 查看實時日誌
tail -f live_trading.log

# 查看最近的錯誤
grep ERROR live_trading.log | tail -20
```

### 關鍵指標監控

實盤運行時，建議監控：

1. **賬戶餘額變化**
2. **倉位變化**
3. **交易執行情況**
4. **錯誤和異常**

---

## 🛡️ 風險管理建議

### 1. 倉位限制

- **單一資產最大倉位**：15-20%
- **總倉位**：不超過總資金的 80%
- **總槓桿**：1.0-2.0x（建議 1.0x）

### 2. 止損設置

雖然策略內建止損邏輯，但建議：

- 在交易所設置**硬止損**（2-3×ATR）
- 設置**總體止損**（例如：總虧損超過 20% 停止交易）

### 3. 資金管理

- **不要投入全部資金**
- 建議只投入**可承受損失的資金**（例如：總資產的 10-20%）
- 保留足夠的**現金緩衝**

### 4. 監控頻率

- **每天檢查**賬戶狀態
- **每週檢查**策略表現
- **每月評估**是否需要調整參數

---

## ⚠️ 常見問題

### Q1: 如何停止實盤交易？

**A**: 按 `Ctrl+C` 安全停止，或使用 `--once` 參數只執行一次。

### Q2: 如何修改重新平衡頻率？

**A**: 使用 `--interval` 參數，例如 `--interval 6` 表示每 6 小時重新平衡。

### Q3: 如何查看當前倉位？

**A**: 日誌中會顯示當前倉位信息，或使用 OKX 網頁/APP 查看。

### Q4: 策略出錯怎麼辦？

**A**: 
1. 檢查日誌文件 `live_trading.log`
2. 檢查 API 憑證是否正確
3. 檢查賬戶配置是否正確
4. 如有必要，手動平倉

### Q5: 如何修改策略參數？

**A**: 編輯 `live_trading.py` 中的 `build_alm_strategy_ultra_conservative` 參數。

---

## 📝 檢查清單

實盤交易前檢查：

- [ ] 已在測試網測試至少 1-3 個月
- [ ] 測試網表現穩定且盈利
- [ ] API 憑證已正確設置
- [ ] 賬戶配置已驗證（FUTURES/CROSS_MARGIN + net_mode）
- [ ] 已設置適當的倉位限制
- [ ] 已設置交易所硬止損
- [ ] 已準備好監控和日誌查看
- [ ] 已準備好應對可能的虧損
- [ ] 已閱讀並理解所有風險警告

---

## 🔗 相關文件

- `live_trading.py` - 實盤交易腳本
- `live_trading_setup.py` - 實盤交易設置（舊版）
- `core/trader.py` - OKX 交易接口
- `strategies/alm/strategy_ultra_conservative.py` - 超保守策略

---

**最後更新**：2024-12-13  
**狀態**：實盤交易腳本已準備就緒

**⚠️ 再次提醒：實盤交易有風險，請謹慎操作！**

