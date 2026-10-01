"""Constants for the Massa Node integration."""

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "massa_node"

CONF_WALLET_ADDRESS: Final = "wallet_address"
DEFAULT_PORT: Final = 33035

PLATFORMS: Final = [Platform.BINARY_SENSOR, Platform.SENSOR]

# Node data is polled often, the market price much less (public API, rate limited).
UPDATE_INTERVAL: Final = timedelta(seconds=30)
PRICE_UPDATE_INTERVAL: Final = timedelta(minutes=5)
REQUEST_TIMEOUT: Final = 10

# Cost (in MAS) of one roll, used to value staked rolls.
ROLL_PRICE: Final = 100

PRICE_CURRENCY: Final = "USDT"
MASSA_UNIT: Final = "MAS"

STORAGE_VERSION: Final = 1
