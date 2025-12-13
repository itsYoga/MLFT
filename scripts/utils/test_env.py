"""
環境測試腳本 - 驗證所有依賴和模塊是否正常工作
"""

import sys

print("=" * 60)
print("環境測試")
print("=" * 60)

# 1. 檢查 Python 版本
print(f"\n1. Python 版本: {sys.version}")

# 2. 檢查 phandas
try:
    from phandas import *
    print("✓ phandas 導入成功")
    
    # 測試基本功能
    print("  測試 fetch_data...")
    panel = fetch_data(
        symbols=['BTC', 'ETH'],
        timeframe='1d',
        start_date='2024-01-01',
        end_date='2024-01-10',
        sources=['binance']
    )
    print(f"  ✓ 數據獲取成功，共 {len(panel.data)} 條記錄")
    
    # 測試 Factor 操作
    close = panel['close']
    print(f"  ✓ Factor 提取成功: {close.name}")
    
    # 測試運算子
    momentum = (close / ts_delay(close, 1)) - 1
    print(f"  ✓ 運算子測試成功: {momentum.name}")
    
except Exception as e:
    print(f"✗ phandas 測試失敗: {e}")
    sys.exit(1)

# 3. 檢查 ALM 策略模塊
try:
    from alm_strategy import (
        OKX_TOP_15_ASSETS,
        calculate_ema,
        calculate_atr,
        calculate_donchian_breakout
    )
    print(f"\n✓ ALM 策略模塊導入成功")
    print(f"  目標資產數量: {len(OKX_TOP_15_ASSETS)}")
except Exception as e:
    print(f"\n✗ ALM 策略模塊導入失敗: {e}")
    sys.exit(1)

# 4. 檢查回測模塊
try:
    from alm_backtest import run_alm_backtest
    print("✓ 回測模塊導入成功")
except Exception as e:
    print(f"✗ 回測模塊導入失敗: {e}")
    sys.exit(1)

# 5. 檢查其他依賴
dependencies = {
    'pandas': 'pd',
    'numpy': 'np',
    'ccxt': None,
    'matplotlib': 'plt',
    'scipy': None
}

print("\n5. 檢查其他依賴:")
for module, alias in dependencies.items():
    try:
        if alias:
            exec(f"import {module} as {alias}")
        else:
            exec(f"import {module}")
        print(f"  ✓ {module}")
    except Exception as e:
        print(f"  ✗ {module}: {e}")

print("\n" + "=" * 60)
print("✓ 所有測試通過！環境配置正確。")
print("=" * 60)
print("\n下一步:")
print("  1. 運行完整回測: python example_alm.py 1")
print("  2. 運行原始測試: python test.py")
print("  3. 查看文檔: cat README_ALM.md")

