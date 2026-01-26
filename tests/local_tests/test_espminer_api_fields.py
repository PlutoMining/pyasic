#!/usr/bin/env python3
"""Test script to check which fields the ESPMiner PATCH /api/system endpoint accepts.

This script tests individual fields to see which ones the API accepts.
Run with: BITAXE_IP=<ip> poetry run python tests/local_tests/test_espminer_api_fields.py
"""

import asyncio
import os
import sys
from typing import Any

import httpx

from pyasic.config import MinerConfig, PoolConfig
from pyasic.config.extra_config.espminer import ESPMinerExtraConfig


async def test_field(ip: str, field_name: str, field_value: Any) -> tuple[bool, str]:
    """Test if a single field is accepted by the API.

    Returns:
        (success, message) tuple
    """
    url = f"http://{ip}/api/system"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.patch(url, json={field_name: field_value})

            if response.status_code == 200:
                try:
                    result = response.json()
                    return True, f"Accepted: {result}"
                except Exception as e:
                    return False, f"Status 200 but invalid JSON: {e}"
            else:
                return False, f"Status {response.status_code}: {response.text[:100]}"
    except Exception as e:
        return False, f"Error: {e}"


async def main():
    ip = os.getenv("BITAXE_IP")
    if not ip:
        print("Error: Set BITAXE_IP environment variable")
        sys.exit(1)

    print(f"Testing ESPMiner API fields on {ip}")
    print("=" * 80)

    # Get current config to use as baseline
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://{ip}/api/system/info")
            if response.status_code == 200:
                current_config = response.json()
                print(f"Current config has {len(current_config)} fields")
            else:
                print(f"Failed to get current config: {response.status_code}")
                current_config = {}
    except Exception as e:
        print(f"Failed to get current config: {e}")
        current_config = {}

    print("\nTesting extra_config fields:")
    print("-" * 80)

    # Test each extra_config field individually
    test_fields = {
        "rotation": 0,  # Try setting to 0 (current value)
        "invertscreen": 0,  # Try setting to 0 (current value)
        "displayTimeout": 1,  # Try setting to 1 (current value)
        "overheat_mode": 0,  # Try setting to 0 (current value)
        "overclockEnabled": 0,  # Try setting to 0 (current value)
        "statsFrequency": 0,  # Try setting to 0 (current value)
        "minFanSpeed": 25,  # Try setting to 25 (current value)
        "networkDifficulty": 146472570619930,  # Try setting (read-only, should fail)
    }

    results = {}
    for field_name, test_value in test_fields.items():
        print(f"\nTesting {field_name} = {test_value}...")
        success, message = await test_field(ip, field_name, test_value)
        results[field_name] = (success, message)
        status = "✓ ACCEPTED" if success else "✗ REJECTED"
        print(f"  {status}: {message}")
        # Small delay to avoid overwhelming the API
        await asyncio.sleep(0.5)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    accepted = [name for name, (success, _) in results.items() if success]
    rejected = [name for name, (success, _) in results.items() if not success]

    print(f"\nAccepted fields ({len(accepted)}):")
    for name in accepted:
        print(f"  ✓ {name}")

    print(f"\nRejected/Ignored fields ({len(rejected)}):")
    for name in rejected:
        success, msg = results[name]
        print(f"  ✗ {name}: {msg[:60]}")

    print("\n" + "=" * 80)
    print("Note: Some fields may be read-only and will be rejected.")
    print(
        "Some fields may be accepted but not persisted (check by reading config back)."
    )


if __name__ == "__main__":
    asyncio.run(main())
