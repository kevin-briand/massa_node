import asyncio
import logging

import requests
_LOGGER = logging.getLogger(__name__)

class BitgetApi:
    """Api of Bitget.com"""
    _base_url = 'https://api.bitget.com/api/v2/spot/market/'
    _headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    async def get_massa_price(self) -> float:
        """get last price of massa, it returns a float of price MAS-USDT"""
        response = await asyncio.to_thread(self._get_massa_price_request)
        if response.status_code != 200:
            return 0
        data = response.json()
        return float(data['data'][0]["lastPr"])

    def _get_massa_price_request(self):
        """request for fetch latest data of MAS-USDT"""
        response = requests.get(
            f'{self._base_url}tickers?symbol=MASUSDT',
            headers=self._headers
        )
        return response
