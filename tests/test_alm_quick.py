"""
ALM 策略快速測試 - 使用短日期範圍
"""

import sys
import os

# 添加項目根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tests.test_strategy_template import test_strategy
from strategies.alm import build_alm_strategy, build_alm_strategy_optimized


def test_alm_quick():
    """快速測試 - 只使用 1 個月數據"""
    print("=" * 80)
    print("ALM 策略快速測試（1個月數據）")
    print("=" * 80)
    
    return test_strategy(
        strategy_name="ALM Base (Quick)",
        build_strategy_func=build_alm_strategy,
        symbols=['BTC', 'ETH'],  # 只用 2 個資產
        start_date='2024-01-01',  # 只測試 1 個月
        end_date='2024-02-01',
        transaction_cost=0.001
    )


if __name__ == "__main__":
    import signal
    
    def timeout_handler(signum, frame):
        print("\n\n測試超時！數據獲取時間過長。")
        print("建議：")
        print("1. 檢查網絡連接")
        print("2. 使用更短的日期範圍")
        print("3. 使用已保存的數據文件")
        sys.exit(1)
    
    # 設置 60 秒超時
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(60)
    
    try:
        test_alm_quick()
        signal.alarm(0)  # 取消超時
    except KeyboardInterrupt:
        print("\n\n測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        signal.alarm(0)
        print(f"\n\n錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

