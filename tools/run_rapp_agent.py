#!/usr/bin/env python3
"""
RAPP Meta-Agent CLI Runner
===========================

Command-line interface for running .rapp development agents.

Usage:
    python tools/run_rapp_agent.py <agent_name> [options]

Examples:
    # Run repository health audit
    python tools/run_rapp_agent.py repository_steward --action audit
    
    # Generate a new agent
    python tools/run_rapp_agent.py agent_generator --name "my_agent" --description "Does X"
    
    # Full health check
    python tools/run_rapp_agent.py repository_steward --action full

Available Agents:
    - repository_steward: Repository health monitoring
    - agent_generator: Create new agents from templates
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from openai import AzureOpenAI, OpenAI
except ImportError:
    print("Error: OpenAI package not installed. Run: pip install openai")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    # dotenv is optional, we can load from local.settings.json instead
    def load_dotenv(*args, **kwargs):
        pass


def get_openai_client():
    """Initialize and return OpenAI client based on environment configuration."""
    load_dotenv()
    
    api_type = os.getenv("OPENAI_API_TYPE", "azure")
    
    if api_type == "azure":
        client = AzureOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            api_version=os.getenv("OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("OPENAI_API_ENDPOINT")
        )
    else:
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_ENDPOINT")
        )
    
    return client


def run_repository_steward(args):
    """Run the Repository Steward agent."""
    # Load environment from local.settings.json
    load_dotenv(project_root / "local.settings.json")
    
    # Import after setting up path
    sys.path.insert(0, str(project_root / ".rapp"))
    from agents.repository_steward import RepositorySteward
    
    # Repository Steward doesn't need AI client for static analysis
    steward = RepositorySteward(client=None)
    
    # Determine action
    action = args.action or "full"
    user_input = f"Run {action} repository audit"
    
    print(f"\n🔍 Running Repository Steward - {action.upper()} audit\n")
    print("=" * 80)
    
    response, _ = steward.execute(user_input, [], user_guid="cli_user")
    
    print(response)
    print("\n" + "=" * 80)
    print("✓ Audit complete")


def run_agent_generator(args):
    """Run the Agent Generator."""
    # Load environment from local.settings.json
    load_dotenv(project_root / "local.settings.json")
    
    # Import after setting up path
    sys.path.insert(0, str(project_root / ".rapp"))
    from agents.agent_generator import AgentGenerator
    
    client = get_openai_client()
    generator = AgentGenerator(client)
    
    # Build user input from args
    if args.name and args.description:
        user_input = f"Create a new agent called '{args.name}' that {args.description}"
    elif args.prompt:
        user_input = args.prompt
    else:
        print("Error: Must provide either --name and --description, or --prompt")
        return
    
    print(f"\n🤖 Generating new agent...\n")
    print("=" * 80)
    
    response, _ = generator.execute(user_input, [], user_guid="cli_user")
    
    print(response)
    print("\n" + "=" * 80)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run RAPP meta-agents for development tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s repository_steward --action full
  %(prog)s repository_steward --action dependencies
  %(prog)s agent_generator --name "my_agent" --description "summarizes emails"
  %(prog)s agent_generator --prompt "Create an agent that analyzes code quality"
        """
    )
    
    parser.add_argument(
        "agent",
        choices=["repository_steward", "agent_generator"],
        help="Which meta-agent to run"
    )
    
    # Repository Steward options
    parser.add_argument(
        "--action",
        choices=["full", "dependencies", "agents", "documentation", "security"],
        help="Type of audit to run (repository_steward only)"
    )
    
    # Agent Generator options
    parser.add_argument(
        "--name",
        help="Name for new agent (agent_generator only)"
    )
    
    parser.add_argument(
        "--description",
        help="Description of new agent (agent_generator only)"
    )
    
    parser.add_argument(
        "--prompt",
        help="Full prompt for agent generation (agent_generator only)"
    )
    
    args = parser.parse_args()
    
    # Route to appropriate agent
    if args.agent == "repository_steward":
        run_repository_steward(args)
    elif args.agent == "agent_generator":
        run_agent_generator(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
