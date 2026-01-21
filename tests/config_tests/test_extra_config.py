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
import unittest

from pyasic.config import MinerConfig, PoolConfig
from pyasic.config.extra_config.espminer import ESPMinerExtraConfig


class TestESPMinerExtraConfig(unittest.TestCase):
    def test_create_with_all_fields(self):
        """Test creating ESPMinerExtraConfig with all fields set"""
        config = ESPMinerExtraConfig(
            rotation=90,
            invertscreen=1,
            display_timeout=5,
            overheat_mode=0,
            overclock_enabled=1,
            stats_frequency=10,
            min_fan_speed=30,
        )
        self.assertEqual(config.rotation, 90)
        self.assertEqual(config.invertscreen, 1)
        self.assertEqual(config.display_timeout, 5)
        self.assertEqual(config.overheat_mode, 0)
        self.assertEqual(config.overclock_enabled, 1)
        self.assertEqual(config.stats_frequency, 10)
        self.assertEqual(config.min_fan_speed, 30)

    def test_create_with_partial_fields(self):
        """Test creating ESPMinerExtraConfig with some fields None"""
        config = ESPMinerExtraConfig(
            rotation=180,
            invertscreen=None,
            display_timeout=None,
        )
        self.assertEqual(config.rotation, 180)
        self.assertIsNone(config.invertscreen)
        self.assertIsNone(config.display_timeout)

    def test_create_empty(self):
        """Test creating ESPMinerExtraConfig with all fields None"""
        config = ESPMinerExtraConfig()
        self.assertIsNone(config.rotation)
        self.assertIsNone(config.invertscreen)
        self.assertIsNone(config.display_timeout)
        self.assertIsNone(config.overheat_mode)
        self.assertIsNone(config.overclock_enabled)
        self.assertIsNone(config.stats_frequency)
        self.assertIsNone(config.min_fan_speed)

    def test_as_espminer_excludes_none(self):
        """Test that as_espminer() excludes None values"""
        config = ESPMinerExtraConfig(
            rotation=90,
            invertscreen=None,
            display_timeout=5,
        )
        result = config.as_espminer()
        self.assertIn("rotation", result)
        self.assertIn("displayTimeout", result)  # camelCase conversion
        self.assertNotIn("invertscreen", result)
        self.assertEqual(result["rotation"], 90)
        self.assertEqual(result["displayTimeout"], 5)

    def test_as_espminer_field_name_conversion(self):
        """Test that as_espminer() converts field names to API format"""
        config = ESPMinerExtraConfig(
            rotation=90,
            invertscreen=1,
            display_timeout=10,
            overheat_mode=0,
            overclock_enabled=1,
            stats_frequency=5,
            min_fan_speed=25,
        )
        result = config.as_espminer()
        # Check camelCase conversion
        self.assertIn("displayTimeout", result)
        self.assertIn("overclockEnabled", result)
        self.assertIn("statsFrequency", result)
        self.assertIn("minFanSpeed", result)
        # Check snake_case fields stay as-is
        self.assertIn("rotation", result)
        self.assertIn("invertscreen", result)
        self.assertIn("overheat_mode", result)

    def test_as_espminer_all_none(self):
        """Test that as_espminer() returns empty dict when all fields are None"""
        config = ESPMinerExtraConfig()
        result = config.as_espminer()
        self.assertEqual(result, {})

    def test_from_espminer_with_all_fields(self):
        """Test creating ESPMinerExtraConfig from API response with all fields"""
        web_system_info = {
            "rotation": 90,
            "invertscreen": 1,
            "displayTimeout": 5,
            "overheat_mode": 0,
            "overclockEnabled": 1,
            "statsFrequency": 10,
            "minFanSpeed": 30,
        }
        config = ESPMinerExtraConfig.from_espminer(web_system_info)
        self.assertEqual(config.rotation, 90)
        self.assertEqual(config.invertscreen, 1)
        self.assertEqual(config.display_timeout, 5)
        self.assertEqual(config.overheat_mode, 0)
        self.assertEqual(config.overclock_enabled, 1)
        self.assertEqual(config.stats_frequency, 10)
        self.assertEqual(config.min_fan_speed, 30)

    def test_from_espminer_with_partial_fields(self):
        """Test creating ESPMinerExtraConfig from API response with some fields missing"""
        web_system_info = {
            "rotation": 180,
            "invertscreen": 0,
            # Other fields missing
        }
        config = ESPMinerExtraConfig.from_espminer(web_system_info)
        self.assertEqual(config.rotation, 180)
        self.assertEqual(config.invertscreen, 0)
        self.assertIsNone(config.display_timeout)
        self.assertIsNone(config.overheat_mode)

    def test_from_espminer_empty(self):
        """Test creating ESPMinerExtraConfig from empty API response"""
        web_system_info = {}
        config = ESPMinerExtraConfig.from_espminer(web_system_info)
        self.assertIsNone(config.rotation)
        self.assertIsNone(config.invertscreen)
        self.assertIsNone(config.display_timeout)
        self.assertIsNone(config.overheat_mode)
        self.assertIsNone(config.overclock_enabled)
        self.assertIsNone(config.stats_frequency)
        self.assertIsNone(config.min_fan_speed)

    def test_serialize_and_deserialize(self):
        """Test round-trip serialization/deserialization"""
        original = ESPMinerExtraConfig(
            rotation=90,
            invertscreen=1,
            display_timeout=5,
            overheat_mode=0,
            overclock_enabled=1,
            stats_frequency=10,
            min_fan_speed=30,
        )
        # Serialize to dict
        serialized = original.model_dump()
        # Deserialize from dict
        deserialized = ESPMinerExtraConfig(**serialized)
        self.assertEqual(original, deserialized)


class TestMinerConfigWithExtraConfig(unittest.TestCase):
    def test_miner_config_with_extra_config(self):
        """Test MinerConfig with ESPMinerExtraConfig"""
        from pyasic.config.pools import Pool
        extra_config = ESPMinerExtraConfig(
            rotation=90,
            invertscreen=1,
            display_timeout=5,
        )
        config = MinerConfig(
            pools=PoolConfig.simple([Pool(url="stratum.test.io", user="test.user", password="x")]),
            extra_config=extra_config,
        )
        self.assertIsNotNone(config.extra_config)
        self.assertIsInstance(config.extra_config, ESPMinerExtraConfig)
        self.assertEqual(config.extra_config.rotation, 90)
        self.assertEqual(config.extra_config.invertscreen, 1)

    def test_as_espminer_includes_extra_config(self):
        """Test that as_espminer() includes extra_config fields"""
        from pyasic.config.pools import Pool
        extra_config = ESPMinerExtraConfig(
            rotation=180,
            invertscreen=0,
            display_timeout=10,
        )
        config = MinerConfig(
            pools=PoolConfig.simple([Pool(url="stratum.test.io", user="test.user", password="x")]),
            extra_config=extra_config,
        )
        result = config.as_espminer()
        # Check that extra_config fields are included with correct API names
        self.assertIn("rotation", result)
        self.assertIn("invertscreen", result)
        self.assertIn("displayTimeout", result)  # camelCase conversion
        self.assertEqual(result["rotation"], 180)
        self.assertEqual(result["invertscreen"], 0)
        self.assertEqual(result["displayTimeout"], 10)

    def test_as_espminer_without_extra_config(self):
        """Test that as_espminer() works without extra_config"""
        from pyasic.config.pools import Pool
        config = MinerConfig(
            pools=PoolConfig.simple([Pool(url="stratum.test.io", user="test.user", password="x")]),
            extra_config=None,
        )
        result = config.as_espminer()
        # Should not have extra_config fields
        self.assertNotIn("rotation", result)
        self.assertNotIn("invertscreen", result)
        self.assertNotIn("displayTimeout", result)
        self.assertNotIn("overheat_mode", result)
        self.assertNotIn("overclockEnabled", result)

    def test_from_espminer_with_extra_config(self):
        """Test creating MinerConfig from ESPMiner API with extra_config"""
        web_system_info = {
            "stratumURL": "stratum.test.io",
            "stratumPort": 3333,
            "stratumUser": "test.user",
            "stratumPassword": "x",
            "autofanspeed": 1,  # Required for FanModeConfig
            "rotation": 90,
            "invertscreen": 1,
            "displayTimeout": 5,
            "overheat_mode": 0,
            "overclockEnabled": 1,
        }
        config = MinerConfig.from_espminer(web_system_info)
        self.assertIsNotNone(config.extra_config)
        self.assertIsInstance(config.extra_config, ESPMinerExtraConfig)
        self.assertEqual(config.extra_config.rotation, 90)
        self.assertEqual(config.extra_config.invertscreen, 1)
        self.assertEqual(config.extra_config.display_timeout, 5)
        self.assertEqual(config.extra_config.overheat_mode, 0)
        self.assertEqual(config.extra_config.overclock_enabled, 1)

    def test_from_espminer_without_extra_config_fields(self):
        """Test creating MinerConfig from ESPMiner API without extra_config fields"""
        web_system_info = {
            "stratumURL": "stratum.test.io",
            "stratumPort": 3333,
            "stratumUser": "test.user",
            "stratumPassword": "x",
            "autofanspeed": 1,  # Required for FanModeConfig
            # No extra_config fields
        }
        config = MinerConfig.from_espminer(web_system_info)
        # extra_config should be None when all fields are None
        self.assertIsNone(config.extra_config)

    def test_from_espminer_with_partial_extra_config(self):
        """Test creating MinerConfig from ESPMiner API with partial extra_config fields"""
        web_system_info = {
            "stratumURL": "stratum.test.io",
            "stratumPort": 3333,
            "stratumUser": "test.user",
            "stratumPassword": "x",
            "autofanspeed": 1,  # Required for FanModeConfig
            "rotation": 180,
            "invertscreen": 0,
            # Other extra_config fields missing
        }
        config = MinerConfig.from_espminer(web_system_info)
        # Should still create extra_config if at least one field is set
        self.assertIsNotNone(config.extra_config)
        self.assertEqual(config.extra_config.rotation, 180)
        self.assertEqual(config.extra_config.invertscreen, 0)
        self.assertIsNone(config.extra_config.display_timeout)
        self.assertIsNone(config.extra_config.overheat_mode)


if __name__ == "__main__":
    unittest.main()
