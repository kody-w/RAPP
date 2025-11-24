#!/usr/bin/env python3
"""
Test script for Order Verification Agent
Demonstrates the McDonald's-style order verification and upselling
"""

# Mock the Azure storage to test without Azure credentials
class MockAzureFileStorageManager:
    def __init__(self):
        self.current_guid = None

    def set_memory_context(self, guid):
        self.current_guid = guid

    def read_file(self, share, path):
        return None

    def write_file(self, share, path, content):
        pass

# Monkey patch the import
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Replace the real storage manager with mock
import utils.azure_file_storage as storage_module
storage_module.AzureFileStorageManager = MockAzureFileStorageManager

# Now import the agent
from agents.order_verification_agent import OrderVerificationAgent


def test_order(customer_input, description):
    """Test a single order scenario"""
    print("=" * 80)
    print(f"TEST: {description}")
    print("=" * 80)
    print(f"Customer says: \"{customer_input}\"\n")

    agent = OrderVerificationAgent()
    result = agent.perform(customer_input=customer_input, enable_upsell=True)

    print(result)
    print("\n")


if __name__ == "__main__":
    print("\n🍔 ORDER VERIFICATION AGENT TEST SUITE\n")

    # Test 1: The classic McDonald's example
    test_order(
        "I'll have a Big Mac and a Coke",
        "Classic McDonald's Order - Missing Fries & Size"
    )

    # Test 2: Complete order
    test_order(
        "Give me a Quarter Pounder, large fries, and a medium Sprite",
        "Complete Order - Should Still Upsell"
    )

    # Test 3: Multiple items
    test_order(
        "I want two cheeseburgers and three small Cokes",
        "Multiple Quantities - Missing Sides"
    )

    # Test 4: Breakfast order
    test_order(
        "Can I get an Egg McMuffin",
        "Breakfast Order - Missing Everything"
    )

    # Test 5: Nuggets order
    test_order(
        "10-piece chicken nuggets please",
        "Nuggets Only - Missing Sides and Drink"
    )

    # Test 6: Just drinks
    test_order(
        "Two large Cokes",
        "Drinks Only - No Food"
    )

    # Test 7: Coffee shop
    test_order(
        "I'd like a grande latte",
        "Coffee Shop - Should Suggest Food Pairing"
    )

    print("=" * 80)
    print("✅ All tests complete!")
    print("=" * 80)
