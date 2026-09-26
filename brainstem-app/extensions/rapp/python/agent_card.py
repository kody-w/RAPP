"""What an agent file's card shows, read statically: the agent is never imported and never run.

The Brainstem app's agent card runs this with the Brainstem's own Python, passes an agent's source on
stdin, and gets one JSON object back. It reads agents the way RAR's build_registry.py does: ast.parse,
then compile() as the stricter gate (it only makes a code object; nothing runs), then ast.literal_eval
for literals. A value that only exists once the agent runs comes out as {"$runtime": true}, which the
card shows as "(set when it runs)".

Standard library only, Python 3.9 or newer. Run it as: python -I -S -B agent_card.py [--local NAME]...
Each --local NAME is a module the Brainstem's own folders provide, so it is not a package to install.
"""
import ast
import json
import re
import sys
import warnings

SCHEMA = "rapp-agent-card/1"
MAX_SOURCE = 1024 * 1024  # bytes; a bigger file gets no card
MAX_DEPTH = 24  # how deeply nested a value the card shows may be
MAX_ITEMS = 200  # items of one list or dict
MAX_TEXT = 4000  # characters of one string
MAX_NAMES = 60  # settings and packages
MAX_VIA = 12  # the names behind one capability hint
MAX_DOMAINS = 20
MAX_EXAMPLES = 6
RUNTIME = {"$runtime": True}
DEEP = {"$deep": True}

# Modules the Brainstem provides itself: rapp_brainstem/brainstem.py _register_shims() maps agents,
# openrappter and utils to its own files, and puts its folder and agents/ on sys.path.
SHIMS = {"agents", "basic_agent", "openrappter", "utils", "local_storage"}
# Import names whose package installs under another name (brainstem.py _PIP_MAP, used by _auto_install).
PIP_MAP = {
    "bs4": "beautifulsoup4", "PIL": "Pillow", "cv2": "opencv-python", "sklearn": "scikit-learn",
    "yaml": "pyyaml", "docx": "python-docx", "pptx": "python-pptx", "dotenv": "python-dotenv",
}
# What the code mentions, as a hint: modules that reach the internet, calls that touch files or run programs.
NETWORK = (
    "urllib.request", "urllib3", "requests", "httpx", "aiohttp", "http.client", "socket", "websocket",
    "websockets", "ftplib", "smtplib", "imaplib", "poplib", "xmlrpc.client", "grpc", "paramiko",
    "pyodide.http", "openai", "azure", "boto3", "botocore", "msal", "google.cloud", "googleapiclient",
)
FILE_CALLS = {
    "open", "io.open", "os.open", "os.fdopen", "codecs.open", "sqlite3.connect", "glob.glob", "glob.iglob",
    "os.remove", "os.unlink", "os.rename", "os.renames", "os.replace", "os.makedirs", "os.mkdir", "os.rmdir",
    "os.removedirs", "os.listdir", "os.scandir", "os.walk", "os.chmod", "os.truncate", "os.link", "os.symlink",
}
FILE_PREFIXES = ("shutil.", "tempfile.")
FILE_METHODS = {"read_text", "write_text", "read_bytes", "write_bytes", "iterdir", "rglob", "touch", "unlink", "rmdir", "mkdir"}
# Hosts in URLs that name an XML or JSON vocabulary rather than a place an agent talks to.
NAMESPACE_HOSTS = {"www.w3.org", "w3.org", "schemas.openxmlformats.org", "purl.org", "schemas.xmlsoap.org", "json-schema.org"}
STORAGE = ("utils.azure_file_storage", "utils.dynamics_storage", "utils.storage_factory", "local_storage")
PROGRAM_CALLS = {
    "os.system", "os.popen", "os.startfile", "os.posix_spawn", "os.posix_spawnp", "pty.spawn",
    "asyncio.create_subprocess_exec", "asyncio.create_subprocess_shell",
}
PROGRAM_PREFIXES = ("subprocess.", "os.exec", "os.spawn")
IMPORT_ERRORS = {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")
URL = re.compile(r"(?i)\b(?:https?|wss?)://([^\s/?#'\"<>\\]+)")
HOST = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
# A docstring heading that plainly introduces example prompts, followed by bulleted or numbered lines.
EXAMPLES_HEADING = re.compile(
    r"(?:(?:example|sample)\s+(?:prompts?|questions?|requests?)|try\s+(?:asking|saying)(?:\s+(?:it|me))?"
    r"|things\s+(?:to|you\s+can)\s+ask(?:\s+(?:it|me))?|you\s+can\s+ask(?:\s+(?:it|me))?)\s*:?\Z",
    re.IGNORECASE,
)
EXAMPLE_ITEM = re.compile(r"\s*(?:[-*\u2022]|\d{1,2}[.)])\s+(.+?)\s*\Z")


def clip(text):
    return text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1] + "\u2026"


def is_marker(value):
    return value is RUNTIME or value is DEEP


def shown(value, depth=0):
    """A resolved value as JSON the card can show: capped in size and depth, markers kept."""
    if is_marker(value):
        return value
    if depth > MAX_DEPTH:
        return DEEP
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value if abs(value) < 2 ** 53 else str(value)
    if isinstance(value, float):
        return value if value == value and abs(value) != float("inf") else str(value)
    if isinstance(value, str):
        return clip(value)
    if isinstance(value, dict):
        return {clip(str(key)): shown(item, depth + 1) for key, item in list(value.items())[:MAX_ITEMS]}
    if isinstance(value, (list, tuple)):
        return [shown(item, depth + 1) for item in list(value)[:MAX_ITEMS]]
    if isinstance(value, (set, frozenset)):
        return [shown(item, depth + 1) for item in sorted(value, key=repr)[:MAX_ITEMS]]
    return RUNTIME


def pick(container, key):
    if is_marker(container) or is_marker(key):
        return RUNTIME
    if isinstance(container, dict) and isinstance(key, (str, int, float, bool)):
        return container.get(key, RUNTIME)
    if isinstance(container, list) and isinstance(key, int) and not isinstance(key, bool) and -len(container) <= key < len(container):
        return container[key]
    return RUNTIME


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class Values:
    """Resolves the expressions an agent uses for its name, metadata and manifest, without running them."""

    def __init__(self, module_nodes):
        self.nodes = module_nodes  # module-level names bound exactly once, to their value's node
        self.cache = {}
        self.busy = set()

    def module(self, name, depth):
        if name in self.cache:
            return self.cache[name]
        node = self.nodes.get(name)
        if node is None or name in self.busy:
            return RUNTIME
        self.busy.add(name)
        try:
            value = self.literal(node, {}, depth + 1)
        finally:
            self.busy.discard(name)
        self.cache[name] = value
        return value

    def literal(self, node, scope, depth=0):
        """ast.literal_eval for a literal; otherwise the same value with its non-literal parts marked."""
        try:
            return ast.literal_eval(node)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            return self.of(node, scope, depth)

    def of(self, node, scope, depth=0):
        if depth > MAX_DEPTH:
            return DEEP
        deeper = depth + 1
        if isinstance(node, ast.Constant):
            value = node.value
            return RUNTIME if isinstance(value, (bytes, complex)) or value is Ellipsis else value
        if isinstance(node, ast.Dict):
            out = {}
            for key, item in zip(node.keys, node.values):
                if key is None:  # {**other}
                    other = self.of(item, scope, deeper)
                    if is_marker(other) or not isinstance(other, dict):
                        return RUNTIME
                    out.update(other)
                    continue
                resolved = self.of(key, scope, deeper)
                if is_marker(resolved) or not (resolved is None or isinstance(resolved, (str, int, float, bool))):
                    return RUNTIME
                out[resolved] = self.of(item, scope, deeper)
                if len(out) >= MAX_ITEMS:
                    break
            return out
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            out = []
            for item in node.elts[:MAX_ITEMS]:
                if isinstance(item, ast.Starred):
                    other = self.of(item.value, scope, deeper)
                    if is_marker(other) or not isinstance(other, list):
                        return RUNTIME
                    out.extend(other)
                else:
                    out.append(self.of(item, scope, deeper))
            return out[:MAX_ITEMS]
        if isinstance(node, ast.Name):
            return scope[node.id] if node.id in scope else self.module(node.id, depth)
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                return scope.get("self." + node.attr, RUNTIME)
            return RUNTIME
        if isinstance(node, ast.Subscript):
            return pick(self.of(node.value, scope, deeper), self.of(node.slice, scope, deeper))
        if isinstance(node, ast.JoinedStr):
            parts = []
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    parts.append(part.value)
                    continue
                if isinstance(part, ast.FormattedValue) and part.conversion == -1 and part.format_spec is None:
                    value = self.of(part.value, scope, deeper)
                    if isinstance(value, str) or number(value):
                        parts.append(str(value))
                        continue
                return RUNTIME
            return clip("".join(parts))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = self.of(node.left, scope, deeper), self.of(node.right, scope, deeper)
            if isinstance(left, str) and isinstance(right, str):
                return clip(left + right)
            if isinstance(left, list) and isinstance(right, list):
                return (left + right)[:MAX_ITEMS]
            return left + right if number(left) and number(right) else RUNTIME
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = self.of(node.operand, scope, deeper)
            if number(value):
                return -value if isinstance(node.op, ast.USub) else value
            return RUNTIME
        if isinstance(node, ast.Call):
            return self.call(node, scope, deeper)
        return RUNTIME

    def call(self, node, scope, deeper):
        func = node.func
        if isinstance(func, ast.Name) and func.id == "dict" and not node.args:
            if any(k.arg is None for k in node.keywords):
                return RUNTIME
            return {k.arg: self.of(k.value, scope, deeper) for k in node.keywords[:MAX_ITEMS]}
        if isinstance(func, ast.Name) and func.id in ("list", "tuple") and len(node.args) == 1 and not node.keywords:
            value = self.of(node.args[0], scope, deeper)
            return value if isinstance(value, list) else RUNTIME
        if isinstance(func, ast.Attribute) and func.attr == "get" and 1 <= len(node.args) <= 2 and not node.keywords:
            container = self.of(func.value, scope, deeper)
            key = self.of(node.args[0], scope, deeper)
            if isinstance(container, dict) and not is_marker(container) and isinstance(key, (str, int)):
                if key in container:
                    return container[key]
                return self.of(node.args[1], scope, deeper) if len(node.args) == 2 else None
        return RUNTIME


def assignments(stmt):
    if isinstance(stmt, ast.Assign):
        return [(target, stmt.value) for target in stmt.targets]
    if isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
        return [(stmt.target, stmt.value)]
    return []


def module_nodes(tree):
    """Module-level names bound exactly once by a plain assignment: the constants an agent may refer to."""
    counts, nodes = {}, {}
    for stmt in tree.body:
        targets = [stmt.target] if isinstance(stmt, ast.AugAssign) else [t for t, _ in assignments(stmt)]
        for target in targets:
            if isinstance(target, ast.Name):
                counts[target.id] = counts.get(target.id, 0) + 1
        for target, value in assignments(stmt):
            if isinstance(target, ast.Name):
                nodes[target.id] = value
    return {name: node for name, node in nodes.items() if counts.get(name) == 1}


def in_order(body):
    """The statements a function body runs, in source order, through if/for/while/with/try, not into nested defs."""
    stack = list(reversed(body))
    while stack:
        stmt = stack.pop()
        yield stmt
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        children = []
        for field in ("body", "handlers", "orelse", "finalbody"):
            children.extend(getattr(stmt, field, None) or [])
        for case in getattr(stmt, "cases", None) or []:
            children.extend(case.body)
        stack.extend(reversed(children))


# Bases that are Python's own. A class built only on these and on classes in this file is not built on
# something from another file.
OWN_BASES = {
    "object", "Exception", "BaseException", "dict", "list", "tuple", "set", "str", "int", "float", "type",
    "Enum", "IntEnum", "Flag", "IntFlag", "NamedTuple", "TypedDict", "Protocol", "ABC", "Generic",
}


def defines_perform(cls):
    return any(isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == "perform" for m in cls.body)


def agent_classes(tree):
    """The classes the Brainstem would load, as brainstem.py _load_agent_from_file() chooses them: public, not
    BasicAgent itself, and with a perform() (hasattr), whether their own, BasicAgent's, or one inherited from a
    class in another file. The last kind can only be told apart when it runs, so it comes back as "maybe".
    Returns them most certain first, with the facts behind that choice."""
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    by_name = {cls.name: cls for cls in classes}
    kinds = {}
    for cls in classes:
        kinds[cls.name] = []
        for base in cls.bases:
            name = base.id if isinstance(base, ast.Name) else base.attr if isinstance(base, ast.Attribute) else None
            root = base.value.id if isinstance(base, ast.Subscript) and isinstance(base.value, ast.Name) else None
            if name == "BasicAgent":
                kinds[cls.name].append(("basic", None))
            elif isinstance(base, ast.Name) and name in by_name and name != cls.name:
                kinds[cls.name].append(("file", name))
            elif (isinstance(base, ast.Name) and name in OWN_BASES) or root in OWN_BASES:
                kinds[cls.name].append(("own", None))
            else:
                kinds[cls.name].append(("elsewhere", None))
    basic, elsewhere = set(), set()
    changed = True
    while changed:
        changed = False
        for cls in classes:
            for kind, name in kinds[cls.name]:
                for flag, marks in ((kind == "basic" or (kind == "file" and name in basic), basic),
                                    (kind == "elsewhere" or (kind == "file" and name in elsewhere), elsewhere)):
                    if flag and cls.name not in marks:
                        marks.add(cls.name)
                        changed = True
    public = [cls for cls in classes if cls.name not in ("BasicAgent", "object") and not cls.name.startswith("_")]
    certain = [cls for cls in public if cls.name in basic]
    own = [cls for cls in public if cls.name not in basic and defines_perform(cls)]
    maybe = [cls for cls in public if cls.name not in basic and not defines_perform(cls) and cls.name in elsewhere]
    return certain + own + maybe, {"basic": basic, "elsewhere": elsewhere, "maybe": {c.name for c in maybe}, "by_name": by_name}


def init_call(stmt):
    """super().__init__(...) or Base.__init__(self, ...): the arguments that become the name and metadata."""
    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
        return {}
    call, func = stmt.value, stmt.value.func
    if not (isinstance(func, ast.Attribute) and func.attr == "__init__"):
        return {}
    via_super = isinstance(func.value, ast.Call) and isinstance(func.value.func, ast.Name) and func.value.func.id == "super"
    args = call.args[0 if via_super else 1:]
    keywords = {k.arg: k.value for k in call.keywords if k.arg}
    return {
        "name": keywords.get("name", args[0] if len(args) > 0 else None),
        "metadata": keywords.get("metadata", args[1] if len(args) > 1 else None),
    }


def self_attribute(target):
    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
        return "self." + target.attr
    return None


def own_scope(cls, values, scope):
    """What a class sets for itself, on top of what it inherits in `scope`, following RAR's
    validate_runtime_contract(): its class-level assignments, then its __init__ in order, then what it gives
    BasicAgent.__init__."""
    class_names = {}
    for stmt in cls.body:
        for target, value in assignments(stmt):
            if isinstance(target, ast.Name):
                class_names[target.id] = scope["self." + target.id] = values.literal(value, class_names)
    init = next((m for m in cls.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == "__init__"), None)
    for stmt in in_order(init.body if init is not None else []):
        for target, value in assignments(stmt):
            key = target.id if isinstance(target, ast.Name) else self_attribute(target)
            if key:
                scope[key] = values.literal(value, scope)
        if isinstance(stmt, ast.AugAssign):
            key = stmt.target.id if isinstance(stmt.target, ast.Name) else self_attribute(stmt.target)
            if key:
                scope[key] = RUNTIME
        for key, node in init_call(stmt).items():
            # BasicAgent.__init__ keeps what the agent already set when it is given None.
            if node is not None and not (isinstance(node, ast.Constant) and node.value is None):
                scope["self." + key] = values.literal(node, scope)
    return scope


def agent_facts(cls, values, found, scopes):
    """An agent's name and metadata, with what it inherits from classes in this file. Set nowhere in this file
    but built on a class from another file, they are only known when it runs."""
    def scope_of(current, seen):
        if current.name not in scopes:
            inherited = {}
            for base in current.bases:
                parent = found["by_name"].get(base.id) if isinstance(base, ast.Name) else None
                if parent is not None and parent.name not in seen:
                    for key, value in scope_of(parent, seen | {current.name}).items():
                        if key.startswith("self."):
                            inherited.setdefault(key, value)
            scopes[current.name] = own_scope(current, values, inherited)
        return scopes[current.name]

    scope = scope_of(cls, {cls.name})
    doc = ast.get_docstring(cls)
    facts = {
        "class": clip(cls.name),
        "line": cls.lineno,
        "basic": cls.name in found["basic"],
        "perform": defines_perform(cls),
        "maybe": cls.name in found["maybe"],
        "elsewhere": cls.name in found["elsewhere"],
        "doc": clip(doc) if doc else None,
        "examples": docstring_examples(doc),
    }
    for key in ("name", "metadata"):
        if "self." + key in scope:
            facts[key] = shown(scope["self." + key])
        elif cls.name in found["elsewhere"]:
            facts[key] = RUNTIME
    return facts


def docstring_examples(doc):
    """Example prompts a docstring really lists: bulleted lines under a heading like "Example prompts:"."""
    if not doc:
        return []
    found, lines, i = [], doc.splitlines(), 0
    while i < len(lines) and len(found) < MAX_EXAMPLES:
        heading = lines[i].strip().strip("#*_ ").strip()
        i += 1
        if not EXAMPLES_HEADING.match(heading):
            continue
        while i < len(lines) and not lines[i].strip():
            i += 1
        while i < len(lines) and len(found) < MAX_EXAMPLES:
            item = EXAMPLE_ITEM.match(lines[i])
            if not item:
                break
            text = item.group(1).strip().strip("\"'`\u201c\u201d\u2018\u2019").strip()
            if text and text[0] not in "{[(<":
                found.append(text if len(text) <= 200 else text[:199] + "\u2026")
            i += 1
    return found


def docstring_nodes(tree):
    """The string constants that are docstrings: documentation, not something the code talks to."""
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                ids.add(id(first.value))
    return ids


def import_aliases(tree):
    """What each imported name stands for, so os.environ, getenv and subprocess.run are found however imported."""
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                aliases[alias.asname or top] = alias.name if alias.asname else top
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            for alias in node.names:
                if alias.name != "*":
                    aliases[alias.asname or alias.name] = node.module + "." + alias.name
    return aliases


def dotted(node, aliases):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    return ".".join([aliases.get(node.id, node.id)] + list(reversed(parts)))


def catches_import_errors(try_node):
    for handler in try_node.handlers:
        kinds = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
        if any(kind is None or (isinstance(kind, ast.Name) and kind.id in IMPORT_ERRORS) for kind in kinds):
            return True
    return False


def matched(path, prefixes):
    return next((p for p in prefixes if path == p or path.startswith(p + ".")), None)


class Stdlib:
    """Whether a top-level module is Python's own: sys.stdlib_module_names, or on Python 3.9 whether the
    standard library's own folders hold it (looked up there, never imported)."""

    def __init__(self):
        names = getattr(sys, "stdlib_module_names", None)
        self.names = set(names) if names else None
        self.paths = None

    def __contains__(self, top):
        if self.names is not None:
            return top in self.names
        if top in sys.builtin_module_names:
            return True
        import importlib.machinery
        import os
        import sysconfig
        if self.paths is None:
            paths = sysconfig.get_paths()
            self.paths = [paths["stdlib"], paths["platstdlib"], os.path.join(paths["stdlib"], "lib-dynload")]
        try:
            return importlib.machinery.PathFinder.find_spec(top, self.paths) is not None
        except (ImportError, ValueError):
            return False


def add(seen, value, limit):
    if value not in seen and len(seen) < limit:
        seen.append(value)


def host_of(authority):
    host = authority.rsplit("@", 1)[-1]
    host = host.split("]")[0] + "]" if host.startswith("[") else host.split(":")[0]
    host = host.lower().rstrip(".")
    if host in NAMESPACE_HOSTS:
        return None
    if HOST.match(host) or (host.startswith("[") and len(host) > 2 and re.match(r"\[[0-9a-f:.]+\]\Z", host)):
        return host
    return None


# ── Whether RAR would take it: RAR's build_registry.py, line for line ────────────────────────────────────

RAR_REQUIRED = ["schema", "name", "version", "display_name", "description", "author", "tags", "category"]
RAR_TOOL_NAME = re.compile(r"[A-Za-z0-9_-]+")
# DANGEROUS_PATTERNS, which scan_security() searches the whole file's text for, comments and strings included;
# any match is an error that keeps the agent out of the registry.
RAR_DANGEROUS = (
    (re.compile(r'\bos\.system\s*\('), "security-system"),
    (re.compile(r'\bopen\s*\(.*(\/etc|\/proc|\.env|\.ssh|passwd)'), "security-file"),
    (re.compile(r'(api[_-]?key|secret|password|token)\s*=\s*["\'][^"\']{8,}'), "security-secret"),
)


def rar_manifest(tree):
    """extract_manifest(): the first plain `__manifest__ = ...` anywhere, as a literal."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__manifest__":
                    try:
                        return ast.literal_eval(node.value), True
                    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                        return None, True
    return None, False


def rar_manifest_problems(manifest):
    """validate_manifest(), and the rapp-agent/1.0 schema itself."""
    if not isinstance(manifest, dict):
        return [{"code": "not-dict"}]
    problems = [{"code": "missing", "field": field} for field in RAR_REQUIRED if field not in manifest]
    if "schema" in manifest and manifest.get("schema") != "rapp-agent/1.0":
        problems.append({"code": "schema"})
    name = manifest.get("name", "")
    if not isinstance(name, str) or not name.startswith("@") or "/" not in name:
        problems.append({"code": "name"})
    version = manifest.get("version", "")
    parts = version.split(".") if isinstance(version, str) else []
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        problems.append({"code": "version"})
    if not isinstance(manifest.get("tags", []), list):
        problems.append({"code": "tags"})
    return problems


def rar_runtime_string(node, manifest, known):
    """_runtime_string(): only a string, a name or self attribute set earlier, or __manifest__["key"]."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return known.get(node.id)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
        return known.get("self." + node.attr)
    if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "__manifest__"
            and isinstance(node.slice, ast.Constant)):
        value = manifest.get(node.slice.value) if isinstance(manifest, dict) else None
        return value if isinstance(value, str) else None
    return None


def rar_metadata_name(node, manifest, known):
    if not isinstance(node, ast.Dict):
        return None
    for key_node, value_node in zip(node.keys, node.values):
        if isinstance(key_node, ast.Constant) and key_node.value == "name":
            return rar_runtime_string(value_node, manifest, known)
    return None


def rar_contract_problems(tree, manifest):
    """validate_runtime_contract(): every public top-level class with a perform() of its own."""
    problems = []
    classes = [
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name != "BasicAgent" and not node.name.startswith("_")
        and any(isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == "perform" for m in node.body)
    ]
    for cls in classes:
        known, runtime_names, metadata_names = {}, [], []

        def remember(target, value_node):
            value = rar_runtime_string(value_node, manifest, known)
            if isinstance(target, ast.Name) and value is not None:
                known[target.id] = value
                if target.id == "name":
                    runtime_names.append(value)
            elif self_attribute(target) and value is not None:
                known[self_attribute(target)] = value
                if target.attr == "name":
                    runtime_names.append(value)
            if (isinstance(target, ast.Name) and target.id == "metadata") or self_attribute(target) == "self.metadata":
                metadata_name = rar_metadata_name(value_node, manifest, known)
                if metadata_name is not None:
                    metadata_names.append(metadata_name)

        for member in cls.body:
            if isinstance(member, ast.Assign):
                for target in member.targets:
                    remember(target, member.value)
            if not (isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == "__init__"):
                continue
            for inner in ast.walk(member):
                if isinstance(inner, ast.Assign):
                    for target in inner.targets:
                        remember(target, inner.value)
                if not (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) and inner.func.attr == "__init__"):
                    continue
                name_arg = inner.args[0] if inner.args else next((k.value for k in inner.keywords if k.arg == "name"), None)
                if name_arg is not None:
                    value = rar_runtime_string(name_arg, manifest, known)
                    if value is not None:
                        runtime_names.append(value)
        runtime_names = list(dict.fromkeys(runtime_names))
        if not runtime_names:
            problems.append({"code": "no-name", "class": clip(cls.name)})
            continue
        if not all(RAR_TOOL_NAME.fullmatch(name) for name in runtime_names):
            problems.append({"code": "name-unsafe", "class": clip(cls.name)})
        if any(name not in runtime_names for name in dict.fromkeys(metadata_names)):
            problems.append({"code": "name-mismatch", "class": clip(cls.name)})
    return problems


def rar_security_problems(text):
    """scan_security(), over the text as read_text() gives it (newlines as \\n)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return [{"code": code} for pattern, code in RAR_DANGEROUS if pattern.search(text)]


def rar_reading(data):
    """How RAR's build_registry.py reads the file: read_text("utf-8"), which keeps a byte order mark as a character
    and fails on bytes that are not UTF-8, then ast.parse, which refuses that character. None when it reads it."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return {"code": "not-utf8"}
    return {"code": "bom"} if text.startswith("\ufeff") else None


def rar_verdict(tree, has_manifest, text, reading=None):
    """What stops RAR from taking this agent as it is, or [] when nothing does; None without a manifest."""
    manifest, found = rar_manifest(tree)
    if not found and not has_manifest:
        return None
    if reading:
        return [reading]
    if not found:
        return [{"code": "not-found"}]
    if manifest is None:
        return [{"code": "not-literal"}]
    return (rar_manifest_problems(manifest) + rar_contract_problems(tree, manifest) + rar_security_problems(text))[:20]


def read(tree, local, text, reading=None):
    values = Values(module_nodes(tree))
    manifest_node = next((value for stmt in tree.body for target, value in assignments(stmt)
                          if isinstance(target, ast.Name) and target.id == "__manifest__"), None)
    manifest, manifest_literal = None, False
    if manifest_node is not None:
        try:
            manifest, manifest_literal = ast.literal_eval(manifest_node), True
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            manifest = values.of(manifest_node, {})
        values.cache["__manifest__"] = manifest

    classes, found = agent_classes(tree)
    scopes = {}
    agents = [agent_facts(cls, values, found, scopes) for cls in classes[:20]]

    aliases = import_aliases(tree)
    docstrings = docstring_nodes(tree)
    stdlib = Stdlib()
    env, domains, internet, files, programs = [], [], [], [], []
    packages, optional = {}, {}

    def env_name(node):
        name = values.of(node, {})
        if isinstance(name, str) and ENV_NAME.match(name):
            add(env, name, MAX_NAMES)

    def environ(node):
        return dotted(node, aliases) == "os.environ"

    def note_module(path, guarded, line):
        network = matched(path, NETWORK)
        if network:
            add(internet, network, MAX_VIA)
        if matched(path, ("subprocess",)):
            add(programs, "subprocess", MAX_VIA)
        if matched(path, STORAGE):
            add(files, "your Brainstem's local storage", MAX_VIA)
        top = path.split(".")[0]
        if top == "__future__" or top in SHIMS or top in local or top in stdlib:
            return
        if top in packages:
            optional[top] = optional[top] and guarded
        else:
            packages[top], optional[top] = line, guarded

    stack = [(tree, False, False)]
    while stack:
        node, guarded, quiet = stack.pop()
        if isinstance(node, ast.Import):
            for alias in node.names:
                note_module(alias.name, guarded, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if not node.level and node.module:
                note_module(node.module, guarded, node.lineno)
                for alias in node.names:
                    network = matched(node.module + "." + alias.name, NETWORK)
                    if alias.name != "*" and network:
                        add(internet, network, MAX_VIA)
        elif isinstance(node, ast.Call):
            target = dotted(node.func, aliases) or ""
            method = node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if target == "os.getenv" or (method in ("get", "setdefault", "pop") and environ(node.func.value)):
                key = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg in ("key", "varname")), None)
                if key is not None:
                    env_name(key)
            network = matched(target, NETWORK)
            if network:
                add(internet, network, MAX_VIA)
            if target in FILE_CALLS or target.startswith(FILE_PREFIXES):
                add(files, target, MAX_VIA)
            elif method in FILE_METHODS:
                add(files, "." + method + "()", MAX_VIA)
            if target in PROGRAM_CALLS or target.startswith(PROGRAM_PREFIXES):
                add(programs, target, MAX_VIA)
        elif isinstance(node, ast.Subscript):
            if isinstance(node.ctx, ast.Load) and environ(node.value):
                env_name(node.slice)
        elif isinstance(node, ast.Compare):
            if len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.NotIn)) and environ(node.comparators[0]):
                env_name(node.left)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and not quiet and id(node) not in docstrings:
            for authority in URL.findall(node.value):
                host = host_of(authority)
                if host:
                    add(domains, host, MAX_DOMAINS)

        if isinstance(node, ast.Try) or type(node).__name__ == "TryStar":
            inner = guarded or catches_import_errors(node)
            children = [(child, inner) for child in node.body] + [(child, guarded) for child in node.handlers + node.orelse + node.finalbody]
            stack.extend((child, flag, quiet) for child, flag in reversed(children))
        else:
            stack.extend((child, guarded, quiet or child is manifest_node) for child in reversed(list(ast.iter_child_nodes(node))))

    doc = ast.get_docstring(tree)
    return {
        "schema": SCHEMA,
        "python": "%d.%d.%d" % sys.version_info[:3],
        "doc": clip(doc) if doc else None,
        "examples": docstring_examples(doc),
        "manifest": shown(manifest) if manifest_node is not None else None,
        "manifestLiteral": manifest_literal,
        "agents": agents,
        "rar": rar_verdict(tree, manifest_node is not None, text, reading),
        "env": env,
        "packages": [
            {"module": top, "pip": PIP_MAP.get(top, top), "optional": optional[top]}
            for top in sorted(packages, key=lambda name: packages[name])[:MAX_NAMES]
        ],
        "internet": {"via": internet, "domains": domains} if internet or domains else None,
        "files": {"via": files} if files else None,
        "programs": {"via": programs} if programs else None,
    }


def problem(kind, **details):
    return {"schema": SCHEMA, "problem": dict(kind=kind, **{k: v for k, v in details.items() if v is not None})}


def plain_syntax(message):
    """Python's words for a file it cannot decode name a codec and a byte, and differ between versions: said plainly."""
    if (message.startswith("(unicode error)") and "unicodeescape" in message) or message.startswith("(value error)"):
        return "a backslash in a text on this line starts an escape Python can\u2019t read"
    if message.startswith("(unicode error)") or message.startswith("Non-UTF-8 code"):
        return "a character on this line isn\u2019t UTF-8: save the file as UTF-8, or name its encoding in a coding: line"
    if message.startswith("unknown encoding"):
        return "its coding: line names an encoding Python doesn\u2019t know"
    if re.match(r"'[\w.-]+' codec can't decode", message):
        return "a character in it isn\u2019t one the encoding its coding: line names can hold"
    if message.startswith("source code string cannot contain null bytes"):
        return "the file contains a null character"
    if message.startswith("encoding problem"):
        return "its coding: line doesn\u2019t match how the file begins (a UTF-8 byte order mark needs a UTF-8 coding: line)"
    return message


def main(argv):
    warnings.simplefilter("ignore")
    local = {name for flag, name in zip(argv[::2], argv[1::2]) if flag == "--local" and IDENTIFIER.match(name)}
    data = sys.stdin.buffer.read(MAX_SOURCE + 1)
    if len(data) > MAX_SOURCE:
        return problem("too-big")
    try:
        # The file's bytes, decoded as Python decodes a file it imports (UTF-8, a BOM, or a coding: line), so a
        # file the Brainstem could not read is not one the card reads.
        tree = ast.parse(data, "<agent>", "exec")
        # The stricter gate RAR's build_registry.py uses: compile() only makes a code object, and it catches
        # what parses yet fails when the Brainstem imports the file ('return' outside a function, a late
        # __future__ import).
        compile(tree, "<agent>", "exec", dont_inherit=True)
    except SyntaxError as error:
        return problem("syntax", line=error.lineno or None, column=error.offset, message=clip(plain_syntax(str(error.msg or "invalid syntax"))))
    except ValueError:
        return problem("syntax", message="the file contains a null character")
    except (RecursionError, MemoryError):
        return problem("too-deep")
    try:
        return read(tree, local, data.decode("utf-8", "replace"), rar_reading(data))
    except (RecursionError, MemoryError):
        return problem("too-deep")


if __name__ == "__main__":
    try:
        result = json.dumps(main(sys.argv[1:]), ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    except Exception:  # never a traceback: it could quote the agent's source
        result = json.dumps(problem("internal"))
    sys.stdout.write(result)
