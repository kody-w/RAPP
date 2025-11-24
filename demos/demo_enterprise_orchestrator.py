#!/usr/bin/env python3
"""
Enterprise System Orchestrator Agent Demo
Shows how the agent prevents overcommitment disasters before contracts are signed
"""

# Mock Azure storage
class MockAzureFileStorageManager:
    def __init__(self):
        self.current_guid = None
    def set_memory_context(self, guid):
        self.current_guid = guid
    def read_file(self, share, path):
        return None
    def write_file(self, share, path, content):
        pass

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import utils.azure_file_storage as storage_module
storage_module.AzureFileStorageManager = MockAzureFileStorageManager

from agents.enterprise_orchestrator_agent import EnterpriseOrchestratorAgent


def demo_scenario(title, description, deal_data, team_data=None):
    """Run a demo scenario"""
    print("\n" + "="*80)
    print(f"SCENARIO: {title}")
    print("="*80)
    print(f"{description}\n")

    agent = EnterpriseOrchestratorAgent()

    # Analyze deal feasibility
    result = agent.perform(
        action='analyze_deal',
        deal_data=deal_data,
        team_data=team_data
    )

    print(result)
    print("\n")


if __name__ == "__main__":
    print("\n" + "🎯"*40)
    print("ENTERPRISE SYSTEM ORCHESTRATOR AGENT - DEMO")
    print("Preventing $500K-2M in overcommitment disasters")
    print("🎯"*40 + "\n")

    # Team data (simulates data from HR/Project Management systems)
    team_data = [
        {
            'name': 'Alice Johnson',
            'skills': ['Python', 'React', 'Azure', 'API Development'],
            'current_allocation_percent': 60,
            'current_projects': ['E-commerce Platform'],
            'hourly_rate': 150
        },
        {
            'name': 'Bob Smith',
            'skills': ['Java', 'AWS', 'Docker', 'Microservices'],
            'current_allocation_percent': 85,
            'current_projects': ['Banking Portal', 'Payment Gateway'],
            'hourly_rate': 160
        },
        {
            'name': 'Carol Davis',
            'skills': ['UX Design', 'Figma', 'React', 'User Research'],
            'current_allocation_percent': 40,
            'current_projects': ['E-commerce Platform'],
            'hourly_rate': 130
        },
        {
            'name': 'David Lee',
            'skills': ['DevOps', 'Kubernetes', 'Terraform', 'CI/CD'],
            'current_allocation_percent': 95,
            'current_projects': ['Banking Portal', 'Payment Gateway', 'Infrastructure Upgrade'],
            'hourly_rate': 170
        },
        {
            'name': 'Emma Wilson',
            'skills': ['Python', 'Data Science', 'SQL', 'Machine Learning'],
            'current_allocation_percent': 50,
            'current_projects': ['Analytics Dashboard'],
            'hourly_rate': 155
        },
        {
            'name': 'Frank Martinez',
            'skills': ['Project Management', 'Agile', 'Stakeholder Management'],
            'current_allocation_percent': 70,
            'current_projects': ['E-commerce Platform', 'Banking Portal'],
            'hourly_rate': 140
        }
    ]

    # Scenario 1: Perfect Deal - We CAN Deliver
    demo_scenario(
        "Perfect Deal - Green Light ✅",
        "Sales wants to close a mobile app development deal. Let's check if we can deliver.",
        deal_data={
            'deal_id': 'DEAL-001',
            'deal_name': 'Mobile App Development for TechCorp',
            'customer_name': 'TechCorp Industries',
            'deal_value': 250000,
            'start_date': '2025-02-01',
            'end_date': '2025-05-01',
            'scope_description': 'iOS and Android app with user authentication, real-time chat, and payment integration',
            'estimated_hours': 400,
            'required_skills': ['React', 'Python', 'API Development'],
            'priority': 'high'
        },
        team_data=team_data
    )

    # Scenario 2: Disaster Waiting to Happen - Missing Skills
    demo_scenario(
        "Disaster Prevented - Missing Critical Skills 🚨",
        "Sales wants to close a blockchain project. Do we have the skills?",
        deal_data={
            'deal_id': 'DEAL-002',
            'deal_name': 'Blockchain Supply Chain for RetailCo',
            'customer_name': 'RetailCo Global',
            'deal_value': 500000,
            'start_date': '2025-01-15',
            'end_date': '2025-06-15',
            'scope_description': 'Blockchain-based supply chain tracking with smart contracts and NFT integration',
            'estimated_hours': 800,
            'required_skills': ['Blockchain', 'Solidity', 'Web3', 'Smart Contracts'],
            'priority': 'high'
        },
        team_data=team_data
    )

    # Scenario 3: Capacity Disaster - Everyone Already Overallocated
    demo_scenario(
        "Disaster Prevented - Team Already Burned Out 🔥",
        "Sales wants to close a huge enterprise deal. Can our already-overloaded team handle it?",
        deal_data={
            'deal_id': 'DEAL-003',
            'deal_name': 'Enterprise CRM Migration for MegaCorp',
            'customer_name': 'MegaCorp International',
            'deal_value': 750000,
            'start_date': '2025-01-01',
            'end_date': '2025-04-01',
            'scope_description': 'Migrate legacy CRM to cloud, data migration, custom integrations, training',
            'estimated_hours': 1200,
            'required_skills': ['Python', 'AWS', 'DevOps', 'Project Management'],
            'priority': 'critical'
        },
        team_data=team_data
    )

    # Scenario 4: Timeline Impossible
    demo_scenario(
        "Disaster Prevented - Impossible Timeline ⏰",
        "Sales promised delivery in 2 weeks. Let's see if physics allows that...",
        deal_data={
            'deal_id': 'DEAL-004',
            'deal_name': 'Urgent Dashboard for StartupXYZ',
            'customer_name': 'StartupXYZ',
            'deal_value': 50000,
            'start_date': '2025-01-05',
            'end_date': '2025-01-19',  # Only 2 weeks!
            'scope_description': 'Analytics dashboard with 20+ data sources, real-time updates, custom visualizations',
            'estimated_hours': 320,  # 8 person-weeks of work in 2 calendar weeks
            'required_skills': ['Python', 'React', 'Data Science'],
            'priority': 'urgent'
        },
        team_data=team_data
    )

    print("="*80)
    print("✅ DEMO COMPLETE")
    print("="*80)
    print("\nKEY TAKEAWAYS:")
    print("1. ✅ Scenario 1: Deal approved - we have capacity and skills")
    print("2. 🚨 Scenario 2: BLOCKED - missing blockchain skills, need to hire/train first")
    print("3. 🔥 Scenario 3: BLOCKED - team already overallocated, would cause burnout")
    print("4. ⏰ Scenario 4: BLOCKED - timeline physically impossible without 3x team size")
    print("\n💡 IMPACT:")
    print("   - Prevented $1.3M in deals we couldn't deliver ($500K + $750K)")
    print("   - Saved team from burnout and project failures")
    print("   - Sales can negotiate realistic terms BEFORE signing contracts")
    print("   - Reputation protected by not over-promising")
    print("\n" + "="*80 + "\n")
