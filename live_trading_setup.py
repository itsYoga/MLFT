"""
實盤交易準備腳本
整合 ALM 策略與 OKX 交易接口，用於實盤執行
"""

import os
import logging
from typing import Dict, Optional
from phandas import *
from core.trader import OKXTrader, rebalance
from strategies.alm import build_alm_strategy_optimized
from core.backtest import resample_panel_to_4h

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ALMLiveTrader:
    """
    ALM 策略實盤交易類
    整合策略信號生成和 OKX 交易執行
    """
    
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        passphrase: str,
        use_testnet: bool = True,
        symbol_suffix: str = '-USDT-SWAP',
        leverage: int = 5
    ):
        """
        初始化實盤交易器
        
        Parameters
        ----------
        api_key : str
            OKX API Key
        secret_key : str
            OKX Secret Key
        passphrase : str
            OKX Passphrase
        use_testnet : bool
            是否使用測試網（強烈建議先使用測試網）
        symbol_suffix : str
            交易對後綴
        leverage : int
            槓桿倍數
        """
        self.trader = OKXTrader(
            api_key=api_key,
            secret_key=secret_key,
            passphrase=passphrase,
            use_testnet=use_testnet,
            inst_type='SWAP'
        )
        self.symbol_suffix = symbol_suffix
        self.leverage = leverage
        self.use_testnet = use_testnet
        
        logger.info(f"ALM Live Trader 初始化完成（{'測試網' if use_testnet else '實盤'}）")
    
    def validate_account(self) -> Dict:
        """驗證賬戶配置"""
        logger.info("驗證賬戶配置...")
        validation = self.trader.validate_account_config()
        
        if validation['status'] == 'error':
            logger.error(f"賬戶配置驗證失敗: {validation['msg']}")
            logger.error("請檢查:")
            logger.error("  1. 賬戶模式必須是 FUTURES(2) 或 CROSS_MARGIN(3)")
            logger.error("  2. 倉位模式必須是 net_mode (單向持倉)")
        else:
            logger.info("✓ 賬戶配置驗證通過")
            for check_name, check_data in validation.get('checks', {}).items():
                logger.info(f"  {check_name}: {check_data['value']}")
        
        return validation
    
    def get_current_positions(self) -> Dict:
        """獲取當前倉位"""
        positions = self.trader.get_positions()
        logger.info(f"當前倉位數量: {len(positions)}")
        
        if positions:
            total_notional = sum(abs(p['notional_usd']) for p in positions.values())
            logger.info(f"總倉位價值: ${total_notional:,.2f}")
            
            for pos_key, pos_data in positions.items():
                logger.info(f"  {pos_data['symbol']:12s} | "
                           f"方向: {pos_data['pos_side']:4s} | "
                           f"數量: {pos_data['pos_qty']:12.4f} | "
                           f"價值: ${pos_data['notional_usd']:12.2f}")
        
        return positions
    
    def generate_strategy_signals(
        self,
        symbols: list,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Factor:
        """
        生成策略信號
        
        Parameters
        ----------
        symbols : list
            交易資產列表
        start_date : str, optional
            開始日期（用於獲取歷史數據）
        end_date : str, optional
            結束日期
        """
        logger.info(f"生成策略信號（資產: {symbols}）...")
        
        # 獲取最新數據（例如過去 30 天）
        if start_date is None:
            from datetime import datetime, timedelta
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        if end_date is None:
            from datetime import datetime
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 獲取數據
        panel_1h = fetch_data(
            symbols=symbols,
            timeframe='1h',
            start_date=start_date,
            end_date=end_date,
            sources=['binance']  # 注意：實際應使用 OKX
        )
        
        try:
            panel_4h = fetch_data(
                symbols=symbols,
                timeframe='4h',
                start_date=start_date,
                end_date=end_date,
                sources=['binance']
            )
        except:
            panel_4h = resample_panel_to_4h(panel_1h)
        
        # 構建優化策略信號
        strategy_signal = build_alm_strategy_optimized(
            panel_1h=panel_1h,
            panel_4h=panel_4h,
            enable_persistence_filter=True,
            persistence_periods=4,
            enable_strength_filter=True,
            strength_threshold=0.5,
            enable_min_holding=True,
            min_holding_hours=8,
            enable_cooldown=True,
            cooldown_hours=4
        )
        
        logger.info("✓ 策略信號生成完成")
        return strategy_signal
    
    def signals_to_weights(
        self,
        strategy_signal: Factor,
        use_inverse_vol_weighting: bool = True
    ) -> Dict[str, float]:
        """
        將策略信號轉換為投資組合權重
        
        Parameters
        ----------
        strategy_signal : Factor
            策略信號因子
        use_inverse_vol_weighting : bool
            是否使用逆波動率加權
        
        Returns
        -------
        Dict[str, float]
            資產權重字典
        """
        # 獲取最新信號
        latest_date = strategy_signal.data['timestamp'].max()
        latest_signals = strategy_signal.data[
            strategy_signal.data['timestamp'] == latest_date
        ]
        
        if latest_signals.empty:
            logger.warning("沒有找到最新信號")
            return {}
        
        # 轉換為權重
        if use_inverse_vol_weighting:
            # 使用逆波動率加權
            from strategies.alm.strategy import calculate_inverse_volatility_weights
            
            # 需要計算收益率（這裡簡化處理）
            # 實際應該從歷史數據計算
            close = strategy_signal.data.pivot_table(
                index='timestamp',
                columns='symbol',
                values='factor'
            )
            returns = close.pct_change()
            
            # 簡化：直接使用信號值作為權重基礎
            weights_dict = {}
            for _, row in latest_signals.iterrows():
                symbol = row['symbol']
                signal_value = row['factor']
                
                # 移除後綴（如果有的話）
                symbol_base = symbol.replace(self.symbol_suffix, '')
                
                if abs(signal_value) > 0.01:  # 只包含有效信號
                    weights_dict[symbol_base] = signal_value
        else:
            # 直接使用信號值
            weights_dict = {}
            for _, row in latest_signals.iterrows():
                symbol = row['symbol']
                signal_value = row['factor']
                symbol_base = symbol.replace(self.symbol_suffix, '')
                
                if abs(signal_value) > 0.01:
                    weights_dict[symbol_base] = signal_value
        
        # 歸一化權重（確保總和為 1）
        total_abs = sum(abs(w) for w in weights_dict.values())
        if total_abs > 0:
            weights_dict = {k: v / total_abs for k, v in weights_dict.items()}
        
        logger.info(f"生成權重（{len(weights_dict)} 個資產）:")
        for symbol, weight in sorted(weights_dict.items(), key=lambda x: abs(x[1]), reverse=True):
            logger.info(f"  {symbol:8s}: {weight:+8.4f} ({weight*100:+6.2f}%)")
        
        return weights_dict
    
    def execute_rebalance(
        self,
        target_weights: Dict[str, float],
        preview: bool = True,
        auto_confirm: bool = False
    ) -> Dict:
        """
        執行投資組合再平衡
        
        Parameters
        ----------
        target_weights : Dict[str, float]
            目標權重字典
        preview : bool
            是否預覽再平衡計劃
        auto_confirm : bool
            是否自動確認（危險！僅在測試網使用）
        
        Returns
        -------
        Dict
            再平衡結果
        """
        # 獲取賬戶餘額
        balance_info = self.trader.get_account_balance_info()
        
        if 'error' in balance_info:
            logger.error(f"無法獲取賬戶餘額: {balance_info['error']}")
            return {'status': 'error', 'msg': balance_info['error']}
        
        budget = balance_info['total_equity']
        logger.info(f"賬戶總權益: ${budget:,.2f}")
        
        if budget <= 0:
            logger.error("賬戶餘額為零或負數")
            return {'status': 'error', 'msg': 'Insufficient balance'}
        
        # 執行再平衡
        logger.info("執行投資組合再平衡...")
        
        rb = rebalance(
            target_weights=target_weights,
            trader=self.trader,
            budget=budget,
            symbol_suffix=self.symbol_suffix,
            leverage=self.leverage,
            preview=preview and not auto_confirm,
            auto_run=True
        )
        
        rb.print_summary()
        
        return rb.get_result()
    
    def run_full_cycle(
        self,
        symbols: list,
        preview: bool = True,
        auto_confirm: bool = False
    ) -> Dict:
        """
        運行完整的交易週期：
        1. 生成策略信號
        2. 轉換為權重
        3. 執行再平衡
        
        Parameters
        ----------
        symbols : list
            交易資產列表
        preview : bool
            是否預覽
        auto_confirm : bool
            是否自動確認
        
        Returns
        -------
        Dict
            執行結果
        """
        logger.info("=" * 80)
        logger.info("ALM 策略實盤執行週期")
        logger.info("=" * 80)
        
        # 1. 驗證賬戶
        validation = self.validate_account()
        if validation['status'] == 'error':
            return {'status': 'error', 'msg': 'Account validation failed'}
        
        # 2. 獲取當前倉位
        current_positions = self.get_current_positions()
        
        # 3. 生成策略信號
        strategy_signal = self.generate_strategy_signals(symbols)
        
        # 4. 轉換為權重
        target_weights = self.signals_to_weights(strategy_signal)
        
        if not target_weights:
            logger.warning("沒有生成有效權重，跳過再平衡")
            return {'status': 'skip', 'msg': 'No valid weights'}
        
        # 5. 執行再平衡
        result = self.execute_rebalance(
            target_weights=target_weights,
            preview=preview,
            auto_confirm=auto_confirm
        )
        
        return result


def main():
    """
    主函數 - 示例使用
    """
    # 從環境變量讀取 API 憑證（安全）
    api_key = os.getenv('OKX_API_KEY', '')
    secret_key = os.getenv('OKX_SECRET_KEY', '')
    passphrase = os.getenv('OKX_PASSPHRASE', '')
    
    if not all([api_key, secret_key, passphrase]):
        logger.error("請設置環境變量:")
        logger.error("  export OKX_API_KEY='your_api_key'")
        logger.error("  export OKX_SECRET_KEY='your_secret_key'")
        logger.error("  export OKX_PASSPHRASE='your_passphrase'")
        logger.error("\n或直接在代碼中設置（僅用於測試）")
        return
    
    # 初始化交易器（使用測試網）
    trader = ALMLiveTrader(
        api_key=api_key,
        secret_key=secret_key,
        passphrase=passphrase,
        use_testnet=True,  # 強烈建議先使用測試網！
        leverage=5
    )
    
    # 定義交易資產
    from strategies.alm import OKX_TOP_15_ASSETS
    symbols = OKX_TOP_15_ASSETS[:5]  # 先用前 5 個資產測試
    
    # 運行完整週期
    result = trader.run_full_cycle(
        symbols=symbols,
        preview=True,  # 預覽模式，需要手動確認
        auto_confirm=False  # 不要自動確認！
    )
    
    logger.info("\n執行完成！")
    logger.info(f"結果狀態: {result.get('status', 'unknown')}")


if __name__ == "__main__":
    main()

