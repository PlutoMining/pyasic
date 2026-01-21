# ------------------------------------------------------------------------------
#  Copyright 2022 Upstream Data Inc                                            -
#                                                                              -
#  Licensed under the Apache License, Version 2.0 (the "License");             -
#  you may not use this file except in compliance with the License.            -
#  You may obtain a copy of the License at                                     -
#                                                                              -
#      http://www.apache.org/licenses/LICENSE-2.0                              -
#                                                                              -
#  Unless required by applicable law or agreed to in writing, software         -
#  distributed on an "AS IS" BASIS,                                           -
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.    -
#  See the License for the specific language governing permissions and         -
#  limitations under the License.                                              -
# ------------------------------------------------------------------------------
from __future__ import annotations

from typing import Any

from pyasic.config.extra_config.base import MinerExtraConfig


class ESPMinerExtraConfig(MinerExtraConfig):
    """ESPMiner/BitAxe-specific extra configuration fields"""
    
    # Display settings
    rotation: int | None = None  # Display rotation (0, 90, 180, 270)
    invertscreen: int | None = None  # Invert screen (0 or 1)
    display_timeout: int | None = None  # Display timeout in seconds
    
    # Performance/Overclock settings
    overheat_mode: int | None = None  # Overheat mode (0 or 1)
    overclock_enabled: int | None = None  # Overclock enabled (0 or 1)
    stats_frequency: int | None = None  # Stats update frequency
    
    # Fan settings (additional to fan_mode)
    min_fan_speed: int | None = None  # Minimum fan speed percentage
    
    def as_espminer(self, *args: Any, **kwargs: Any) -> dict:
        """Convert to ESPMiner API format.
        
        Returns:
            A dictionary with ESPMiner-specific config fields, excluding None values.
            Field names are converted to match API format (snake_case to camelCase where needed).
        """
        result = {}
        # Map our field names to API field names
        field_mapping = {
            "rotation": "rotation",
            "invertscreen": "invertscreen",
            "display_timeout": "displayTimeout",
            "overheat_mode": "overheat_mode",
            "overclock_enabled": "overclockEnabled",
            "stats_frequency": "statsFrequency",
            "min_fan_speed": "minFanSpeed",
        }
        
        for field_name, api_name in field_mapping.items():
            value = getattr(self, field_name, None)
            if value is not None:
                result[api_name] = value
        
        return result
    
    @classmethod
    def from_espminer(cls, web_system_info: dict) -> "ESPMinerExtraConfig":
        """Create ESPMinerExtraConfig from ESPMiner API response.
        
        Args:
            web_system_info: The system/info response from ESPMiner API.
            
        Returns:
            An ESPMinerExtraConfig instance with fields extracted from the API response.
        """
        return cls(
            rotation=web_system_info.get("rotation"),
            invertscreen=web_system_info.get("invertscreen"),
            display_timeout=web_system_info.get("displayTimeout"),
            overheat_mode=web_system_info.get("overheat_mode"),
            overclock_enabled=web_system_info.get("overclockEnabled"),
            stats_frequency=web_system_info.get("statsFrequency"),
            min_fan_speed=web_system_info.get("minFanSpeed"),
        )
