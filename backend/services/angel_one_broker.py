import logging
import pyotp
from typing import Dict, Any, List

try:
    from SmartApi import SmartConnect
except ImportError:
    SmartConnect = None

from backend.services.broker_base import BrokerBase
from backend.core.config import settings

logger = logging.getLogger(__name__)

class AngelOneBroker(BrokerBase):
    def __init__(self):
        super().__init__()
        self.api_key = settings.ANGEL_ONE_KEY
        self.api_secret = settings.ANGEL_ONE_SECRET
        self.client_code = "" 
        self.password = ""
        self.totp_secret = ""
        if SmartConnect:
            self.smartApi = SmartConnect(api_key=self.api_key)
        else:
            self.smartApi = None
        self.session_data = None

    def generate_login_url(self) -> str:
        return "Angel One requires direct credential login with TOTP, not OAuth URL."

    async def complete_login(self, request_token: str) -> bool:
        try:
            if not self.smartApi:
                raise Exception("SmartApi not installed")
            totp = pyotp.TOTP(self.totp_secret).now()
            data = self.smartApi.generateSession(self.client_code, self.password, totp)
            if data['status']:
                self.session_data = data['data']
                return True
            else:
                self.last_error = data.get('message', 'Login failed')
                return False
        except Exception as e:
            self.last_error = str(e)
            return False

    async def get_profile(self) -> Dict[str, Any]:
        try:
            return self.smartApi.getProfile(self.session_data['refreshToken']) if self.session_data else {}
        except Exception as e:
            self.last_error = str(e)
            return {}

    async def get_funds(self) -> Dict[str, Any]:
        try:
            return self.smartApi.rmsLimit()
        except Exception as e:
            self.last_error = str(e)
            return {}

    async def get_positions(self) -> List[Dict[str, Any]]:
        try:
            return self.smartApi.position().get('data', [])
        except Exception as e:
            self.last_error = str(e)
            return []

    async def get_holdings(self) -> List[Dict[str, Any]]:
        try:
            return self.smartApi.holding().get('data', [])
        except Exception as e:
            self.last_error = str(e)
            return []

    async def place_order(self, symbol: str, qty: int, side: str, order_type: str, price: float = 0.0) -> Dict[str, Any]:
        try:
            orderparams = {
                "variety": "NORMAL",
                "tradingsymbol": f"{symbol}-EQ",
                "symboltoken": "3045", 
                "transactiontype": side.upper(),
                "exchange": "NSE",
                "ordertype": order_type.upper(),
                "producttype": "DELIVERY",
                "duration": "DAY",
                "price": price,
                "squareoff": "0",
                "stoploss": "0",
                "quantity": qty
            }
            orderId = self.smartApi.placeOrder(orderparams)
            return {"order_id": orderId}
        except Exception as e:
            self.last_error = str(e)
            return {}

    async def cancel_order(self, order_id: str) -> bool:
        try:
            self.smartApi.cancelOrder("NORMAL", order_id)
            return True
        except Exception as e:
            self.last_error = str(e)
            return False

    async def test_connection(self) -> Dict[str, Any]:
        try:
            if not self.session_data:
                return {"connected": False, "error": "No session"}
            self.smartApi.getProfile(self.session_data['refreshToken'])
            return {"connected": True, "error": None}
        except Exception as e:
            self.last_error = str(e)
            return {"connected": False, "error": str(e)}

    def is_session_valid(self) -> bool:
        return self.session_data is not None
