import json
import aiohttp
from tronpy import Tron, AsyncTron
from tronpy.providers import AsyncHTTPProvider
from config import config

class TronService:
    def __init__(self):
        self.network = config.TRON_NETWORK
        self.api_key = config.TRONGRID_API_KEY
        self.provider = AsyncHTTPProvider(
            endpoint=f"https://api.trongrid.io/" if self.network == "mainnet" else "https://api.shasta.trongrid.io/",
            api_key=self.api_key
        )
        self.client = AsyncTron(provider=self.provider)
        
    async def get_trx_balance(self, address: str) -> float:
        """获取指定地址的TRX余额"""
        try:
            balance = await self.client.get_account_balance(address)
            return balance / 1_000_000  # 转换为TRX单位（1 TRX = 10^6 Sun）
        except Exception as e:
            print(f"获取TRX余额出错: {e}")
            return 0.0
            
    async def get_trc20_balance(self, address: str, contract_address: str) -> float:
        """获取指定地址的TRC20代币余额（如USDT）"""
        try:
            contract = await self.client.get_contract(contract_address)
            # 调用合约的balanceOf方法
            balance_hex = await contract.functions.balanceOf(address)
            # 假设代币有6位小数（如USDT）
            decimals = 6
            balance = int(balance_hex, 16) / (10 ​**​ decimals)
            return balance
        except Exception as e:
            print(f"获取TRC20余额出错: {e}")
            return 0.0
            
    async def get_transactions(self, address: str, limit: int = 20):
        """获取地址的最近交易记录（示例）"""
        # 此处可实现调用TRON API获取交易记录的逻辑
        # 在实际部署中，你可能需要更复杂的逻辑来处理分页和过滤
        pass
        
# 创建全局服务实例
tron_service = TronService()
