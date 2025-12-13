"""
快速測試範例 - 使用本地 CSV 數據
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tests.integration.test_with_csv import test_with_csv

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='快速測試範例')
    parser.add_argument('--csv', default='test_4h.csv', help='CSV 數據文件')
    parser.add_argument('--strategy', choices=['base', 'improved'], 
                       default='improved', help='策略類型')
    parser.add_argument('--no-plot', action='store_true', help='不繪製圖表')
    args = parser.parse_args()
    
    test_with_csv(
        csv_file=args.csv,
        strategy_type=args.strategy,
        plot=not args.no_plot
    )

