"""
Agent Discovery Utility

Automatically discovers agents from local filesystem and Azure Storage,
extracts metadata, generates categories, and creates intelligent presets.
"""
import os
import sys
import importlib
import importlib.util
import inspect
import json
import logging
from typing import Dict, List, Any, Optional
from agents.basic_agent import BasicAgent


class AgentDiscovery:
    """Discovers and analyzes agents from filesystem"""

    def __init__(self, agents_dir: str = None):
        self.agents_dir = agents_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents")
        self.discovered_agents = {}
        self.categories = {}
        self.suggested_presets = []

    def discover_all_agents(self) -> Dict[str, Any]:
        """Discover all agents from local filesystem"""
        logging.info(f"Discovering agents in: {self.agents_dir}")

        if not os.path.exists(self.agents_dir):
            logging.error(f"Agents directory not found: {self.agents_dir}")
            return {}

        agent_files = [
            f for f in os.listdir(self.agents_dir)
            if f.endswith('.py') and f not in ['__init__.py', 'basic_agent.py']
        ]

        for filename in agent_files:
            try:
                agent_info = self._load_agent_from_file(filename)
                if agent_info:
                    self.discovered_agents[agent_info['name']] = agent_info
            except Exception as e:
                logging.error(f"Error loading agent from {filename}: {str(e)}")
                continue

        # Auto-generate categories
        self._auto_categorize_agents()

        # Auto-generate presets
        self._auto_generate_presets()

        return self.discovered_agents

    def _load_agent_from_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load a single agent file and extract all metadata via static analysis"""
        filepath = os.path.join(self.agents_dir, filename)

        try:
            # Read the file to extract docstring and metadata
            with open(filepath, 'r') as f:
                file_content = f.read()

            # Parse metadata from file content (no import required)
            agent_name = self._parse_agent_name(file_content, filename)
            metadata_dict = self._parse_metadata_dict(file_content)
            class_name = self._parse_class_name(file_content)

            if not agent_name:
                logging.warning(f"Could not parse agent name from {filename}")
                return None

            # Extract all metadata
            agent_info = {
                'name': agent_name,
                'filename': filename,
                'class_name': class_name or filename[:-3].title().replace('_', ''),
                'metadata': metadata_dict,
                'description': metadata_dict.get('description', 'No description available'),
                'parameters': metadata_dict.get('parameters', {}),
                'docstring': self._parse_class_docstring(file_content),
                'file_docstring': self._extract_file_docstring(file_content),
                'capabilities': self._extract_capabilities_from_params(metadata_dict.get('parameters', {})),
                'category': self._infer_category_from_content(agent_name, metadata_dict.get('description', ''), filename),
                'tags': self._extract_tags_from_content(metadata_dict.get('description', ''), file_content),
                'use_cases': self._extract_use_cases(file_content),
                'dependencies': self._extract_dependencies(file_content),
            }

            return agent_info

        except Exception as e:
            logging.error(f"Error loading {filename}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_agent_name(self, file_content: str, filename: str) -> Optional[str]:
        """Parse agent name from self.name = '...' assignment"""
        import re

        # Look for self.name = 'AgentName' or self.name = "AgentName"
        match = re.search(r"self\.name\s*=\s*['\"]([^'\"]+)['\"]", file_content)
        if match:
            return match.group(1)

        # Fallback: derive from filename
        return filename[:-9].replace('_', ' ').title().replace(' ', '')

    def _parse_class_name(self, file_content: str) -> Optional[str]:
        """Parse class name from class definition"""
        import re

        # Look for class ClassName(BasicAgent):
        match = re.search(r'class\s+(\w+)\s*\(.*BasicAgent.*\):', file_content)
        if match:
            return match.group(1)

        return None

    def _parse_metadata_dict(self, file_content: str) -> Dict[str, Any]:
        """Parse metadata dictionary from self.metadata = {...}"""
        import re
        import ast

        # Find the metadata assignment
        # Look for self.metadata = { ... }
        match = re.search(
            r'self\.metadata\s*=\s*(\{[^}]+\}.*?\n\s*\})',
            file_content,
            re.DOTALL
        )

        if not match:
            return {}

        try:
            # Extract the dictionary string
            dict_str = match.group(1)

            # Try to parse as Python literal
            metadata = ast.literal_eval(dict_str)
            return metadata
        except:
            # If literal_eval fails, try a more lenient approach
            try:
                # Use json.loads after some cleanup
                dict_str = match.group(1)
                # Replace single quotes with double quotes
                dict_str = dict_str.replace("'", '"')
                metadata = json.loads(dict_str)
                return metadata
            except:
                logging.warning("Could not parse metadata dictionary")
                return {}

    def _parse_class_docstring(self, file_content: str) -> str:
        """Parse class-level docstring"""
        import re

        # Look for class definition followed by docstring
        match = re.search(
            r'class\s+\w+\s*\([^)]+\):\s*"""([^"]+)"""',
            file_content,
            re.DOTALL
        )

        if match:
            return match.group(1).strip()

        return ""

    def _extract_capabilities_from_params(self, params: Dict[str, Any]) -> List[str]:
        """Extract capabilities from parameter schema"""
        capabilities = []

        properties = params.get('properties', {})

        # Infer capabilities from parameters
        for param_name, param_info in properties.items():
            if param_name not in ['user_guid', 'user_id', 'session_id']:
                desc = param_info.get('description', '')
                if desc:
                    capabilities.append(f"{param_name}: {desc}")

        return capabilities

    def _infer_category_from_content(self, agent_name: str, description: str, filename: str) -> str:
        """Intelligently infer category from agent name, description, and parameters"""
        name = agent_name.lower()
        desc = description.lower()
        filename_lower = filename.lower()

        # Category inference rules
        category_keywords = {
            'Memory': ['memory', 'context', 'recall', 'remember', 'history'],
            'Commerce': ['order', 'purchase', 'payment', 'checkout', 'cart', 'upsell', 'sales', 'verification'],
            'Communication': ['email', 'message', 'notify', 'slack', 'teams', 'chat'],
            'Analytics': ['analyze', 'analytics', 'report', 'metrics', 'dashboard', 'insights', 'contract'],
            'Document': ['document', 'pdf', 'contract', 'file', 'upload', 'download'],
            'CRM': ['crm', 'salesforce', 'dynamics', 'customer', 'lead', 'contact'],
            'Automation': ['workflow', 'automate', 'schedule', 'trigger', 'pipeline'],
            'Development': ['code', 'github', 'git', 'deploy', 'build', 'test', 'library'],
            'Entertainment': ['game', 'dungeon', 'play', 'fun', 'interactive', 'dnd', 'master'],
            'Utilities': ['demo', 'playground', 'test', 'helper', 'utility', 'tool', 'prompt'],
        }

        # Check keywords against name, description, and filename
        search_text = f"{name} {desc} {filename_lower}"

        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in search_text)
            if score > 0:
                category_scores[category] = score

        # Return category with highest score
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]

        return 'Other'

    def _extract_tags_from_content(self, description: str, file_content: str) -> List[str]:
        """Extract relevant tags from agent"""
        tags = []

        # Extract from description
        desc = description.lower()

        tag_keywords = [
            'ai', 'ml', 'nlp', 'gpt', 'openai',
            'customer', 'service', 'support',
            'sales', 'marketing', 'analytics',
            'automation', 'workflow', 'integration',
            'data', 'storage', 'database',
            'api', 'webhook', 'rest',
        ]

        for keyword in tag_keywords:
            if keyword in desc or keyword in file_content.lower():
                tags.append(keyword)

        return list(set(tags))  # Remove duplicates

    def _extract_file_docstring(self, file_content: str) -> str:
        """Extract module-level docstring from file content"""
        lines = file_content.split('\n')
        docstring_lines = []
        in_docstring = False
        quote_style = None

        for line in lines:
            stripped = line.strip()

            # Check for start of docstring
            if not in_docstring:
                if stripped.startswith('"""'):
                    in_docstring = True
                    quote_style = '"""'
                    # Check if it's a single-line docstring
                    if stripped.endswith('"""') and len(stripped) > 6:
                        return stripped[3:-3]
                    if len(stripped) > 3:
                        docstring_lines.append(stripped[3:])
                elif stripped.startswith("'''"):
                    in_docstring = True
                    quote_style = "'''"
                    if stripped.endswith("'''") and len(stripped) > 6:
                        return stripped[3:-3]
                    if len(stripped) > 3:
                        docstring_lines.append(stripped[3:])
            else:
                # Check for end of docstring
                if stripped.endswith(quote_style):
                    if len(stripped) > 3:
                        docstring_lines.append(stripped[:-3])
                    break
                else:
                    docstring_lines.append(line)

        return '\n'.join(docstring_lines).strip()

    def _extract_capabilities(self, agent_instance: BasicAgent) -> List[str]:
        """Extract capabilities from parameter schema"""
        capabilities = []

        if hasattr(agent_instance, 'metadata'):
            params = agent_instance.metadata.get('parameters', {})
            properties = params.get('properties', {})

            # Infer capabilities from parameters
            for param_name, param_info in properties.items():
                if param_name not in ['user_guid', 'user_id', 'session_id']:
                    desc = param_info.get('description', '')
                    if desc:
                        capabilities.append(f"{param_name}: {desc}")

        return capabilities

    def _infer_category(self, agent_instance: BasicAgent, filename: str) -> str:
        """Intelligently infer category from agent name, description, and parameters"""
        name = agent_instance.name.lower()
        desc = self._extract_description(agent_instance).lower()
        filename_lower = filename.lower()

        # Category inference rules
        category_keywords = {
            'Memory': ['memory', 'context', 'recall', 'remember', 'history'],
            'Commerce': ['order', 'purchase', 'payment', 'checkout', 'cart', 'upsell', 'sales'],
            'Communication': ['email', 'message', 'notify', 'slack', 'teams', 'chat'],
            'Analytics': ['analyze', 'analytics', 'report', 'metrics', 'dashboard', 'insights'],
            'Document': ['document', 'pdf', 'contract', 'file', 'upload', 'download'],
            'CRM': ['crm', 'salesforce', 'dynamics', 'customer', 'lead', 'contact'],
            'Automation': ['workflow', 'automate', 'schedule', 'trigger', 'pipeline'],
            'Development': ['code', 'github', 'git', 'deploy', 'build', 'test'],
            'Entertainment': ['game', 'dungeon', 'play', 'fun', 'interactive'],
            'Utilities': ['demo', 'playground', 'test', 'helper', 'utility', 'tool'],
        }

        # Check keywords against name, description, and filename
        search_text = f"{name} {desc} {filename_lower}"

        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in search_text)
            if score > 0:
                category_scores[category] = score

        # Return category with highest score
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]

        return 'Other'

    def _extract_tags(self, agent_instance: BasicAgent, file_content: str) -> List[str]:
        """Extract relevant tags from agent"""
        tags = []

        # Add category as tag
        category = self._infer_category(agent_instance, "")
        if category != 'Other':
            tags.append(category.lower())

        # Extract from description
        desc = self._extract_description(agent_instance).lower()

        tag_keywords = [
            'ai', 'ml', 'nlp', 'gpt', 'openai',
            'customer', 'service', 'support',
            'sales', 'marketing', 'analytics',
            'automation', 'workflow', 'integration',
            'data', 'storage', 'database',
            'api', 'webhook', 'rest',
        ]

        for keyword in tag_keywords:
            if keyword in desc:
                tags.append(keyword)

        return list(set(tags))  # Remove duplicates

    def _extract_use_cases(self, file_content: str) -> List[str]:
        """Extract use cases from docstring"""
        use_cases = []

        # Look for "Perfect for:", "Use cases:", etc.
        patterns = [
            'perfect for:',
            'use cases:',
            'use for:',
            'ideal for:',
            'best for:',
        ]

        content_lower = file_content.lower()
        for pattern in patterns:
            if pattern in content_lower:
                # Extract the line after the pattern
                lines = file_content.split('\n')
                for i, line in enumerate(lines):
                    if pattern in line.lower():
                        # Collect following lines until we hit an empty line or section
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j].strip()
                            if not next_line or next_line.startswith('#') or next_line.startswith('"""'):
                                break
                            if next_line:
                                use_cases.append(next_line.lstrip('-*• '))
                            j += 1
                        break

        return use_cases

    def _extract_dependencies(self, file_content: str) -> List[str]:
        """Extract agent dependencies from import statements"""
        dependencies = []

        lines = file_content.split('\n')
        for line in lines:
            # Look for agent imports
            if 'from agents.' in line or 'import agents.' in line:
                # Extract agent name
                if 'import' in line:
                    parts = line.split('import')
                    if len(parts) > 1:
                        imported = parts[1].strip().split()[0]
                        if imported != 'BasicAgent':
                            dependencies.append(imported)

        return dependencies

    def _auto_categorize_agents(self):
        """Organize agents by category"""
        self.categories = {}

        for agent_name, agent_info in self.discovered_agents.items():
            category = agent_info['category']

            if category not in self.categories:
                self.categories[category] = []

            self.categories[category].append(agent_name)

    def _auto_generate_presets(self):
        """Automatically generate intelligent presets based on agent combinations"""
        self.suggested_presets = []

        # Preset 1: Full Suite (all agents)
        self.suggested_presets.append({
            'name': 'Full Suite',
            'description': 'All agents enabled for maximum functionality',
            'agents': None,  # None means all agents
            'settings': {},
            'icon': '🌟',
            'auto_generated': True
        })

        # Preset 2: Category-based presets
        for category, agent_names in self.categories.items():
            if len(agent_names) > 0:
                # Get filenames for these agents
                agent_filenames = [
                    self.discovered_agents[name]['filename']
                    for name in agent_names
                    if name in self.discovered_agents
                ]

                self.suggested_presets.append({
                    'name': f'{category} Suite',
                    'description': f'All {category.lower()} agents',
                    'agents': agent_filenames,
                    'settings': {},
                    'icon': self._get_category_icon(category),
                    'auto_generated': True
                })

        # Preset 3: Common combinations
        # Memory + Commerce (Customer Service)
        memory_agents = self.categories.get('Memory', [])
        commerce_agents = self.categories.get('Commerce', [])

        if memory_agents and commerce_agents:
            combined = memory_agents + commerce_agents
            agent_filenames = [
                self.discovered_agents[name]['filename']
                for name in combined
                if name in self.discovered_agents
            ]

            self.suggested_presets.append({
                'name': 'Customer Service',
                'description': 'Memory and commerce agents for customer interactions',
                'agents': agent_filenames,
                'settings': {'enable_upsell': True},
                'icon': '🛒',
                'auto_generated': True
            })

        # Preset 4: Essential (Memory only)
        if memory_agents:
            agent_filenames = [
                self.discovered_agents[name]['filename']
                for name in memory_agents
                if name in self.discovered_agents
            ]

            self.suggested_presets.append({
                'name': 'Essential',
                'description': 'Core memory agents for basic conversations',
                'agents': agent_filenames,
                'settings': {},
                'icon': '⭐',
                'auto_generated': True
            })

    def _get_category_icon(self, category: str) -> str:
        """Get icon for category"""
        icons = {
            'Memory': '🧠',
            'Commerce': '🛒',
            'Communication': '💬',
            'Analytics': '📊',
            'Document': '📄',
            'CRM': '👥',
            'Automation': '⚙️',
            'Development': '💻',
            'Entertainment': '🎮',
            'Utilities': '🔧',
        }
        return icons.get(category, '📦')

    def get_agent_manifest(self) -> Dict[str, Any]:
        """Generate a complete manifest of all discovered agents"""
        return {
            'agents': self.discovered_agents,
            'categories': self.categories,
            'suggested_presets': self.suggested_presets,
            'statistics': {
                'total_agents': len(self.discovered_agents),
                'total_categories': len(self.categories),
                'total_presets': len(self.suggested_presets),
            }
        }

    def export_manifest(self, output_path: str = None):
        """Export manifest to JSON file"""
        manifest = self.get_agent_manifest()

        if output_path is None:
            output_path = os.path.join(self.agents_dir, '..', 'agent_manifest.json')

        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        logging.info(f"Manifest exported to: {output_path}")
        return output_path


def main():
    """CLI entry point for agent discovery"""
    logging.basicConfig(level=logging.INFO)

    discovery = AgentDiscovery()
    discovery.discover_all_agents()

    # Print summary
    manifest = discovery.get_agent_manifest()

    print("\n" + "="*60)
    print("AGENT DISCOVERY SUMMARY")
    print("="*60)

    print(f"\n📦 Total Agents: {manifest['statistics']['total_agents']}")
    print(f"📁 Total Categories: {manifest['statistics']['total_categories']}")
    print(f"⚙️ Total Presets: {manifest['statistics']['total_presets']}")

    print("\n" + "-"*60)
    print("AGENTS BY CATEGORY")
    print("-"*60)

    for category, agents in manifest['categories'].items():
        icon = discovery._get_category_icon(category)
        print(f"\n{icon} {category} ({len(agents)} agents):")
        for agent_name in agents:
            agent_info = manifest['agents'][agent_name]
            print(f"  - {agent_name}")
            print(f"    {agent_info['description'][:80]}...")

    print("\n" + "-"*60)
    print("AUTO-GENERATED PRESETS")
    print("-"*60)

    for preset in manifest['suggested_presets']:
        print(f"\n{preset['icon']} {preset['name']}")
        print(f"  {preset['description']}")
        if preset['agents']:
            print(f"  Agents: {len(preset['agents'])}")

    # Export manifest
    output_path = discovery.export_manifest()
    print(f"\n✅ Manifest exported to: {output_path}")


if __name__ == '__main__':
    main()
