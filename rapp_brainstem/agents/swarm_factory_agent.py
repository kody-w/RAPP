"""
swarm_factory_agent.py — Converge your local agents into a single-file RAPP swarm.

Takes every agent loaded on your local brainstem and collapses them into ONE
sacred agent.py file. The output is a drop-in singleton you can share with
anyone — they copy the file into their brainstem's agents/ dir and it works.

Usage: ask the brainstem "Package my agents as a swarm called SalesBot"
"""

from agents.basic_agent import BasicAgent
import ast
import os
import re
import json
import hashlib
import glob


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/swarm-factory",
    "tier": "core",
    "trust": "official",
    "version": "0.1.0",
    "tags": ["meta", "build", "singleton", "swarm-factory"],
    "example_call": {"args": {"swarm_name": "SalesBot", "description": "B2B sales acceleration pipeline"}},
}


class SwarmFactoryAgent(BasicAgent):
    def __init__(self):
        self.name = "SwarmFactory"
        self.metadata = {
            "name": "SwarmFactory",
            "description": (
                "Converge the agents loaded on this brainstem into a single "
                "shareable .py file. The output is a RAPP swarm singleton — one "
                "file that contains every agent collapsed into _Internal classes "
                "with a single public entrypoint. Anyone can drop this file into "
                "their brainstem's agents/ dir and it works. Call this when the "
                "user wants to package, publish, export, or share their agent swarm."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "swarm_name": {
                        "type": "string",
                        "description": "PascalCase name for the swarm (e.g. SalesBot, ResearchPipeline)"
                    },
                    "description": {
                        "type": "string",
                        "description": "One-line description of what this swarm does"
                    },
                    "exclude": {
                        "type": "string",
                        "description": "Comma-separated agent names to exclude (e.g. 'SaveMemory,RecallMemory'). Built-in memory/factory agents are excluded automatically."
                    }
                },
                "required": ["swarm_name"]
            }
        }
        super().__init__(self.name, self.metadata)

    def perform(self, swarm_name="MySwarm", description="", exclude="", **kwargs):
        agents_dir = os.environ.get("AGENTS_PATH",
                        os.path.join(os.path.dirname(os.path.abspath(__file__))))

        auto_exclude = {"SwarmFactory", "BasicAgent", "SaveMemory", "RecallMemory"}
        user_exclude = set(x.strip() for x in exclude.split(",") if x.strip())
        skip = auto_exclude | user_exclude

        agent_files = sorted(glob.glob(os.path.join(agents_dir, "*_agent.py")))

        sources = {}
        for path in agent_files:
            fname = os.path.basename(path)
            if fname == "basic_agent.py":
                continue
            try:
                src = open(path).read()
                tree = ast.parse(src, filename=fname)
                classes = [n for n in tree.body if isinstance(n, ast.ClassDef)
                           and n.name != "BasicAgent"]
                if not classes:
                    continue
                cls_name = classes[0].name
                if cls_name in skip or cls_name.replace("Agent", "") in skip:
                    continue
                sources[fname] = {
                    "src": src,
                    "tree": tree,
                    "class_name": cls_name,
                    "path": path,
                }
            except Exception:
                continue

        if not sources:
            return json.dumps({"status": "error",
                               "message": "No eligible agents found to converge."})

        slug = re.sub(r'[^a-z0-9]', '', swarm_name.lower())
        public_name = re.sub(r'[^A-Za-z0-9]', '', swarm_name)
        if not public_name:
            public_name = "MySwarm"

        # Detect which agents import other agents (composites vs leaves)
        import_map = {}
        for fname, info in sources.items():
            imports = set()
            for node in info["tree"].body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    s = ast.get_source_segment(info["src"], node) or ""
                    for other_fname, other_info in sources.items():
                        if other_info["class_name"] in s:
                            imports.add(other_info["class_name"])
            import_map[fname] = imports

        leaves = [f for f in sources if not import_map[f]]
        composites = [f for f in sources if import_map[f]]

        # Build rename table
        renames = {}
        for fname, info in sources.items():
            cn = info["class_name"]
            base = cn.replace("Agent", "") if cn.endswith("Agent") else cn
            renames[cn] = f"_Internal{base}"

        # Extract SOUL constants and helper functions from each file
        all_souls = []
        has_llm_helper = False
        llm_helper_src = ""
        post_helper_src = ""

        for fname in leaves + composites:
            info = sources[fname]
            src = info["src"]
            tree = info["tree"]
            stem = os.path.splitext(fname)[0].replace("_agent", "").upper().replace("-", "_")

            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id == "SOUL":
                            seg = ast.get_source_segment(src, node)
                            if seg:
                                renamed = re.sub(r'^SOUL\s*=', f'_SOUL_{stem} =', seg)
                                all_souls.append((stem, renamed))

            if not has_llm_helper:
                m_llm = re.search(
                    r'(def _llm_call\b.*?)(?=\n(?:def |class |__manifest__|\Z))',
                    src, re.DOTALL)
                m_post = re.search(
                    r'(def _post\b.*?)(?=\n(?:def |class |__manifest__|\Z))',
                    src, re.DOTALL)
                if m_llm:
                    llm_helper_src = m_llm.group(1).rstrip()
                    has_llm_helper = True
                if m_post:
                    post_helper_src = m_post.group(1).rstrip()

        # Extract standalone module-level constants (not SOUL, not __manifest__)
        extra_constants = []
        for fname in leaves + composites:
            info = sources[fname]
            for node in info["tree"].body:
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id not in (
                                "SOUL", "__manifest__", "metadata"):
                            seg = ast.get_source_segment(info["src"], node)
                            if seg and len(seg) < 5000:
                                extra_constants.append(seg)
                if isinstance(node, ast.Assert):
                    seg = ast.get_source_segment(info["src"], node)
                    if seg:
                        extra_constants.append(seg)

        # Extract standalone helper functions (not _llm_call, _post)
        extra_helpers = []
        for fname in leaves + composites:
            info = sources[fname]
            for node in info["tree"].body:
                if isinstance(node, ast.FunctionDef) and node.name not in (
                        "_llm_call", "_post", "perform"):
                    seg = ast.get_source_segment(info["src"], node)
                    if seg:
                        extra_helpers.append(seg)

        # Now build the singleton
        out = f'"""\n{slug}_agent.py — {public_name} singleton.\n\n'
        out += f'{description or "A converged RAPP swarm."}\n\n'
        out += 'Drop this file into any RAPP brainstem\'s agents/ directory and it works.\n'
        out += f'Generated by SwarmFactory from {len(sources)} source agents.\n\n'
        out += 'Inlined agents:\n'
        for fname, info in sources.items():
            out += f'  - {info["class_name"]}\n'
        out += '"""\n\n'
        out += 'from agents.basic_agent import BasicAgent\n'
        out += 'import json\nimport os\nimport re\nimport hashlib\n'
        out += 'import urllib.request\nimport urllib.error\n\n\n'

        delegates = [f'@rapp/{info["class_name"].replace("Agent","").lower()}'
                      for info in sources.values()]
        out += f'__manifest__ = {{\n'
        out += f'    "schema": "rapp-agent/1.0",\n'
        out += f'    "name": "@rapp/{slug}-singleton",\n'
        out += f'    "version": "0.1.0",\n'
        out += f'    "tags": ["composite", "singleton", "swarm-factory-generated"],\n'
        out += f'    "delegates_to_inlined": {json.dumps(delegates, indent=8)},\n'
        out += f'    "example_call": {{"args": {{}}}},\n'
        out += f'}}\n\n\n'

        # Constants
        if extra_constants:
            out += '# ─── Constants ─────────────────────────────────────────────────────────\n\n'
            for c in extra_constants:
                out += c + '\n\n'

        # SOULs
        if all_souls:
            out += '# ─── SOUL constants (verbatim from each agent) ─────────────────────────\n\n'
            for stem, soul_src in all_souls:
                out += soul_src + '\n\n'

        # Helper functions
        if extra_helpers:
            out += '# ─── Helper functions ──────────────────────────────────────────────────\n\n'
            for h in extra_helpers:
                out += h + '\n\n'

        # Internal classes — leaves first
        out += '# ─── Internal classes (prefixed _Internal to hide from discovery) ──────\n\n'
        for fname in leaves:
            info = sources[fname]
            cls_src = None
            for node in info["tree"].body:
                if isinstance(node, ast.ClassDef) and node.name == info["class_name"]:
                    cls_src = ast.get_source_segment(info["src"], node)
                    break
            if not cls_src:
                continue
            new = cls_src
            cn = info["class_name"]
            new = re.sub(rf'\bclass {re.escape(cn)}\b', f'class {renames[cn]}', new)
            stem = os.path.splitext(fname)[0].replace("_agent", "").upper().replace("-", "_")
            new = re.sub(r'\bSOUL\b', f'_SOUL_{stem}', new)
            out += new + '\n\n\n'

        # Internal classes — composites
        for fname in composites:
            info = sources[fname]
            cls_src = None
            for node in info["tree"].body:
                if isinstance(node, ast.ClassDef) and node.name == info["class_name"]:
                    cls_src = ast.get_source_segment(info["src"], node)
                    break
            if not cls_src:
                continue
            new = cls_src
            cn = info["class_name"]
            new = re.sub(rf'\bclass {re.escape(cn)}\b', f'class {renames[cn]}', new)
            for old_cn, new_cn in renames.items():
                if old_cn != cn:
                    new = re.sub(rf'\b{re.escape(old_cn)}\b', new_cn, new)
            out += new + '\n\n\n'

        # Public entrypoint — pick the top composite or first agent
        if composites:
            top_fname = composites[-1]
        else:
            top_fname = leaves[-1] if leaves else list(sources.keys())[-1]
        top_info = sources[top_fname]
        top_cls = top_info["class_name"]
        top_internal = renames[top_cls]

        out += '# ─── PUBLIC ENTRYPOINT ──────────────────────────────────────────────────\n\n'
        out += f'class {public_name}({top_internal}):\n'
        out += f'    def __init__(self):\n'
        out += f'        self.name = "{public_name}"\n'
        out += f'        self.metadata = {{\n'
        out += f'            "name": "{public_name}",\n'
        out += f'            "description": "{description or public_name + " swarm"}",\n'
        out += f'            "parameters": {json.dumps(top_info.get("metadata", {}).get("parameters", {"type": "object", "properties": {}, "required": []}))}\n'
        out += f'        }}\n'
        out += f'        super().__init__(self.name, self.metadata)\n\n\n'

        out += f'class {public_name}Agent({public_name}):\n'
        out += f'    pass\n\n\n'

        # LLM helpers
        if llm_helper_src:
            out += '# ─── Inlined LLM dispatch ──────────────────────────────────────────────\n\n'
            out += llm_helper_src + '\n\n\n'
        if post_helper_src:
            out += post_helper_src + '\n'

        # Write output
        output_fname = f"{slug}_agent.py"
        brainstem_dir = os.path.dirname(agents_dir)
        output_path = os.path.join(brainstem_dir, output_fname)
        with open(output_path, 'w') as f:
            f.write(out)

        n_lines = len(out.split('\n'))
        sha = hashlib.sha256(out.encode()).hexdigest()

        return json.dumps({
            "status": "ok",
            "swarm_name": public_name,
            "output_file": output_path,
            "filename": output_fname,
            "lines": n_lines,
            "bytes": len(out),
            "sha256": sha,
            "agents_collapsed": len(sources),
            "leaves": len(leaves),
            "composites": len(composites),
            "souls_inlined": len(all_souls),
            "message": (
                f"Converged {len(sources)} agents into {output_fname} "
                f"({n_lines} lines). The file is at {output_path} — "
                f"share it with anyone. They drop it in their brainstem's "
                f"agents/ dir and it works."
            ),
        })
