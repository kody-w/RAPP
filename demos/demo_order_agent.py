#!/usr/bin/env python3
"""
Standalone demo of Order Verification Agent
Shows the core logic without Azure dependencies
"""
import re


class OrderDemo:
    def __init__(self):
        self.menu = {
            "big mac": {"price": 5.99, "category": "burger"},
            "quarter pounder": {"price": 6.49, "category": "burger"},
            "cheeseburger": {"price": 2.99, "category": "burger"},
            "fries": {"price": 2.49, "category": "side", "size_options": ["small", "medium", "large"]},
            "coke": {"price": 1.99, "category": "drink", "size_options": ["small", "medium", "large"]},
            "sprite": {"price": 1.99, "category": "drink", "size_options": ["small", "medium", "large"]},
            "chicken nuggets": {"price": 4.99, "category": "chicken", "size_options": ["6-piece", "10-piece", "20-piece"]},
        }

    def parse_order(self, customer_input):
        """Parse customer input into items"""
        parsed_items = []
        input_lower = customer_input.lower()

        for item_name, item_data in self.menu.items():
            if item_name in input_lower:
                # Extract size
                size = None
                if 'size_options' in item_data:
                    for size_option in item_data['size_options']:
                        if size_option in input_lower:
                            size = size_option
                            break
                    if not size:
                        size = "medium"  # default

                parsed_items.append({
                    'name': item_name,
                    'size': size,
                    'price': item_data['price'],
                    'category': item_data['category']
                })

        return parsed_items

    def verify_order(self, customer_input):
        """Main verification logic"""
        print(f"\n{'='*60}")
        print(f"🎤 Customer says: \"{customer_input}\"")
        print(f"{'='*60}\n")

        items = self.parse_order(customer_input)

        if not items:
            print("❌ I didn't catch any menu items. Could you repeat that?")
            return

        # Show what was heard
        print("✅ I heard you order:")
        total = 0
        for item in items:
            size_text = f"{item['size']} " if item['size'] else ""
            print(f"   - {size_text}{item['name'].title()} (${item['price']:.2f})")
            total += item['price']

        print()

        # Validation checks
        categories = [item['category'] for item in items]
        has_main = any(cat in ['burger', 'chicken'] for cat in categories)
        has_side = 'side' in categories
        has_drink = 'drink' in categories

        print("⚠️  Let me verify:")
        if has_main and not has_side:
            print("   - I notice you didn't order fries. Did you want fries? 🍟")

        if not has_drink:
            print("   - No drink? What size Coke would you like? 🥤")
        elif has_drink:
            # Check if size was specified
            drink_items = [item for item in items if item['category'] == 'drink']
            for drink in drink_items:
                if drink['size'] == 'medium':
                    print(f"   - I have your {drink['name']} as medium - is that correct?")

        print()

        # Upselling
        print("💡 Suggestions:")
        if has_main and not has_side:
            print(f"   - That {items[0]['name'].title()} pairs great with our fries")
            print("     → Add medium fries for just $2.49? 🔥")

        if not has_drink:
            print("   - Can I get you a medium Coke for just $1.99? 🥤")
        elif has_drink and 'medium' in str([i['size'] for i in items if i['category'] == 'drink']):
            print("   - Upgrade to large for just 50¢ more? 📈")

        print()
        print(f"💰 Current Total: ${total:.2f}")
        print("\n💬 Say 'yes' to confirm, or tell me what to add/change.\n")


if __name__ == "__main__":
    demo = OrderDemo()

    print("\n" + "="*60)
    print("🍔 ORDER VERIFICATION AGENT DEMO")
    print("="*60)

    # Test Case 1: The McDonald's example
    demo.verify_order("I'll have a Big Mac and a Coke")

    # Test Case 2: Incomplete order
    demo.verify_order("Can I get a Quarter Pounder")

    # Test Case 3: Complete order
    demo.verify_order("Give me a cheeseburger, large fries, and a large Sprite")

    # Test Case 4: Nuggets only
    demo.verify_order("10-piece chicken nuggets please")

    print("="*60)
    print("✅ Demo complete! This shows real-time order verification,")
    print("   error prevention, and intelligent upselling.")
    print("="*60 + "\n")
