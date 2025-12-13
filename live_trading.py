"""
ALM 策略實盤交易腳本 - 持續運行
使用超保守策略配置進行實盤交易
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, Optional

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from phandas import *
from strategies.alm import build_alm_strategy_ultra_conservative
from core.trader import OKXTrader, rebalance
from core.backtest import resample_panel_to_4h

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('live_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ALMLiveTrader:
    """
    ALM 策略實盤交易類
    持續運行，定期生成信號並執行交易
    """
    
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        passphrase: str,
        use_testnet: bool = True,
        symbols: Optional[list] = None,
        rebalance_interval_hours: int = 4,  # 每 4 小時重新平衡一次
        max_position_size_pct: float = 0.20,  # 單一資產最大倉位 20%
        total_leverage: float = 1.0  # 總槓桿（1.0 = 無槓桿）
    ):
        """
        初始化實盤交易器
        
        參數
        ----------
        api_key : str
            OKX API Key
        secret_key : str
            OKX Secret Key
        passphrase : str
            OKX Passphrase
        use_testnet : bool
            是否使用測試網（強烈建議先使用測試網測試 1-3 個月）
        symbols : list, optional
            交易資產列表，默認使用 OKX_TOP_15_ASSETS 前 7 個
        rebalance_interval_hours : int
            重新平衡間隔（小時）
        max_position_size_pct : float
            單一資產最大倉位百分比
        total_leverage : float
            總槓桿倍數（建議 1.0-2.0）
        """
        self.trader = OKXTrader(
            api_key=api_key,
            secret_key=secret_key,
            passphrase=passphrase,
            use_testnet=use_testnet,
            inst_type='SWAP'
        )
        
        if symbols is None:
            from strategies.alm import OKX_TOP_15_ASSETS
            symbols = OKX_TOP_15_ASSETS[:7]  # 使用前 7 個資產
        
        self.symbols = symbols
        self.rebalance_interval_hours = rebalance_interval_hours
        self.max_position_size_pct = max_position_size_pct
        self.total_leverage = total_leverage
        self.use_testnet = use_testnet
        
        logger.info("=" * 80)
        logger.info("ALM 實盤交易器初始化")
        logger.info("=" * 80)
        logger.info(f"模式: {'測試網' if use_testnet else '實盤'}")
        logger.info(f"交易資產: {self.symbols}")
        logger.info(f"重新平衡間隔: {rebalance_interval_hours} 小時")
        logger.info(f"單一資產最大倉位: {max_position_size_pct:.0%}")
        logger.info(f"總槓桿: {total_leverage}x")
        logger.info("=" * 80)
    
    def validate_account(self) -> bool:
        """驗證賬戶配置"""
        logger.info("\n驗證賬戶配置...")
        validation = self.trader.validate_account_config()
        
        if validation.get('status') == 'error':
            logger.error(f"賬戶配置驗證失敗: {validation.get('msg', 'Unknown error')}")
            logger.error("\n請檢查:")
            logger.error("  1. 賬戶模式必須是 FUTURES(2) 或 CROSS_MARGIN(3)")
            logger.error("  2. 倉位模式必須是 net_mode (單向持倉)")
            logger.error("  3. API 權限必須包含交易權限")
            return False
        else:
            logger.info("✓ 賬戶配置驗證通過")
            for check_name, check_data in validation.get('checks', {}).items():
                status_icon = "✓" if check_data.get('status') == 'ok' else "✗"
                logger.info(f"  {status_icon} {check_name}: {check_data.get('value')}")
            return True
    
    def get_account_balance(self) -> Dict:
        """獲取賬戶餘額"""
        try:
            balance_info = self.trader.get_account_balance_info()
            if 'error' in balance_info:
                logger.error(f"獲取餘額失敗: {balance_info['error']}")
                return {}
            
            total_equity = balance_info.get('total_equity', 0)
            available_equity = balance_info.get('available_equity', 0)
            
            logger.info(f"\n賬戶餘額:")
            logger.info(f"  總權益: ${total_equity:,.2f}")
            logger.info(f"  可用餘額: ${available_equity:,.2f}")
            
            return balance_info
        except Exception as e:
            logger.error(f"獲取餘額異常: {e}")
            return {}
    
    def generate_strategy_signals(self) -> Optional[Factor]:
        """
        生成策略信號
        
        返回
        -------
        Factor
            策略信號因子
        """
        logger.info("\n生成策略信號...")
        
        try:
            # 獲取 1H 數據
            logger.info("  獲取 1H 數據...")
            panel_1h = fetch_data(
                symbols=self.symbols,
                timeframe='1h',
                start_date=None,  # 獲取最近數據
                sources=['binance']  # 或使用 'okx'
            )
            
            # 獲取 4H 數據（如果失敗則從 1H 重採樣）
            try:
                logger.info("  獲取 4H 數據...")
                panel_4h = fetch_data(
                    symbols=self.symbols,
                    timeframe='4h',
                    start_date=None,
                    sources=['binance']
                )
            except:
                logger.info("  4H 數據獲取失敗，從 1H 重採樣...")
                panel_4h = resample_panel_to_4h(panel_1h)
            
            # 構建超保守策略
            logger.info("  構建超保守策略信號...")
            strategy_signal = build_alm_strategy_ultra_conservative(
                panel_1h=panel_1h,
                panel_4h=panel_4h,
                signal_entry_threshold=0.75,
                signal_exit_threshold=0.25,
                smoothing_window=15,
                min_holding_periods=72,
                enable_adaptive_params=True,
                base_window=30
            )
            
            # 統計信號
            signal_data = strategy_signal.data
            total = len(signal_data)
            long_signals = (signal_data['factor'] > 0).sum()
            short_signals = (signal_data['factor'] < 0).sum()
            
            logger.info(f"  ✓ 策略信號生成成功")
            logger.info(f"    總數據點: {total}")
            logger.info(f"    做多信號: {long_signals} ({long_signals/total*100:.2f}%)")
            logger.info(f"    做空信號: {short_signals} ({short_signals/total*100:.2f}%)")
            
            return strategy_signal
            
        except Exception as e:
            logger.error(f"  ✗ 策略信號生成失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def execute_rebalance(self, strategy_signal: Factor) -> Dict:
        """
        執行重新平衡
        
        參數
        ----------
        strategy_signal : Factor
            策略信號因子
        
        返回
        -------
        Dict
            執行結果
        """
        logger.info("\n執行重新平衡...")
        
        try:
            # 獲取最新信號（最後一個時間點）
            latest_signals = {}
            signal_df = strategy_signal.data.sort_values(['symbol', 'timestamp'])
            
            for symbol in self.symbols:
                symbol_data = signal_df[signal_df['symbol'] == symbol]
                if not symbol_data.empty:
                    latest_signal = symbol_data.iloc[-1]['factor']
                    latest_signals[symbol] = latest_signal
                else:
                    latest_signals[symbol] = 0.0
            
            logger.info("  當前信號:")
            for symbol, signal in latest_signals.items():
                signal_type = "做多" if signal > 0 else ("做空" if signal < 0 else "空倉")
                logger.info(f"    {symbol:8s}: {signal_type} (信號強度: {signal:+.2f})")
            
            # 獲取賬戶餘額
            balance_info = self.get_account_balance()
            total_equity = balance_info.get('total_equity', 0)
            
            if total_equity == 0:
                logger.error("  無法獲取賬戶餘額，跳過重新平衡")
                return {'status': 'error', 'msg': 'Cannot get account balance'}
            
            # 計算目標權重（基於信號強度）
            target_weights = {}
            total_signal_strength = sum(abs(s) for s in latest_signals.values())
            
            if total_signal_strength > 0:
                for symbol, signal in latest_signals.items():
                    if signal != 0:
                        # 根據信號強度分配權重，並應用最大倉位限制
                        weight = (abs(signal) / total_signal_strength) * self.total_leverage
                        weight = min(weight, self.max_position_size_pct)  # 限制單一資產倉位
                        target_weights[symbol] = weight if signal > 0 else -weight
                    else:
                        target_weights[symbol] = 0.0
            else:
                logger.info("  無有效信號，全部平倉")
                for symbol in self.symbols:
                    target_weights[symbol] = 0.0
            
            logger.info("\n  目標權重:")
            for symbol, weight in target_weights.items():
                if weight != 0:
                    logger.info(f"    {symbol:8s}: {weight:+.2%}")
            
            # 執行重新平衡
            logger.info("\n  執行交易...")
            result = rebalance(
                trader=self.trader,
                target_weights=target_weights,
                total_budget=total_equity,
                symbol_suffix='-USDT-SWAP',
                max_position_size_pct=self.max_position_size_pct
            )
            
            if result.get('status') == 'success':
                logger.info("  ✓ 重新平衡完成")
                if result.get('trades'):
                    logger.info(f"    執行交易數: {len(result['trades'])}")
            else:
                logger.error(f"  ✗ 重新平衡失敗: {result.get('msg', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"  ✗ 執行重新平衡異常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'status': 'error', 'msg': str(e)}
    
    def run_once(self) -> Dict:
        """
        執行一次完整的交易循環
        
        返回
        -------
        Dict
            執行結果
        """
        logger.info("\n" + "=" * 80)
        logger.info(f"交易循環開始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        # 1. 生成策略信號
        strategy_signal = self.generate_strategy_signals()
        if strategy_signal is None:
            return {'status': 'error', 'msg': 'Failed to generate strategy signals'}
        
        # 2. 執行重新平衡
        result = self.execute_rebalance(strategy_signal)
        
        logger.info("\n" + "=" * 80)
        logger.info(f"交易循環完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        return result
    
    def run_continuous(self, max_iterations: Optional[int] = None):
        """
        持續運行交易循環
        
        參數
        ----------
        max_iterations : int, optional
            最大迭代次數（None 表示無限運行）
        """
        logger.info("\n" + "=" * 80)
        logger.info("開始持續運行模式")
        logger.info("=" * 80)
        logger.info(f"重新平衡間隔: {self.rebalance_interval_hours} 小時")
        logger.info(f"最大迭代次數: {'無限' if max_iterations is None else max_iterations}")
        logger.info("按 Ctrl+C 停止")
        logger.info("=" * 80)
        
        iteration = 0
        interval_seconds = self.rebalance_interval_hours * 3600
        
        try:
            while True:
                if max_iterations and iteration >= max_iterations:
                    logger.info(f"\n達到最大迭代次數 ({max_iterations})，停止運行")
                    break
                
                iteration += 1
                logger.info(f"\n>>> 第 {iteration} 次迭代 <<<")
                
                # 執行交易循環
                result = self.run_once()
                
                if result.get('status') == 'error':
                    logger.warning(f"本次迭代失敗，將在 {self.rebalance_interval_hours} 小時後重試")
                
                # 等待下一次迭代
                if iteration < (max_iterations or float('inf')):
                    logger.info(f"\n等待 {self.rebalance_interval_hours} 小時後執行下一次重新平衡...")
                    logger.info(f"下次執行時間: {(datetime.now().timestamp() + interval_seconds):.0f}")
                    time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("\n\n收到停止信號，正在安全退出...")
        except Exception as e:
            logger.error(f"\n運行異常: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            logger.info("\n實盤交易器已停止")


def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ALM 策略實盤交易')
    parser.add_argument('--testnet', action='store_true', default=True,
                       help='使用測試網（默認，強烈建議）')
    parser.add_argument('--mainnet', action='store_true',
                       help='使用實盤（危險！請先測試 1-3 個月）')
    parser.add_argument('--once', action='store_true',
                       help='只執行一次，不持續運行')
    parser.add_argument('--interval', type=int, default=4,
                       help='重新平衡間隔（小時，默認 4）')
    parser.add_argument('--max-iterations', type=int, default=None,
                       help='最大迭代次數（默認無限）')
    parser.add_argument('--max-position', type=float, default=0.20,
                       help='單一資產最大倉位百分比（默認 0.20 = 20%）')
    parser.add_argument('--leverage', type=float, default=1.0,
                       help='總槓桿倍數（默認 1.0 = 無槓桿）')
    
    args = parser.parse_args()
    
    # 確定使用測試網還是實盤
    use_testnet = not args.mainnet
    if args.mainnet:
        logger.warning("=" * 80)
        logger.warning("⚠️  警告：您正在使用實盤模式！")
        logger.warning("⚠️  請確保：")
        logger.warning("   1. 已在測試網測試至少 1-3 個月")
        logger.warning("   2. 已充分理解策略風險")
        logger.warning("   3. 已設置適當的倉位限制")
        logger.warning("   4. 已準備好承擔可能的虧損")
        logger.warning("=" * 80)
        response = input("\n確認要使用實盤模式嗎？(yes/no): ")
        if response.lower() != 'yes':
            logger.info("已取消")
            return
    
    # 從環境變量獲取 API 憑證
    api_key = os.getenv('OKX_API_KEY')
    secret_key = os.getenv('OKX_SECRET_KEY')
    passphrase = os.getenv('OKX_PASSPHRASE')
    
    if not all([api_key, secret_key, passphrase]):
        logger.error("=" * 80)
        logger.error("錯誤：缺少 API 憑證")
        logger.error("=" * 80)
        logger.error("請設置環境變量：")
        logger.error("  export OKX_API_KEY='your_api_key'")
        logger.error("  export OKX_SECRET_KEY='your_secret_key'")
        logger.error("  export OKX_PASSPHRASE='your_passphrase'")
        logger.error("\n或直接在代碼中設置（不推薦，安全性較低）")
        return
    
    # 初始化交易器
    trader = ALMLiveTrader(
        api_key=api_key,
        secret_key=secret_key,
        passphrase=passphrase,
        use_testnet=use_testnet,
        rebalance_interval_hours=args.interval,
        max_position_size_pct=args.max_position,
        total_leverage=args.leverage
    )
    
    # 驗證賬戶配置
    if not trader.validate_account():
        logger.error("賬戶配置驗證失敗，請檢查配置後重試")
        return
    
    # 顯示賬戶餘額
    trader.get_account_balance()
    
    # 執行交易
    if args.once:
        # 只執行一次
        trader.run_once()
    else:
        # 持續運行
        trader.run_continuous(max_iterations=args.max_iterations)


if __name__ == "__main__":
    main()

