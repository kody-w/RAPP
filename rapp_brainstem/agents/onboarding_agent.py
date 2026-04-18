"""
OnboardingAgent — guides users through RAPP Brainstem tiers.

Tier 1 (Brainstem): Local Flask server + GitHub Copilot — where you start.
Tier 2 (Spinal Cord): Azure Functions + Azure OpenAI — when you're ready to scale.
Tier 3 (Nervous System): Copilot Studio + M365 — enterprise integration.

When the user is ready for Tier 2 or 3, this agent activates the HatchRapp agent
by copying it from agents/experimental/ into agents/ so brainstem auto-discovers it.
"""

from openrappter.agents.basic_agent import BasicAgent
import os
import shutil


class OnboardingAgent(BasicAgent):
    def __init__(self):
        self.name = "Onboarding"
        self.metadata = {
            "name": self.name,
            "description": (
                "Guides the user through the RAPP platform tiers. "
                "Use when the user asks about getting started, next steps, "
                "upgrading to Azure (Tier 2), Copilot Studio (Tier 3), "
                "or says they are ready to hatch/create/deploy a RAPP."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "overview",
                            "status",
                            "activate_tier2",
                            "activate_tier3",
                        ],
                        "description": (
                            "overview: explain the tiers and what's available. "
                            "status: show what tier capabilities are currently active. "
                            "activate_tier2: user is ready for Azure Functions (Spinal Cord). "
                            "activate_tier3: user is ready for Copilot Studio (Nervous System)."
                        ),
                    }
                },
                "required": ["action"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

        # Resolve paths relative to this file
        self._agents_dir = os.path.dirname(os.path.abspath(__file__))
        self._experimental_dir = os.path.join(self._agents_dir, "experimental")

    def perform(self, **kwargs) -> str:
        action = kwargs.get("action", "overview")

        if action == "overview":
            return self._overview()
        elif action == "status":
            return self._status()
        elif action == "activate_tier2":
            return self._activate_hatch("azure_functions")
        elif action == "activate_tier3":
            return self._activate_hatch("copilot_studio")
        else:
            return f"Unknown action: {action}. Try: overview, status, activate_tier2, activate_tier3"

    def _overview(self) -> str:
        return (
            "RAPP Platform — Three Tiers, One Path\n"
            "\n"
            "Tier 1: Brainstem (you are here)\n"
            "  Local Flask server + GitHub Copilot API.\n"
            "  Write Python agents, test locally, no cloud needed.\n"
            "  Agents live in agents/ and are auto-discovered.\n"
            "\n"
            "Tier 2: Spinal Cord (Azure Functions)\n"
            "  Deploy your agents to Azure as a Function App.\n"
            "  Uses Azure OpenAI, managed identity, persistent storage.\n"
            "  Full CommunityRAPP backend with memory agents.\n"
            "\n"
            "Tier 3: Nervous System (Copilot Studio + M365)\n"
            "  Native Copilot Studio agents, Power Automate flows.\n"
            "  Teams channel, M365 Copilot declarative agents.\n"
            "  Transpile Python agents to MCS format.\n"
            "\n"
            "When you're ready to move to Tier 2 or 3, just say so.\n"
            "I'll activate the HatchRapp agent to scaffold your project."
        )

    def _status(self) -> str:
        hatch_active = os.path.isfile(
            os.path.join(self._agents_dir, "hatch_rapp_agent.py")
        )
        hatch_available = os.path.isfile(
            os.path.join(self._experimental_dir, "hatch_rapp_agent.py")
        )

        lines = [
            "Current capabilities:",
            "",
            "Tier 1 (Brainstem): ACTIVE",
            "  - Agent auto-discovery: ON",
            "  - Local storage shim: ON",
            "  - GitHub Copilot API: ON",
            "",
        ]

        if hatch_active:
            lines.extend([
                "Tier 2/3 (HatchRapp): ACTIVE",
                "  - HatchRapp agent is loaded in agents/",
                "  - You can scaffold Azure Functions or Copilot Studio projects.",
                "  - Try: 'hatch a new rapp called my_project'",
            ])
        elif hatch_available:
            lines.extend([
                "Tier 2/3 (HatchRapp): AVAILABLE (not yet activated)",
                "  - Say 'I'm ready for Tier 2' or 'activate Tier 2' to enable.",
            ])
        else:
            lines.extend([
                "Tier 2/3 (HatchRapp): NOT AVAILABLE",
                "  - hatch_rapp_agent.py not found in agents/experimental/",
            ])

        return "\n".join(lines)

    def _activate_hatch(self, target: str) -> str:
        src = os.path.join(self._experimental_dir, "hatch_rapp_agent.py")
        dst = os.path.join(self._agents_dir, "hatch_rapp_agent.py")

        # Already active?
        if os.path.isfile(dst):
            tier = "Tier 2 (Azure Functions)" if target == "azure_functions" else "Tier 3 (Copilot Studio)"
            return (
                f"HatchRapp agent is already active for {tier}.\n"
                f"You can use it now — try:\n"
                f"  'Hatch a new rapp called my_project'"
            )

        # Source exists?
        if not os.path.isfile(src):
            return (
                "Error: hatch_rapp_agent.py not found in agents/experimental/.\n"
                "This file should have been included with your brainstem installation.\n"
                "Try re-running the installer or check the RAPP repo."
            )

        # Copy from experimental → agents
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            return f"Error activating HatchRapp agent: {e}"

        tier_label = (
            "Tier 2 — Spinal Cord (Azure Functions)"
            if target == "azure_functions"
            else "Tier 3 — Nervous System (Copilot Studio)"
        )

        return (
            f"HatchRapp agent activated for {tier_label}.\n"
            "\n"
            "It will be available on your next message. Here's what to do:\n"
            "\n"
            f"  1. Ask me to 'hatch a new rapp called <name>'\n"
            f"     (I'll scaffold a complete project for you.)\n"
            f"  2. I'll tell you where to open it in VS Code.\n"
            f"  3. Configure your Azure OpenAI credentials.\n"
            f"  4. Test locally with 'func start'.\n"
            f"  5. Deploy when ready.\n"
            "\n"
            "The hatched project is yours — fully self-contained,\n"
            "independent from the brainstem."
        )
