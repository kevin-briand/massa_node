"""MASSA node API class"""
import asyncio
from typing import Optional

import requests
from homeassistant.core import HomeAssistant


class CycleInfo:
    """Object class of a massa cycle"""

    def __init__(self, cycle, is_final, ok_count, nok_count, active_rolls, **kwargs):
        self.cycle: int = cycle
        self.is_final: bool = is_final
        self.ok_count: int = ok_count
        self.nok_count: int = nok_count
        self.active_rolls: int = active_rolls


class AddressInfo:
    """Object class of a massa address"""

    def __init__(self, address, final_balance, final_roll_count, candidate_balance,
                 candidate_roll_count, cycle_infos, **kwargs):
        self.address: str = address
        self.final_balance: str = final_balance
        self.final_roll_count: int = final_roll_count
        self.candidate_balance: str = candidate_balance
        self.candidate_roll_count: int = candidate_roll_count
        self.cycle_infos: [CycleInfo] = [CycleInfo(**cycle_info) for cycle_info in cycle_infos]


class NodeApi:
    """API of MASSA node, used for fetch some information of local node"""
    _ip: str
    _port: int
    _wallet_address: str
    _headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    def __init__(self, hass: HomeAssistant, ip: str, port: int, wallet_address: str) -> None:
        """Init API"""
        self._ip = ip
        self._port = port
        self._wallet_address = wallet_address
        self._base_url = 'http://' + self._ip + ':' + str(self._port) + '/'

    async def test_connection(self) -> bool:
        """test if node is online, return a boolean"""
        try:
            response = await asyncio.to_thread(self._get_status_request)
            return response.status_code == 200
        except Exception:
            return False

    async def get_address(self) -> Optional[AddressInfo]:
        """fetch information of a wallet"""
        try:
            response = await asyncio.to_thread(self._get_address_request)
            if response.status_code != 200:
                return
            data = response.json()
            if not data['result']:
                return
            address_info = data['result'][0]
            result = AddressInfo(**address_info)
            return result
        except Exception:
            return None

    def _get_status_request(self):
        """request for fetch latest data of status"""
        response = requests.post(
            self._base_url,
            json={'jsonrpc': '2.0', 'id': 1, 'method': 'get_status'},
            headers=self._headers
        )
        return response

    def _get_address_request(self):
        """request for fetch latest data of a wallet"""
        response = requests.post(
            self._base_url,
            json={'jsonrpc': '2.0', 'id': 1, 'method': 'get_addresses', 'params': [[self._wallet_address]]},
            headers=self._headers
        )
        return response
