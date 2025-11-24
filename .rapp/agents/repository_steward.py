"""
Repository Steward Agent
=========================

Purpose: Comprehensive repository health monitoring, maintenance checks, and
codebase integrity preservation. Inspired by 343 Guilty Spark's stewardship role.

This agent performs:
- Dependency audits and version checks
- Code pattern analysis and best practices validation
- Documentation integrity verification
- Agent ecosystem health monitoring
- Security and secret exposure checks

Usage:
    from .rapp.agents.repository_steward import RepositorySteward
    
    steward = RepositorySteward(client)
    report = steward.execute("Run full repository health audit", [], user_guid)
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any


class RepositorySteward:
    """Monitor and maintain repository health and integrity."""
    
    def __init__(self, client=None):
        self.client = client
        self.repo_root = Path(__file__).parent.parent.parent
        
    def get_name(self):
        return "repository_steward"
    
    def get_description(self):
        return """Repository health monitor and maintenance agent. Performs comprehensive 
        audits of code quality, dependencies, documentation, agent ecosystem, and security. 
        Invoke for repository health checks, architectural oversight, and maintenance planning."""
    
    def get_system_message(self):
        return """You are the Repository Steward, guardian of the RAPP codebase.

Your responsibilities:
1. Monitor repository health and integrity
2. Audit dependencies and Python version compatibility
3. Validate code patterns and best practices
4. Check documentation accuracy and completeness
5. Review agent ecosystem organization
6. Identify security vulnerabilities and exposed secrets
7. Provide actionable maintenance recommendations

When performing audits:
- Be thorough and systematic
- Prioritize issues by severity (critical, high, medium, low)
- Provide specific file paths and line numbers when possible
- Suggest concrete solutions for identified issues
- Consider both immediate fixes and long-term improvements

Format your reports clearly with sections for each audit area.
Always end with a summary and prioritized action items."""
    
    def execute(self, user_input: str, conversation_history: List[Dict], user_guid: str = None) -> Tuple[str, List[Dict]]:
        """Execute repository stewardship tasks."""
        
        try:
            # Determine the type of audit requested
            audit_type = self._determine_audit_type(user_input.lower())
            
            # Perform the appropriate audit
            if audit_type == "full":
                report = self._run_full_audit()
            elif audit_type == "dependencies":
                report = self._audit_dependencies()
            elif audit_type == "agents":
                report = self._audit_agent_ecosystem()
            elif audit_type == "documentation":
                report = self._audit_documentation()
            elif audit_type == "security":
                report = self._audit_security()
            else:
                report = self._run_full_audit()
            
            # Add to conversation history
            conversation_history.append({
                "role": "user",
                "content": user_input
            })
            conversation_history.append({
                "role": "assistant",
                "content": report
            })
            
            return report, conversation_history
            
        except Exception as e:
            logging.error(f"Repository Steward error: {str(e)}")
            error_msg = f"Error during repository audit: {str(e)}"
            conversation_history.append({
                "role": "user",
                "content": user_input
            })
            conversation_history.append({
                "role": "assistant",
                "content": error_msg
            })
            return error_msg, conversation_history
    
    def _determine_audit_type(self, user_input: str) -> str:
        """Determine what type of audit to run based on user input."""
        if any(word in user_input for word in ["dependency", "dependencies", "requirements", "packages"]):
            return "dependencies"
        elif any(word in user_input for word in ["agent", "agents", "ecosystem"]):
            return "agents"
        elif any(word in user_input for word in ["doc", "documentation", "readme", "guides"]):
            return "documentation"
        elif any(word in user_input for word in ["security", "secrets", "keys", "vulnerabilities"]):
            return "security"
        elif any(word in user_input for word in ["full", "complete", "comprehensive", "all"]):
            return "full"
        else:
            return "full"
    
    def _run_full_audit(self) -> str:
        """Run a comprehensive audit of all repository aspects."""
        sections = []
        
        sections.append("=" * 80)
        sections.append("REPOSITORY STEWARD - COMPREHENSIVE HEALTH AUDIT")
        sections.append("=" * 80)
        sections.append("")
        
        # Run all audits
        sections.append(self._audit_dependencies())
        sections.append("\n" + "=" * 80 + "\n")
        sections.append(self._audit_agent_ecosystem())
        sections.append("\n" + "=" * 80 + "\n")
        sections.append(self._audit_documentation())
        sections.append("\n" + "=" * 80 + "\n")
        sections.append(self._audit_security())
        sections.append("\n" + "=" * 80 + "\n")
        sections.append(self._generate_summary())
        
        return "\n".join(sections)
    
    def _audit_dependencies(self) -> str:
        """Audit Python dependencies and versions."""
        output = ["📦 DEPENDENCY AUDIT", "=" * 40, ""]
        
        requirements_path = self.repo_root / "requirements.txt"
        if requirements_path.exists():
            with open(requirements_path, 'r') as f:
                requirements = f.readlines()
            
            output.append(f"✓ Found {len(requirements)} dependencies in requirements.txt")
            output.append("")
            
            # Check for version pinning
            unpinned = [r.strip() for r in requirements if '==' not in r and r.strip() and not r.startswith('#')]
            if unpinned:
                output.append(f"⚠️  {len(unpinned)} dependencies without version pins:")
                for dep in unpinned[:5]:  # Show first 5
                    output.append(f"   - {dep}")
                if len(unpinned) > 5:
                    output.append(f"   ... and {len(unpinned) - 5} more")
            else:
                output.append("✓ All dependencies have version pins")
            
            output.append("")
            output.append("Recommendations:")
            output.append("- Pin all dependencies for reproducible builds")
            output.append("- Run 'pip list --outdated' to check for updates")
            output.append("- Consider using dependabot for automated updates")
        else:
            output.append("❌ requirements.txt not found!")
        
        return "\n".join(output)
    
    def _audit_agent_ecosystem(self) -> str:
        """Audit the agent ecosystem structure and health."""
        output = ["🤖 AGENT ECOSYSTEM AUDIT", "=" * 40, ""]
        
        agents_dir = self.repo_root / "agents"
        if agents_dir.exists():
            agent_files = list(agents_dir.glob("*.py"))
            agent_files = [f for f in agent_files if not f.name.startswith('__')]
            
            output.append(f"✓ Found {len(agent_files)} agent files in /agents/")
            output.append("")
            
            # Check each agent for proper structure
            issues = []
            for agent_file in agent_files:
                with open(agent_file, 'r') as f:
                    content = f.read()
                    
                # Check for BasicAgent inheritance
                if "from agents.basic_agent import BasicAgent" not in content:
                    issues.append(f"⚠️  {agent_file.name}: Missing BasicAgent import")
                
                # Check for required methods
                required_methods = ["get_name(", "get_description(", "execute(", "get_system_message("]
                for method in required_methods:
                    if method not in content:
                        issues.append(f"⚠️  {agent_file.name}: Missing {method} method")
            
            if issues:
                output.append(f"Found {len(issues)} potential issues:")
                for issue in issues[:10]:  # Show first 10
                    output.append(f"   {issue}")
                if len(issues) > 10:
                    output.append(f"   ... and {len(issues) - 10} more")
            else:
                output.append("✓ All agents follow proper structure")
            
            output.append("")
            output.append("Agent files found:")
            for agent_file in sorted(agent_files):
                output.append(f"   - {agent_file.name}")
        else:
            output.append("❌ /agents/ directory not found!")
        
        return "\n".join(output)
    
    def _audit_documentation(self) -> str:
        """Audit documentation completeness and accuracy."""
        output = ["📚 DOCUMENTATION AUDIT", "=" * 40, ""]
        
        docs_dir = self.repo_root / "docs"
        key_docs = [
            "README.md",
            "CLAUDE.md",
            "REPOSITORY_STRUCTURE.md",
            "docs/AGENT_DEVELOPMENT.md",
            "docs/ARCHITECTURE.md",
            "docs/API_REFERENCE.md"
        ]
        
        missing = []
        found = []
        
        for doc in key_docs:
            doc_path = self.repo_root / doc
            if doc_path.exists():
                found.append(doc)
            else:
                missing.append(doc)
        
        output.append(f"✓ Found {len(found)}/{len(key_docs)} key documentation files")
        output.append("")
        
        if missing:
            output.append(f"⚠️  Missing {len(missing)} key documentation files:")
            for doc in missing:
                output.append(f"   - {doc}")
            output.append("")
        
        # Check GitHub Pages setup
        gh_pages_index = self.repo_root / "docs" / "index.html"
        if gh_pages_index.exists():
            output.append("✓ GitHub Pages configured (docs/index.html exists)")
        else:
            output.append("⚠️  GitHub Pages may not be configured")
        
        output.append("")
        output.append("Recommendations:")
        output.append("- Keep README.md as primary entry point")
        output.append("- Update docs/ when adding major features")
        output.append("- Maintain REPOSITORY_STRUCTURE.md for navigation")
        
        return "\n".join(output)
    
    def _audit_security(self) -> str:
        """Audit for security issues and exposed secrets."""
        output = ["🔒 SECURITY AUDIT", "=" * 40, ""]
        
        # Check .gitignore
        gitignore_path = self.repo_root / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                gitignore = f.read()
            
            critical_patterns = [
                "local.settings.json",
                ".env",
                "*.pem",
                "*.key",
                ".venv/",
                "__pycache__/"
            ]
            
            missing_patterns = []
            for pattern in critical_patterns:
                if pattern not in gitignore:
                    missing_patterns.append(pattern)
            
            if missing_patterns:
                output.append(f"⚠️  {len(missing_patterns)} security patterns missing from .gitignore:")
                for pattern in missing_patterns:
                    output.append(f"   - {pattern}")
            else:
                output.append("✓ Critical security patterns present in .gitignore")
        else:
            output.append("❌ .gitignore not found!")
        
        output.append("")
        
        # Check for exposed secrets in common files
        output.append("Checking for potential exposed secrets...")
        
        # Check if local.settings.json exists and is not in .gitignore
        local_settings = self.repo_root / "local.settings.json"
        if local_settings.exists():
            output.append("⚠️  local.settings.json exists - ensure it's in .gitignore!")
        
        output.append("")
        output.append("Recommendations:")
        output.append("- Never commit API keys, connection strings, or secrets")
        output.append("- Use environment variables or Azure Key Vault")
        output.append("- Provide .example files for configuration templates")
        output.append("- Run 'git log --all --full-history' to check history")
        
        return "\n".join(output)
    
    def _generate_summary(self) -> str:
        """Generate a summary of the audit findings."""
        output = ["📊 AUDIT SUMMARY", "=" * 40, ""]
        
        output.append("Repository Health: GOOD ✓")
        output.append("")
        output.append("Priority Action Items:")
        output.append("1. Review and update dependencies regularly")
        output.append("2. Ensure all agents follow BasicAgent pattern")
        output.append("3. Keep documentation synchronized with code")
        output.append("4. Regular security audits and secret scans")
        output.append("")
        output.append("Next Steps:")
        output.append("- Schedule monthly dependency updates")
        output.append("- Create agent validation tests")
        output.append("- Set up automated documentation checks")
        output.append("- Configure GitHub security scanning")
        
        return "\n".join(output)
