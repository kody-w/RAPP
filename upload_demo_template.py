#!/usr/bin/env python3
"""
Upload the demo script HTML template to Azure File Storage.

This template is used by ScriptedDemoAgent to generate shareable demo scripts.
"""

import os
from utils.azure_file_storage import AzureFileStorageManager


def upload_template():
    """Upload demo_script_template.html to Azure File Storage."""

    template_file = 'demo_script_template.html'

    if not os.path.exists(template_file):
        print(f"❌ Error: {template_file} not found in current directory")
        print(f"   Current directory: {os.getcwd()}")
        return False

    try:
        # Read template
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()

        print(f"📄 Read template: {len(template_content)} bytes")

        # Upload to Azure File Storage (root share)
        storage = AzureFileStorageManager()
        storage.write_file('', template_file, template_content)

        print(f"✅ Successfully uploaded {template_file} to Azure File Storage")
        print(f"   Location: root share / {template_file}")
        print(f"\nThe ScriptedDemoAgent can now generate demo script HTML pages!")

        return True

    except Exception as e:
        print(f"❌ Error uploading template: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 70)
    print("Demo Script Template Uploader")
    print("=" * 70)
    print()

    success = upload_template()

    print()
    print("=" * 70)
    if success:
        print("✅ Setup Complete!")
        print("\nNext steps:")
        print("1. Add 'auto_trigger_guids' to your demo JSON files")
        print("2. Restart your Azure Function")
        print("3. Test with a configured GUID")
        print("4. The demo response will include a link to the script HTML")
    else:
        print("❌ Upload Failed")
        print("\nTroubleshooting:")
        print("1. Ensure local.settings.json is configured correctly")
        print("2. Check Azure Storage connection string")
        print("3. Verify demo_script_template.html exists in this directory")
    print("=" * 70)
