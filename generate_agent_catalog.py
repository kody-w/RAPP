#!/usr/bin/env python3
"""
Generate agent catalog from AI-Agent-Templates metadata.json files
"""
import json
import os
from pathlib import Path

def parse_metadata_files():
    """Parse all metadata.json files and generate agent catalog"""
    agents = []
    base_path = Path("AI-Agent-Templates/agent_stacks")

    # Category mapping to icons and display names
    category_map = {
        'b2b_sales_stacks': {'icon': '💼', 'name': 'B2B Sales', 'display': 'B2B Sales'},
        'b2c_sales_stacks': {'icon': '🛒', 'name': 'B2C Sales', 'display': 'B2C Sales'},
        'customer_service_stacks': {'icon': '💬', 'name': 'Customer Service', 'display': 'Customer Service'},
        'energy_stacks': {'icon': '⚡', 'name': 'Energy', 'display': 'Energy'},
        'federal_government_stacks': {'icon': '🏛️', 'name': 'Federal Gov', 'display': 'Federal Government'},
        'financial_services_stacks': {'icon': '💰', 'name': 'Financial Services', 'display': 'Financial Services'},
        'general_stacks': {'icon': '🔧', 'name': 'General', 'display': 'Utilities'},
        'healthcare_stacks': {'icon': '🏥', 'name': 'Healthcare', 'display': 'Healthcare'},
        'human_resources_stacks': {'icon': '👥', 'name': 'HR', 'display': 'Human Resources'},
        'it_management_stacks': {'icon': '💻', 'name': 'IT Management', 'display': 'Development'},
        'manufacturing_stacks': {'icon': '🏭', 'name': 'Manufacturing', 'display': 'Manufacturing'},
        'professional_services_stacks': {'icon': '📊', 'name': 'Professional Services', 'display': 'Professional Services'},
        'retail_cpg_stacks': {'icon': '🏪', 'name': 'Retail & CPG', 'display': 'Retail & CPG'},
        'slg_government_stacks': {'icon': '🏢', 'name': 'State/Local Gov', 'display': 'State/Local Government'},
        'software_dp_stacks': {'icon': '🚀', 'name': 'Software Dev', 'display': 'Development'}
    }

    # Iterate through all stack categories
    for category_dir in base_path.iterdir():
        if not category_dir.is_dir():
            continue

        # Skip copy directories
        if 'copy' in category_dir.name:
            continue

        category_info = category_map.get(category_dir.name, {'icon': '📦', 'name': 'Other', 'display': 'Utilities'})

        # Find all metadata.json files in this category
        for metadata_file in category_dir.rglob('metadata.json'):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)

                # Extract stack directory name
                stack_dir = metadata_file.parent.name
                stack_id = stack_dir.replace('_stack', '').replace('_', '-')

                # Generate agent entry
                agent = {
                    'id': stack_id,
                    'name': metadata.get('name', stack_dir.replace('_', ' ').title()),
                    'category': category_info['display'],
                    'shortDescription': metadata.get('description', 'AI-powered agent for automation'),
                    'tags': metadata.get('tags', []),
                    'rating': metadata.get('rating', 4.5),
                    'installs': metadata.get('installs', 1000),
                    'version': metadata.get('version', '1.0.0'),
                    'author': metadata.get('author', 'Kody Wildfeuer'),
                    'sizeKb': metadata.get('size_kb', 100),
                    'icon': category_info['icon']
                }

                agents.append(agent)

            except Exception as e:
                print(f"Error processing {metadata_file}: {e}")
                continue

    return agents

def generate_javascript_array(agents):
    """Generate JavaScript array code for agent_store.html"""
    js_code = "        const sampleAgents = [\n"

    for agent in agents:
        # Escape quotes in strings
        name = agent['name'].replace("'", "\\'")
        desc = agent['shortDescription'].replace("'", "\\'")

        js_code += "            {\n"
        js_code += f"                id: '{agent['id']}',\n"
        js_code += f"                name: '{name}',\n"
        js_code += f"                category: '{agent['category']}',\n"
        js_code += f"                shortDescription: '{desc}',\n"
        js_code += f"                tags: {json.dumps(agent['tags'])},\n"
        js_code += f"                rating: {agent['rating']},\n"
        js_code += f"                installs: {agent['installs']},\n"
        js_code += f"                version: '{agent['version']}',\n"
        js_code += f"                author: '{agent['author']}',\n"
        js_code += f"                sizeKb: {agent['sizeKb']},\n"
        js_code += f"                icon: '{agent['icon']}'\n"
        js_code += "            },\n"

    js_code += "        ];\n"

    return js_code

def main():
    print("🔍 Parsing metadata files...")
    agents = parse_metadata_files()

    print(f"✅ Found {len(agents)} agent stacks")

    # Calculate statistics
    total_installs = sum(agent['installs'] for agent in agents)
    avg_rating = sum(agent['rating'] for agent in agents) / len(agents) if agents else 0

    print(f"📊 Total Installs: {total_installs:,}")
    print(f"⭐ Average Rating: {avg_rating:.1f}")

    # Group by category
    by_category = {}
    for agent in agents:
        cat = agent['category']
        by_category[cat] = by_category.get(cat, 0) + 1

    print(f"\n📁 Agents by Category:")
    for cat, count in sorted(by_category.items()):
        print(f"  {cat}: {count} agents")

    # Generate JavaScript
    print(f"\n💾 Generating JavaScript array...")
    js_code = generate_javascript_array(agents)

    # Save to file
    output_file = "agent_catalog_generated.js"
    with open(output_file, 'w') as f:
        f.write(js_code)

    print(f"✅ Saved to {output_file}")
    print(f"\n📋 Statistics for agent_store.html:")
    print(f"  Total Agents: {len(agents)}")
    print(f"  Total Installs: {total_installs // 1000}K")
    print(f"  Average Rating: {avg_rating:.1f}")

if __name__ == '__main__':
    main()
