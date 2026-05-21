from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BrokerBase(ABC):
    def __init__(self):
        self._last_error = ""

    @property
    def last_error(self) -> str:
        return self._last_error

    @last_error.setter
    def last_error(self, value: str):
        self._last_error = value

    @abstractmethod
    def generate_login_url(self) -> str:
        pass

    @abstractmethod
    async def complete_login(self, request_token: str) -> bool:
        pass

    @abstractmethod
    async def get_profile(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_funds(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_holdings(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def place_order(self, symbol: str, qty: int, side: str, order_type: str, price: float = 0.0) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def is_session_valid(self) -> bool:
        pass
