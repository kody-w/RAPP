#!/usr/bin/env python3
"""Tests for hatch_rapp_agent.py — scaffolding, status, deploy, and template validation."""

import os
import sys
import json
import shutil
import tempfile
import unittest

# Ensure brainstem dir is importable
BRAINSTEM_DIR = os.path.dirname(os.path.abspath(__file__))
if BRAINSTEM_DIR not in sys.path:
    sys.path.insert(0, BRAINSTEM_DIR)

AGENT_PATH = os.path.join(BRAINSTEM_DIR, "agents", "experimental", "hatch_rapp_agent.py")
ONBOARDING_PATH = os.path.join(BRAINSTEM_DIR, "agents", "onboarding_agent.py")


def _load_agent():
    """Load HatchRappAgent via brainstem's loader."""
    import brainstem
    brainstem._shims_registered = False
    agents = brainstem._load_agent_from_file(AGENT_PATH)
    return agents.get("HatchRapp")


class TestAgentLoading(unittest.TestCase):
    """Verify brainstem can auto-discover the agent."""

    def test_agent_loads(self):
        agent = _load_agent()
        self.assertIsNotNone(agent, "HatchRapp agent should load via brainstem")
        self.assertEqual(agent.name, "HatchRapp")

    def test_agent_has_correct_metadata(self):
        agent = _load_agent()
        params = agent.metadata["parameters"]["properties"]
        self.assertIn("action", params)
        self.assertIn("project_name", params)
        self.assertIn("target", params)
        actions = params["action"]["enum"]
        self.assertEqual(
            set(actions),
            {"scaffold", "test_local", "deploy", "status", "open_in_vscode"},
        )
        targets = params["target"]["enum"]
        self.assertEqual(set(targets), {"azure_functions", "copilot_studio"})

    def test_to_tool(self):
        agent = _load_agent()
        tool = agent.to_tool()
        self.assertEqual(tool["type"], "function")
        self.assertEqual(tool["function"]["name"], "HatchRapp")


class TestScaffoldAzureFunctions(unittest.TestCase):
    """Test scaffold action with azure_functions target."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.agent = _load_agent()
        # Monkey-patch output dir to temp
        self._orig = self.agent._output_dir
        self.agent._output_dir = lambda name: os.path.join(self._tmp, name)

    def tearDown(self):
        self.agent._output_dir = self._orig
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_scaffold_creates_structure(self):
        result = self.agent.perform(
            action="scaffold", project_name="test_rapp", target="azure_functions"
        )
        self.assertIn("scaffolded successfully", result)
        project = os.path.join(self._tmp, "test_rapp")
        self.assertTrue(os.path.exists(project))
        # Core files
        for f in [
            "function_app.py",
            "host.json",
            "requirements.txt",
            ".funcignore",
            "local.settings.template.json",
        ]:
            self.assertTrue(
                os.path.exists(os.path.join(project, f)), f"{f} should exist"
            )
        # Agent files
        for f in [
            "agents/__init__.py",
            "agents/basic_agent.py",
            "agents/context_memory_agent.py",
            "agents/manage_memory_agent.py",
        ]:
            self.assertTrue(
                os.path.exists(os.path.join(project, f)), f"{f} should exist"
            )
        # Utils files
        for f in [
            "utils/__init__.py",
            "utils/result.py",
            "utils/storage_factory.py",
            "utils/local_file_storage.py",
            "utils/environment.py",
        ]:
            self.assertTrue(
                os.path.exists(os.path.join(project, f)), f"{f} should exist"
            )

    def test_scaffold_no_copilot_files_for_azure_target(self):
        self.agent.perform(
            action="scaffold", project_name="test_rapp", target="azure_functions"
        )
        project = os.path.join(self._tmp, "test_rapp")
        self.assertFalse(
            os.path.exists(
                os.path.join(project, "agents", "copilot_studio_transpiler_agent.py")
            )
        )
        self.assertFalse(
            os.path.exists(os.path.join(project, "utils", "mcs_generator.py"))
        )

    def test_scaffold_refuses_overwrite(self):
        self.agent.perform(
            action="scaffold", project_name="test_rapp", target="azure_functions"
        )
        result = self.agent.perform(
            action="scaffold", project_name="test_rapp", target="azure_functions"
        )
        self.assertIn("already exists", result)


class TestScaffoldCopilotStudio(unittest.TestCase):
    """Test scaffold action with copilot_studio target."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.agent = _load_agent()
        self._orig = self.agent._output_dir
        self.agent._output_dir = lambda name: os.path.join(self._tmp, name)

    def tearDown(self):
        self.agent._output_dir = self._orig
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_scaffold_includes_copilot_files(self):
        result = self.agent.perform(
            action="scaffold", project_name="cs_rapp", target="copilot_studio"
        )
        self.assertIn("Copilot Studio", result)
        project = os.path.join(self._tmp, "cs_rapp")
        self.assertTrue(
            os.path.exists(
                os.path.join(project, "agents", "copilot_studio_transpiler_agent.py")
            )
        )
        self.assertTrue(
            os.path.exists(os.path.join(project, "utils", "mcs_generator.py"))
        )

    def test_scaffold_copilot_also_has_base_files(self):
        self.agent.perform(
            action="scaffold", project_name="cs_rapp", target="copilot_studio"
        )
        project = os.path.join(self._tmp, "cs_rapp")
        for f in ["function_app.py", "agents/basic_agent.py", "utils/result.py"]:
            self.assertTrue(
                os.path.exists(os.path.join(project, f)),
                f"{f} should exist in copilot_studio scaffold too",
            )


class TestTemplateValidity(unittest.TestCase):
    """Verify all scaffolded Python files are valid syntax."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.agent = _load_agent()
        self._orig = self.agent._output_dir
        self.agent._output_dir = lambda name: os.path.join(self._tmp, name)
        # Scaffold a copilot_studio project (superset of files)
        self.agent.perform(
            action="scaffold", project_name="valid_py", target="copilot_studio"
        )
        self.project = os.path.join(self._tmp, "valid_py")

    def tearDown(self):
        self.agent._output_dir = self._orig
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_function_app_compiles(self):
        import py_compile

        py_compile.compile(
            os.path.join(self.project, "function_app.py"), doraise=True
        )

    def test_basic_agent_compiles(self):
        import py_compile

        py_compile.compile(
            os.path.join(self.project, "agents", "basic_agent.py"), doraise=True
        )

    def test_context_memory_agent_compiles(self):
        import py_compile

        py_compile.compile(
            os.path.join(self.project, "agents", "context_memory_agent.py"),
            doraise=True,
        )

    def test_manage_memory_agent_compiles(self):
        import py_compile

        py_compile.compile(
            os.path.join(self.project, "agents", "manage_memory_agent.py"),
            doraise=True,
        )

    def test_copilot_transpiler_compiles(self):
        import py_compile

        py_compile.compile(
            os.path.join(
                self.project, "agents", "copilot_studio_transpiler_agent.py"
            ),
            doraise=True,
        )

    def test_result_compiles(self):
        import py_compile

        py_compile.compile(
            os.path.join(self.project, "utils", "result.py"), doraise=True
        )

    def test_storage_factory_compiles(self):
        import py_compile

        py_compile.compile(
            os.path.join(self.project, "utils", "storage_factory.py"), doraise=True
        )

    def test_local_file_storage_compiles(self):
        import py_compile

        py_compile.compile(
            os.path.join(self.project, "utils", "local_file_storage.py"),
            doraise=True,
        )

    def test_environment_compiles(self):
        import py_compile

        py_compile.compile(
            os.path.join(self.project, "utils", "environment.py"), doraise=True
        )

    def test_mcs_generator_compiles(self):
        import py_compile

        py_compile.compile(
            os.path.join(self.project, "utils", "mcs_generator.py"), doraise=True
        )

    def test_host_json_valid(self):
        with open(os.path.join(self.project, "host.json")) as f:
            data = json.load(f)
        self.assertEqual(data["version"], "2.0")

    def test_local_settings_template_valid(self):
        with open(os.path.join(self.project, "local.settings.template.json")) as f:
            data = json.load(f)
        self.assertIn("Values", data)
        self.assertIn("FUNCTIONS_WORKER_RUNTIME", data["Values"])


class TestStatus(unittest.TestCase):
    """Test status action."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.agent = _load_agent()
        self._orig = self.agent._output_dir
        self.agent._output_dir = lambda name: os.path.join(self._tmp, name)

    def tearDown(self):
        self.agent._output_dir = self._orig
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_status_missing_project(self):
        result = self.agent.perform(action="status", project_name="nope")
        self.assertIn("does not exist", result)

    def test_status_existing_project(self):
        self.agent.perform(
            action="scaffold", project_name="stat_test", target="azure_functions"
        )
        result = self.agent.perform(action="status", project_name="stat_test")
        self.assertIn("function_app.py", result)
        self.assertIn("MISSING", result)  # no local.settings.json yet


class TestOpenInVscode(unittest.TestCase):
    """Test open_in_vscode action."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.agent = _load_agent()
        self._orig = self.agent._output_dir
        self.agent._output_dir = lambda name: os.path.join(self._tmp, name)

    def tearDown(self):
        self.agent._output_dir = self._orig
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_open_missing(self):
        result = self.agent.perform(action="open_in_vscode", project_name="nope")
        self.assertIn("does not exist", result)

    def test_open_existing(self):
        self.agent.perform(
            action="scaffold", project_name="vsc_test", target="azure_functions"
        )
        result = self.agent.perform(action="open_in_vscode", project_name="vsc_test")
        self.assertIn("code", result)
        self.assertIn("vsc_test", result)


class TestDeploy(unittest.TestCase):
    """Test deploy action."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.agent = _load_agent()
        self._orig = self.agent._output_dir
        self.agent._output_dir = lambda name: os.path.join(self._tmp, name)

    def tearDown(self):
        self.agent._output_dir = self._orig
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_deploy_missing_project(self):
        result = self.agent.perform(
            action="deploy", project_name="nope", target="azure_functions"
        )
        self.assertIn("not found", result.lower())

    def test_deploy_azure_guide(self):
        self.agent.perform(
            action="scaffold", project_name="dep_test", target="azure_functions"
        )
        result = self.agent.perform(
            action="deploy", project_name="dep_test", target="azure_functions"
        )
        self.assertIn("az login", result)
        self.assertIn("func azure functionapp publish", result)

    def test_deploy_copilot_guide(self):
        self.agent.perform(
            action="scaffold", project_name="cs_dep", target="copilot_studio"
        )
        result = self.agent.perform(
            action="deploy", project_name="cs_dep", target="copilot_studio"
        )
        self.assertIn("Copilot Studio", result)


class TestProjectNameSanitization(unittest.TestCase):
    """Test that special characters in project names are sanitized."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.agent = _load_agent()
        self._orig = self.agent._output_dir
        self.agent._output_dir = lambda name: os.path.join(self._tmp, name)

    def tearDown(self):
        self.agent._output_dir = self._orig
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_special_chars_sanitized(self):
        result = self.agent.perform(
            action="scaffold", project_name="my rapp!@#", target="azure_functions"
        )
        self.assertIn("scaffolded successfully", result)
        # The sanitized name should not contain spaces or special chars
        self.assertFalse(os.path.exists(os.path.join(self._tmp, "my rapp!@#")))
        # Should exist with sanitized name
        sanitized = os.path.join(self._tmp, "my_rapp___")
        self.assertTrue(os.path.exists(sanitized))


class TestNoPII(unittest.TestCase):
    """Verify no PII leaked into scaffolded files."""

    PII_PATTERNS = [
        "billwhalen",
        "kody-w",
        "otis",
        "vermeer",
        "carrier",
        "zurnelkay",
        "org6feab",
        "daa9e2eb",
        "8562b2aa",
        "Emma Thompson",
        "Marco Rossi",
        "David Chen",
        "Marriott",
        "Canary Wharf",
        "+44 20",
        "+1 310",
    ]

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.agent = _load_agent()
        self._orig = self.agent._output_dir
        self.agent._output_dir = lambda name: os.path.join(self._tmp, name)
        self.agent.perform(
            action="scaffold", project_name="pii_test", target="copilot_studio"
        )
        self.project = os.path.join(self._tmp, "pii_test")

    def tearDown(self):
        self.agent._output_dir = self._orig
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_no_pii_in_scaffolded_files(self):
        for root, dirs, files in os.walk(self.project):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read().lower()
                except UnicodeDecodeError:
                    continue
                rel = os.path.relpath(fpath, self.project)
                for pattern in self.PII_PATTERNS:
                    self.assertNotIn(
                        pattern.lower(),
                        content,
                        f"PII pattern '{pattern}' found in {rel}",
                    )


class TestUnknownAction(unittest.TestCase):
    """Test that unknown actions return a helpful error."""

    def test_unknown_action(self):
        agent = _load_agent()
        result = agent.perform(action="bogus")
        self.assertIn("Unknown action", result)


# =====================================================================
# Onboarding Agent Tests
# =====================================================================


def _load_onboarding():
    import brainstem
    brainstem._shims_registered = False
    agents = brainstem._load_agent_from_file(ONBOARDING_PATH)
    return agents.get("Onboarding")


class TestOnboardingLoads(unittest.TestCase):
    """Verify onboarding agent auto-discovers."""

    def test_loads(self):
        agent = _load_onboarding()
        self.assertIsNotNone(agent)
        self.assertEqual(agent.name, "Onboarding")

    def test_metadata_actions(self):
        agent = _load_onboarding()
        actions = agent.metadata["parameters"]["properties"]["action"]["enum"]
        self.assertEqual(
            set(actions),
            {"overview", "status", "activate_tier2", "activate_tier3"},
        )


class TestOnboardingOverview(unittest.TestCase):
    def test_overview_mentions_tiers(self):
        agent = _load_onboarding()
        result = agent.perform(action="overview")
        self.assertIn("Tier 1", result)
        self.assertIn("Tier 2", result)
        self.assertIn("Tier 3", result)


class TestOnboardingActivation(unittest.TestCase):
    """Test that activation copies hatch_rapp_agent from experimental/ to agents/."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        # Create mock experimental/ with a hatch_rapp_agent.py
        self._exp = os.path.join(self._tmp, "experimental")
        os.makedirs(self._exp)
        with open(os.path.join(self._exp, "hatch_rapp_agent.py"), "w") as f:
            f.write("# mock hatch agent\n")

        self.agent = _load_onboarding()
        # Patch paths to use temp dirs
        self.agent._agents_dir = self._tmp
        self.agent._experimental_dir = self._exp

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_activate_tier2_copies_file(self):
        result = self.agent.perform(action="activate_tier2")
        self.assertIn("activated", result)
        self.assertTrue(
            os.path.isfile(os.path.join(self._tmp, "hatch_rapp_agent.py"))
        )

    def test_activate_tier3_copies_file(self):
        result = self.agent.perform(action="activate_tier3")
        self.assertIn("activated", result)
        self.assertIn("Copilot Studio", result)

    def test_activate_idempotent(self):
        self.agent.perform(action="activate_tier2")
        result = self.agent.perform(action="activate_tier2")
        self.assertIn("already active", result)

    def test_status_before_activation(self):
        result = self.agent.perform(action="status")
        self.assertIn("Tier 1", result)
        self.assertIn("AVAILABLE", result)

    def test_status_after_activation(self):
        self.agent.perform(action="activate_tier2")
        result = self.agent.perform(action="status")
        self.assertIn("ACTIVE", result)

    def test_activate_missing_source(self):
        os.remove(os.path.join(self._exp, "hatch_rapp_agent.py"))
        result = self.agent.perform(action="activate_tier2")
        self.assertIn("not found", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
