import logging
from typing import Dict, Any, List
from backend.services.broker_base import BrokerBase
from backend.services.zerodha_broker import ZerodhaBroker
from backend.services.angel_one_broker import AngelOneBroker
from backend.services.icici_direct_broker import ICICIDirectBroker
from backend.utils.cache import redis_cache

logger = logging.getLogger(__name__)

class BrokerManager:
    def __init__(self):
        self.brokers: Dict[str, BrokerBase] = {}

    def get_broker(self, broker_name: str, user_id: str) -> BrokerBase:
        key = f"{user_id}_{broker_name}"
        if key not in self.brokers:
            if broker_name == "zerodha":
                self.brokers[key] = ZerodhaBroker()
            elif broker_name == "angel_one":
                self.brokers[key] = AngelOneBroker()
            elif broker_name == "icici_direct":
                self.brokers[key] = ICICIDirectBroker()
            else:
                raise ValueError(f"Unknown broker: {broker_name}")
        return self.brokers[key]

    @redis_cache(ttl_seconds=300, key_prefix="unified_portfolio")
    async def get_unified_portfolio(self, user_id: str, connected_brokers: List[str]) -> Dict[str, Any]:
        unified_holdings = {}
        for b_name in connected_brokers:
            broker = self.get_broker(b_name, user_id)
            if broker.is_session_valid():
                holdings = await broker.get_holdings()
                for h in holdings:
                    sym = h.get('symbol') or h.get('stock_code')
                    if sym:
                        if sym in unified_holdings:
                            unified_holdings[sym]['quantity'] += float(h.get('quantity', 0))
                        else:
                            unified_holdings[sym] = {
                                'symbol': sym,
                                'quantity': float(h.get('quantity', 0)),
                                'average_price': float(h.get('average_price', 0))
                            }
        return {"holdings": list(unified_holdings.values())}

    async def place_smart_order(self, user_id: str, symbol: str, qty: int, side: str, order_type: str, price: float = 0.0) -> Dict[str, Any]:
        return {"error": "Not implemented completely - specify broker"}
