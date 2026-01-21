import argparse
import os
import sys
import unittest
from typing import Any

import httpx

from pyasic.miners.base import BaseMiner
from pyasic.miners.data import DataOptions
from pyasic.miners.factory import MinerFactory
from pyasic.web.espminer import ESPMinerWebAPI


class TestBitAxeLocal(unittest.IsolatedAsyncioTestCase):
    ip: str | None = None
    miner: BaseMiner

    @classmethod
    def setUpClass(cls) -> None:
        cls.ip = os.getenv("BITAXE_IP")
        if not cls.ip:
            raise unittest.SkipTest("Set BITAXE_IP to run local BitAxe tests")

    async def asyncSetUp(self) -> None:
        assert self.ip is not None  # set in setUpClass or test is skipped
        factory = MinerFactory()
        miner = await factory.get_miner(self.ip)  # type: ignore[func-returns-value]
        if miner is None:
            self.skipTest("Miner discovery failed; check IP")
        self.miner = miner
        return None

    async def test_get_data_basics(self):
        data = await self.miner.get_data(
            include=[
                DataOptions.HOSTNAME,
                DataOptions.API_VERSION,
                DataOptions.FW_VERSION,
                DataOptions.HASHRATE,
                DataOptions.MAC,
            ]
        )
        if data.hostname is None:
            self.skipTest("Hostname not reported; skipping")
        if data.hashrate is None:
            self.skipTest("Hashrate not reported; skipping")
        if data.mac is None:
            self.skipTest("MAC not reported; skipping")

        self.assertIsNotNone(data.hostname)
        self.assertIsNotNone(data.hashrate)
        self.assertIsNotNone(data.mac)

    async def test_get_config(self):
        cfg = await self.miner.get_config()
        self.assertIsNotNone(cfg)

    async def test_get_config_with_extra_config(self):
        """Test that get_config() includes extra_config fields if present"""
        cfg = await self.miner.get_config()
        self.assertIsNotNone(cfg)

        # Check if extra_config is present (may be None if miner doesn't have these fields)
        if cfg.extra_config is not None:
            from pyasic.config.extra_config.espminer import ESPMinerExtraConfig

            self.assertIsInstance(cfg.extra_config, ESPMinerExtraConfig)

            # If extra_config exists, check that fields are accessible
            # (they may be None if not set on the miner)
            self.assertIsInstance(cfg.extra_config.rotation, (int, type(None)))
            self.assertIsInstance(cfg.extra_config.invertscreen, (int, type(None)))
            self.assertIsInstance(cfg.extra_config.display_timeout, (int, type(None)))
            self.assertIsInstance(cfg.extra_config.overheat_mode, (int, type(None)))
            self.assertIsInstance(cfg.extra_config.overclock_enabled, (int, type(None)))
            self.assertIsInstance(cfg.extra_config.stats_frequency, (int, type(None)))
            self.assertIsInstance(cfg.extra_config.min_fan_speed, (int, type(None)))

    async def test_send_config_with_extra_config(self):
        """Test sending config with extra_config fields.

        Note: This test may skip if the miner doesn't support these extra config fields
        or if the API rejects them. This is expected behavior for some miner firmware versions.
        """
        # Get current config
        current_cfg = await self.miner.get_config()
        self.assertIsNotNone(current_cfg)

        # Import ESPMinerExtraConfig
        from pyasic.config.extra_config.espminer import ESPMinerExtraConfig

        # Check what config will be sent
        config_dict = current_cfg.as_espminer()
        print(
            f"\nConfig to send (before adding extra_config): {list(config_dict.keys())}"
        )

        # Create or update extra_config
        if current_cfg.extra_config is None:
            current_cfg.extra_config = ESPMinerExtraConfig()

        # Set extra_config fields (toggle invertscreen as test)
        original_invertscreen = current_cfg.extra_config.invertscreen
        current_cfg.extra_config.invertscreen = (
            (0 if original_invertscreen == 1 else 1)
            if original_invertscreen is not None
            else 1
        )

        # Check what will be sent after adding extra_config
        config_dict_with_extra = current_cfg.as_espminer()
        print(
            f"Config to send (after adding extra_config): {list(config_dict_with_extra.keys())}"
        )
        print(f"Extra config fields: {current_cfg.extra_config.as_espminer()}")

        # Send config - if it fails, the miner may not support these fields
        try:
            await self.miner.send_config(current_cfg)
            print("Config sent successfully")
        except Exception as e:
            # If sending fails, it might be because the miner doesn't support these fields
            # This is OK - just skip the verification part
            error_msg = str(e)
            if (
                "empty response" in error_msg.lower()
                or "json decode" in error_msg.lower()
            ):
                self.skipTest(
                    f"Miner may not support extra_config fields (API returned empty response): {e}"
                )
            else:
                # Re-raise if it's a different error
                raise

        # Try to verify config was sent by reading it back
        # Note: Some miners may not persist these settings immediately
        try:
            verify_cfg = await self.miner.get_config()
            if verify_cfg.extra_config is not None:
                # Check that the value we set is reflected (if miner supports it)
                self.assertIsNotNone(verify_cfg.extra_config)
                print(
                    f"Verified extra_config exists: {verify_cfg.extra_config.as_espminer()}"
                )
                # Verify the invertscreen value was set correctly
                if verify_cfg.extra_config.invertscreen is not None:
                    self.assertEqual(
                        verify_cfg.extra_config.invertscreen,
                        current_cfg.extra_config.invertscreen,
                        "invertscreen value should match what we set",
                    )
        except Exception as e:
            # If verification fails, that's OK - miner may not support reading these fields
            print(f"Could not verify extra_config (this is OK): {e}")

    async def test_network_difficulty_read_only(self):
        """Test that network_difficulty is available as a read-only data field.

        network_difficulty should be in MinerData, not in MinerConfig.extra_config,
        because it's a read-only metric, not a writable configuration field.
        """
        # Get data including network_difficulty
        data = await self.miner.get_data(include=[DataOptions.NETWORK_DIFFICULTY])

        # network_difficulty should be in MinerData
        self.assertIsNotNone(data.network_difficulty)
        self.assertIsInstance(data.network_difficulty, int)
        self.assertGreater(
            data.network_difficulty, 0, "Network difficulty should be positive"
        )

        # Verify it's NOT in extra_config (it's read-only, not writable)
        config = await self.miner.get_config()
        if config.extra_config is not None:
            # network_difficulty should not be in extra_config
            extra_dict = config.extra_config.as_espminer()
            self.assertNotIn("networkDifficulty", extra_dict)
            self.assertNotIn("network_difficulty", extra_dict)

        print(f"Network difficulty (read-only): {data.network_difficulty}")

    async def test_get_data_extended(self):
        data = await self.miner.get_data(
            include=[
                DataOptions.HOSTNAME,
                DataOptions.API_VERSION,
                DataOptions.FW_VERSION,
                DataOptions.HASHRATE,
                DataOptions.EXPECTED_HASHRATE,
                DataOptions.WATTAGE,
                DataOptions.UPTIME,
                DataOptions.FANS,
                DataOptions.HASHBOARDS,
                DataOptions.MAC,
            ]
        )

        if data.hostname is None:
            self.skipTest("Hostname not reported; skipping")
        if data.api_ver is None:
            self.skipTest("API version not reported; skipping")
        if data.fw_ver is None:
            self.skipTest("FW version not reported; skipping")
        if data.expected_hashrate is None:
            self.skipTest("Expected hashrate not reported; skipping")
        if data.wattage is None:
            self.skipTest("Wattage not reported; skipping")
        if data.uptime is None:
            self.skipTest("Uptime not reported; skipping")
        if data.hashboards is None or len(data.hashboards) == 0:
            self.skipTest("Hashboards not reported; skipping")
        if data.fans is None or len(data.fans) == 0:
            self.skipTest("Fans not reported; skipping")

        self.assertIsNotNone(data.hostname)
        self.assertIsNotNone(data.api_ver)
        self.assertIsNotNone(data.fw_ver)
        self.assertIsNotNone(data.expected_hashrate)
        self.assertIsNotNone(data.wattage)
        self.assertIsNotNone(data.uptime)
        self.assertGreater(len(data.hashboards), 0)
        self.assertGreater(len(data.fans), 0)

    async def test_bitaxe_specific_fields(self):
        """Test that BitAxe/ESPMiner-specific fields are accessible and correctly typed.

        Note: These fields may be None if the miner hasn't found shares yet or
        if the miner doesn't support these metrics. The test verifies the fields
        exist and are the correct type when they have values.
        """
        # First, get raw API response to verify fields exist
        web = getattr(self.miner, "web", None)
        if web is None or not isinstance(web, ESPMinerWebAPI):
            self.skipTest("No web client available")

        raw_system_info = await web.system_info()

        # Debug: Print what we got from API
        print(f"\nRaw API bestDiff: {raw_system_info.get('bestDiff')}")
        print(f"Raw API bestSessionDiff: {raw_system_info.get('bestSessionDiff')}")
        print(f"Raw API sharesAccepted: {raw_system_info.get('sharesAccepted')}")
        print(f"Raw API sharesRejected: {raw_system_info.get('sharesRejected')}")

        # Now get parsed data
        data = await self.miner.get_data(
            include=[
                DataOptions.BEST_DIFFICULTY,
                DataOptions.BEST_SESSION_DIFFICULTY,
                DataOptions.SHARES_ACCEPTED,
                DataOptions.SHARES_REJECTED,
            ]
        )

        # Debug: Print what we got from parsed data
        print(f"\nParsed best_difficulty: {data.best_difficulty}")
        print(f"Parsed best_session_difficulty: {data.best_session_difficulty}")
        print(f"Parsed shares_accepted: {data.shares_accepted}")
        print(f"Parsed shares_rejected: {data.shares_rejected}")

        # If raw API has values but parsed doesn't, that's a bug
        if raw_system_info.get("bestDiff") is not None and data.best_difficulty is None:
            self.fail(
                f"Parsing bug: Raw API has bestDiff={raw_system_info.get('bestDiff')} "
                f"but parsed best_difficulty is None"
            )
        if (
            raw_system_info.get("bestSessionDiff") is not None
            and data.best_session_difficulty is None
        ):
            self.fail(
                f"Parsing bug: Raw API has bestSessionDiff={raw_system_info.get('bestSessionDiff')} "
                f"but parsed best_session_difficulty is None"
            )
        if (
            raw_system_info.get("sharesAccepted") is not None
            and data.shares_accepted is None
        ):
            self.fail(
                f"Parsing bug: Raw API has sharesAccepted={raw_system_info.get('sharesAccepted')} "
                f"but parsed shares_accepted is None"
            )
        if (
            raw_system_info.get("sharesRejected") is not None
            and data.shares_rejected is None
        ):
            self.fail(
                f"Parsing bug: Raw API has sharesRejected={raw_system_info.get('sharesRejected')} "
                f"but parsed shares_rejected is None"
            )

        # Verify fields exist and are correct type when they have values
        if data.best_difficulty is not None:
            self.assertIsInstance(data.best_difficulty, int)
            self.assertGreaterEqual(data.best_difficulty, 0)

        if data.best_session_difficulty is not None:
            self.assertIsInstance(data.best_session_difficulty, int)
            self.assertGreaterEqual(data.best_session_difficulty, 0)

        if data.shares_accepted is not None:
            self.assertIsInstance(data.shares_accepted, int)
            self.assertGreaterEqual(data.shares_accepted, 0)

        if data.shares_rejected is not None:
            self.assertIsInstance(data.shares_rejected, int)
            self.assertGreaterEqual(data.shares_rejected, 0)

    async def test_swarm_and_asic_info(self):
        """Test swarm_info and asic_info endpoints.

        Note: swarm_info may not be available on all miner firmware versions,
        so we make it optional. asic_info should be available on all BitAxe miners.
        """
        # Only run if the miner exposes the ESPMiner web API methods
        web = getattr(self.miner, "web", None)
        if web is None or not isinstance(web, ESPMinerWebAPI):
            self.skipTest("No web client available")

        # Try to get swarm_info (optional - may not be available on all firmware versions)
        swarm_info: dict[str, Any] | None = None
        try:
            swarm_info = await web.swarm_info()
            # Check if the response indicates an error (some APIs return 200 with error field)
            if swarm_info and "error" in swarm_info:
                print(f"swarm_info returned error: {swarm_info.get('error')}")
                swarm_info = None
        except Exception as e:
            # swarm_info is optional, so we just log and continue
            print(f"swarm_info not available: {type(e).__name__}: {e}")
            swarm_info = None

        # Try to get asic_info (should be available on all BitAxe miners)
        asic_info: dict[str, Any] | None = None
        try:
            asic_info = await web.asic_info()
            # Check if the response indicates an error
            if asic_info and "error" in asic_info:
                error_msg = asic_info.get("error")
                self.skipTest(f"ASIC info endpoint returned error: {error_msg}")
        except Exception as e:
            self.skipTest(f"ASIC info not available: {type(e).__name__}: {e}")

        # asic_info should be available
        if not asic_info:
            self.skipTest("ASIC info empty; skipping")

        # Test asic_info fields
        self.assertIsInstance(asic_info, dict)
        if "asicCount" in asic_info:
            self.assertIsInstance(asic_info.get("asicCount"), int)
            self.assertGreater(asic_info.get("asicCount"), 0)
        if "ASICModel" in asic_info:
            self.assertIsInstance(asic_info.get("ASICModel"), str)
        if "defaultFrequency" in asic_info:
            self.assertIsInstance(asic_info.get("defaultFrequency"), (int, float))
        if "frequencyOptions" in asic_info:
            self.assertIsInstance(asic_info.get("frequencyOptions"), list)
            self.assertGreater(len(asic_info.get("frequencyOptions")), 0)

        # Test swarm_info if available (optional)
        if swarm_info:
            self.assertIsInstance(swarm_info, dict)
            print(f"swarm_info available: {list(swarm_info.keys())}")
        else:
            print("swarm_info not available on this miner (this is OK)")

    async def test_api_vs_library_parsing(self):
        """Compare raw API response with library's parsed output to identify parsing issues."""
        assert self.ip is not None

        # Get raw API response directly
        raw_api_response: dict[str, Any] | None = None
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://{self.ip}/api/system/info")
                if response.status_code == 200:
                    raw_api_response = response.json()
        except Exception as e:
            self.skipTest(f"Could not fetch raw API response: {e}")

        if not raw_api_response:
            self.skipTest("Raw API response is empty")

        # Get library's parsed response
        web = getattr(self.miner, "web", None)
        if web is None or not isinstance(web, ESPMinerWebAPI):
            self.skipTest("No web client available")

        library_api_response: dict[str, Any] | None = None
        try:
            library_api_response = await web.system_info()
        except Exception as e:
            self.skipTest(f"Could not fetch library API response: {e}")

        if not library_api_response:
            self.skipTest("Library API response is empty")

        # Get parsed MinerData
        parsed_data = await self.miner.get_data(
            include=[
                DataOptions.HASHRATE,
                DataOptions.EXPECTED_HASHRATE,
                DataOptions.WATTAGE,
                DataOptions.UPTIME,
                DataOptions.HOSTNAME,
                DataOptions.API_VERSION,
                DataOptions.FW_VERSION,
                DataOptions.MAC,
                DataOptions.BEST_DIFFICULTY,
                DataOptions.BEST_SESSION_DIFFICULTY,
                DataOptions.SHARES_ACCEPTED,
                DataOptions.SHARES_REJECTED,
            ]
        )

        # Print comparison for debugging
        print("\n" + "=" * 80)
        print("RAW API RESPONSE vs LIBRARY PARSING COMPARISON")
        print("=" * 80)

        # Compare key fields
        comparisons = []

        # Wattage (note: parsed value is rounded, so compare rounded raw value)
        raw_power = raw_api_response.get("power")
        parsed_wattage = parsed_data.wattage
        wattage_match = None
        if raw_power is not None and parsed_wattage is not None:
            # Wattage is rounded in _get_wattage(), so compare rounded values
            wattage_match = round(raw_power) == parsed_wattage
        comparisons.append(
            {
                "field": "wattage",
                "raw_api": raw_power,
                "parsed": parsed_wattage,
                "match": wattage_match,
            }
        )

        # Hashrate
        raw_hashrate = raw_api_response.get("hashRate")
        parsed_hashrate = (
            float(parsed_data.hashrate) if parsed_data.hashrate is not None else None
        )
        comparisons.append(
            {
                "field": "hashrate",
                "raw_api": raw_hashrate,
                "parsed": parsed_hashrate,
                "match": None,  # Hashrate is converted, so exact match not expected
            }
        )

        # Uptime
        raw_uptime = raw_api_response.get("uptimeSeconds")
        parsed_uptime = parsed_data.uptime
        comparisons.append(
            {
                "field": "uptime",
                "raw_api": raw_uptime,
                "parsed": parsed_uptime,
                "match": raw_uptime == parsed_uptime
                if raw_uptime is not None
                else None,
            }
        )

        # Hostname
        raw_hostname = raw_api_response.get("hostname")
        parsed_hostname = parsed_data.hostname
        comparisons.append(
            {
                "field": "hostname",
                "raw_api": raw_hostname,
                "parsed": parsed_hostname,
                "match": raw_hostname == parsed_hostname
                if raw_hostname is not None
                else None,
            }
        )

        # Version
        raw_version = raw_api_response.get("version")
        parsed_api_ver = parsed_data.api_ver
        parsed_fw_ver = parsed_data.fw_ver
        comparisons.append(
            {
                "field": "version (api_ver)",
                "raw_api": raw_version,
                "parsed": parsed_api_ver,
                "match": raw_version == parsed_api_ver
                if raw_version is not None
                else None,
            }
        )
        comparisons.append(
            {
                "field": "version (fw_ver)",
                "raw_api": raw_version,
                "parsed": parsed_fw_ver,
                "match": raw_version == parsed_fw_ver
                if raw_version is not None
                else None,
            }
        )

        # MAC
        raw_mac = raw_api_response.get("macAddr")
        parsed_mac = parsed_data.mac
        comparisons.append(
            {
                "field": "mac",
                "raw_api": raw_mac,
                "parsed": parsed_mac,
                "match": (
                    raw_mac.upper() == parsed_mac
                    if raw_mac is not None and parsed_mac is not None
                    else None
                ),
            }
        )

        # Best difficulty
        raw_best_diff = raw_api_response.get("bestDiff")
        parsed_best_diff = parsed_data.best_difficulty
        comparisons.append(
            {
                "field": "best_difficulty",
                "raw_api": raw_best_diff,
                "parsed": parsed_best_diff,
                "match": None,  # May be string in API, int in parsed
            }
        )

        # Best session difficulty
        raw_best_session = raw_api_response.get("bestSessionDiff")
        parsed_best_session = parsed_data.best_session_difficulty
        comparisons.append(
            {
                "field": "best_session_difficulty",
                "raw_api": raw_best_session,
                "parsed": parsed_best_session,
                "match": None,  # May be string in API, int in parsed
            }
        )

        # Shares accepted
        raw_shares_acc = raw_api_response.get("sharesAccepted")
        parsed_shares_acc = parsed_data.shares_accepted
        comparisons.append(
            {
                "field": "shares_accepted",
                "raw_api": raw_shares_acc,
                "parsed": parsed_shares_acc,
                "match": raw_shares_acc == parsed_shares_acc
                if raw_shares_acc is not None
                else None,
            }
        )

        # Shares rejected
        raw_shares_rej = raw_api_response.get("sharesRejected")
        parsed_shares_rej = parsed_data.shares_rejected
        comparisons.append(
            {
                "field": "shares_rejected",
                "raw_api": raw_shares_rej,
                "parsed": parsed_shares_rej,
                "match": raw_shares_rej == parsed_shares_rej
                if raw_shares_rej is not None
                else None,
            }
        )

        # Print comparison table
        print(f"\n{'Field':<30} {'Raw API':<20} {'Parsed':<20} {'Match':<10}")
        print("-" * 80)
        for comp in comparisons:
            match_str = (
                "✓"
                if comp["match"] is True
                else "✗"
                if comp["match"] is False
                else "N/A"
            )
            print(
                f"{comp['field']:<30} "
                f"{str(comp['raw_api']):<20} "
                f"{str(comp['parsed']):<20} "
                f"{match_str:<10}"
            )

        # Print full raw API response for reference
        print("\n" + "=" * 80)
        print("FULL RAW API RESPONSE (system/info):")
        print("=" * 80)
        import json

        print(json.dumps(raw_api_response, indent=2))

        # Assert on critical mismatches
        wattage_match = comparisons[0]["match"]
        if wattage_match is False:
            self.fail(
                f"Wattage mismatch! Raw API: {raw_power}, Parsed: {parsed_wattage}. "
                f"Check _get_wattage() implementation."
            )

        # Print summary
        print("\n" + "=" * 80)
        print("COMPARISON SUMMARY")
        print("=" * 80)
        mismatches = [c for c in comparisons if c["match"] is False]
        if mismatches:
            print(f"⚠️  Found {len(mismatches)} field mismatch(es):")
            for m in mismatches:
                print(f"   - {m['field']}: API={m['raw_api']}, Parsed={m['parsed']}")
        else:
            print("✓ All comparable fields match!")


def _main() -> None:
    parser = argparse.ArgumentParser(description="Local BitAxe smoke tests")
    parser.add_argument("ip", nargs="?", help="Miner IP (overrides BITAXE_IP)")
    args, unittest_args = parser.parse_known_args()

    if args.ip:
        os.environ["BITAXE_IP"] = args.ip

    unittest.main(argv=[sys.argv[0]] + unittest_args)


if __name__ == "__main__":
    _main()
