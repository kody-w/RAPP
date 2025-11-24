"""
RAPP Meta-Agents Package
=========================

This package contains repository-specific agents for development,
maintenance, and management tasks. These agents are NOT deployed
to production and are intended for internal use only.

Available Agents:
- RepositorySteward: Repository health monitoring and maintenance
- AgentGenerator: Scaffolds new agents from templates

Usage:
    from .rapp.agents.repository_steward import RepositorySteward
    from .rapp.agents.agent_generator import AgentGenerator
"""

__all__ = ['RepositorySteward', 'AgentGenerator']
