"""
HatchRappAgent — scaffolds, tests, and deploys RAPP Swarm projects.

Supports two deployment targets:
  - azure_functions: Azure Function App backend with local development support
  - copilot_studio: Copilot Studio native agents (MCS format)

All file templates are inline string constants — this agent is fully self-contained.
"""

from openrappter.agents.basic_agent import BasicAgent
import os
import json
import re
import shutil
import subprocess
import time


# =============================================================================
# INLINE FILE TEMPLATES
# =============================================================================

TEMPLATE_HOST_JSON = """{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
"""

TEMPLATE_REQUIREMENTS = """azure-functions==1.18.0
azure-identity>=1.15.0
openai>=1.55.0
httpx>=0.27.0
requests>=2.31.0
python-dotenv>=1.0.0
python-dateutil>=2.8.2
"""

TEMPLATE_FUNCIGNORE = """.venv
.env
local.settings.json
local.settings.template.json
.local_storage
__pycache__
*.pyc
*.pyo
.git
.gitignore
.claude
.vscode
.idea
*.md
tests/
test_*.py
experimental/
docs/
*.html
*.zip
"""

TEMPLATE_LOCAL_SETTINGS = """{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage__accountName": "<your-storage-account-name>",
    "AZURE_OPENAI_API_KEY": "<your-openai-api-key>",
    "AZURE_OPENAI_ENDPOINT": "https://<your-openai-service>.openai.azure.com/",
    "AZURE_OPENAI_API_VERSION": "2024-02-01",
    "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-deployment",
    "AZURE_STORAGE_ACCOUNT_NAME": "<your-storage-account-name>",
    "AZURE_FILES_SHARE_NAME": "<your-file-share-name>",
    "ASSISTANT_NAME": "RAPP Agent",
    "CHARACTERISTIC_DESCRIPTION": "AI assistant with memory and agent capabilities"
  },
  "Host": {
    "CORS": "*",
    "CORSCredentials": false
  }
}
"""

TEMPLATE_AGENTS_INIT = ""
TEMPLATE_UTILS_INIT = ""

TEMPLATE_BASIC_AGENT = '''class BasicAgent:
    def __init__(self, name, metadata):
        self.name = name
        self.metadata = metadata

    def perform(self):
        pass
'''

TEMPLATE_CONTEXT_MEMORY_AGENT = '''import logging
from agents.basic_agent import BasicAgent
from utils.storage_factory import get_storage_manager


class ContextMemoryAgent(BasicAgent):
    def __init__(self):
        self.name = \'ContextMemory\'
        self.metadata = {
            "name": self.name,
            "description": "Recalls and provides context based on stored memories of past interactions with the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_guid": {
                        "type": "string",
                        "description": "Optional unique identifier of the user to recall memories from a user-specific location."
                    },
                    "max_messages": {
                        "type": "integer",
                        "description": "Optional maximum number of messages to include in the context. Default is 10."
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of keywords to filter memories by."
                    },
                    "full_recall": {
                        "type": "boolean",
                        "description": "Optional flag to return all memories without filtering. Default is false."
                    }
                },
                "required": []
            }
        }
        self.storage_manager = get_storage_manager()
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        user_guid = kwargs.get(\'user_guid\')
        max_messages = kwargs.get(\'max_messages\', 10)
        keywords = kwargs.get(\'keywords\', [])
        full_recall = kwargs.get(\'full_recall\', False)
        if \'max_messages\' not in kwargs and \'keywords\' not in kwargs:
            full_recall = True
        self.storage_manager.set_memory_context(user_guid)
        return self._recall_context(max_messages, keywords, full_recall)

    def _recall_context(self, max_messages, keywords, full_recall=False):
        memory_data = self.storage_manager.read_json()
        if not memory_data:
            if self.storage_manager.current_guid:
                return f"No memories stored yet for user {self.storage_manager.current_guid}."
            return "No memories stored in shared memory yet."
        legacy_memories = []
        for key, value in memory_data.items():
            if isinstance(value, dict) and \'message\' in value:
                legacy_memories.append(value)
        if not legacy_memories:
            return "No memories found."
        return self._format_legacy_memories(legacy_memories, max_messages, keywords, full_recall)

    def _format_legacy_memories(self, memories, max_messages, keywords, full_recall=False):
        if not memories:
            return "No memories found."
        if full_recall:
            sorted_memories = sorted(memories, key=lambda x: (x.get(\'date\', \'\'), x.get(\'time\', \'\')), reverse=True)
            lines = []
            for m in sorted_memories:
                msg = m.get(\'message\', \'\')
                theme = m.get(\'theme\', \'Unknown\')
                date = m.get(\'date\', \'\')
                t = m.get(\'time\', \'\')
                if date and t:
                    lines.append(f"* {msg} (Theme: {theme}, Recorded: {date} {t})")
                else:
                    lines.append(f"* {msg} (Theme: {theme})")
            if not lines:
                return "No memories found."
            src = f"for user {self.storage_manager.current_guid}" if self.storage_manager.current_guid else "from shared memory"
            return f"All memories {src}:\\n" + "\\n".join(lines)
        if keywords:
            filtered = [m for m in memories if any(
                k.lower() in str(m.get(\'message\', \'\')).lower() or k.lower() in str(m.get(\'theme\', \'\')).lower()
                for k in keywords
            )]
            if filtered:
                memories = filtered
            else:
                memories = sorted(memories, key=lambda x: (x.get(\'date\', \'\'), x.get(\'time\', \'\')), reverse=True)[:max_messages]
        else:
            memories = sorted(memories, key=lambda x: (x.get(\'date\', \'\'), x.get(\'time\', \'\')), reverse=True)[:max_messages]
        lines = []
        for m in memories:
            msg = m.get(\'message\', \'\')
            theme = m.get(\'theme\', \'Unknown\')
            date = m.get(\'date\', \'\')
            t = m.get(\'time\', \'\')
            if date and t:
                lines.append(f"* {msg} (Theme: {theme}, Recorded: {date} {t})")
            else:
                lines.append(f"* {msg} (Theme: {theme})")
        if not lines:
            return "No matching memories found."
        src = f"for user {self.storage_manager.current_guid}" if self.storage_manager.current_guid else "from shared memory"
        return f"Memories {src}:\\n" + "\\n".join(lines)
'''

TEMPLATE_MANAGE_MEMORY_AGENT = '''import uuid
from datetime import datetime
from agents.basic_agent import BasicAgent
from utils.storage_factory import get_storage_manager


class ManageMemoryAgent(BasicAgent):
    def __init__(self):
        self.name = \'ManageMemory\'
        self.metadata = {
            "name": self.name,
            "description": "Stores memories for future reference. Saves facts, preferences, insights, and tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_type": {
                        "type": "string",
                        "description": "Type of memory: fact, preference, insight, or task.",
                        "enum": ["fact", "preference", "insight", "task"]
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to store in memory."
                    },
                    "importance": {
                        "type": "integer",
                        "description": "Importance rating from 1-5.",
                        "minimum": 1,
                        "maximum": 5
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags to categorize this memory."
                    },
                    "user_guid": {
                        "type": "string",
                        "description": "Optional user identifier for user-specific storage."
                    }
                },
                "required": ["memory_type", "content"]
            }
        }
        self.storage_manager = get_storage_manager()
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        memory_type = kwargs.get(\'memory_type\', \'fact\')
        content = kwargs.get(\'content\', \'\')
        user_guid = kwargs.get(\'user_guid\')
        if not content:
            return "Error: No content provided for memory storage."
        self.storage_manager.set_memory_context(user_guid)
        return self._store_memory(memory_type, content)

    def _store_memory(self, memory_type, content):
        memory_data = self.storage_manager.read_json()
        if not memory_data:
            memory_data = {}
        memory_id = str(uuid.uuid4())
        memory_data[memory_id] = {
            "conversation_id": self.storage_manager.current_guid or "current",
            "session_id": "current",
            "message": content,
            "mood": "neutral",
            "theme": memory_type,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S")
        }
        self.storage_manager.write_json(memory_data)
        loc = f"for user {self.storage_manager.current_guid}" if self.storage_manager.current_guid else "in shared memory"
        return f\'Successfully stored {memory_type} memory {loc}: \\"{content}\\"\'
'''

TEMPLATE_ENVIRONMENT = '''import os
import logging


def is_running_in_azure():
    indicators = [\'WEBSITE_INSTANCE_ID\', \'WEBSITE_SITE_NAME\', \'APPSETTING_WEBSITE_SITE_NAME\']
    for ind in indicators:
        if os.environ.get(ind):
            return True
    return False


def should_use_azure_storage():
    if os.environ.get(\'USE_CLOUD_STORAGE\', \'\').lower() in (\'true\', \'1\', \'yes\'):
        return True
    if is_running_in_azure():
        return True
    storage_account = os.environ.get(\'AZURE_STORAGE_ACCOUNT_NAME\')
    share_name = os.environ.get(\'AZURE_FILES_SHARE_NAME\')
    if storage_account and share_name:
        return True
    return False
'''

TEMPLATE_STORAGE_FACTORY = '''import logging
from utils.local_file_storage import LocalFileStorageManager

_instance = None


def get_storage_manager():
    global _instance
    if _instance is None:
        logging.info("Using local file storage")
        _instance = LocalFileStorageManager()
    return _instance


def reset_storage_manager():
    global _instance
    _instance = None
'''

TEMPLATE_LOCAL_FILE_STORAGE = '''"""
Local File Storage Manager

Provides a local file system fallback that implements the same interface
as AzureFileStorageManager for seamless local development.
"""

import json
import os
import logging
import re
from typing import Optional, Union, Any, List
from datetime import datetime


def safe_json_loads(json_str):
    """
    Safely loads JSON string, handling potential errors.
    """
    if not json_str:
        return {}
    try:
        if isinstance(json_str, (dict, list)):
            return json_str
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON: {json_str}"}


class LocalFileItem:
    """Mock object to match Azure File Storage list_files return type"""
    def __init__(self, name: str, is_directory: bool = False):
        self.name = name
        self.is_directory = is_directory


class LocalFileStorageManager:
    """
    Local file system storage manager that mirrors AzureFileStorageManager interface.

    Uses local filesystem under .local_storage/ directory for development.
    """

    # Intentionally invalid default GUID - contains non-hex chars to prevent DB insertion
    DEFAULT_MARKER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"

    def __init__(self, base_path: Optional[str] = None):
        if base_path:
            self.base_path = base_path
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.base_path = os.path.join(project_root, \'.local_storage\')

        os.makedirs(self.base_path, exist_ok=True)
        logging.info(f"Initialized local storage at: {self.base_path}")

        self.shared_memory_path = "shared_memories"
        self.default_file_name = \'memory.json\'
        self.current_guid = None
        self.current_memory_path = self.shared_memory_path

        self._ensure_defaults()

    def _ensure_defaults(self):
        """Ensure default directories and files exist."""
        try:
            shared_dir = os.path.join(self.base_path, self.shared_memory_path)
            os.makedirs(shared_dir, exist_ok=True)

            default_memory = os.path.join(shared_dir, self.default_file_name)
            if not os.path.exists(default_memory):
                with open(default_memory, \'w\') as f:
                    json.dump({}, f)
                logging.info(f"Created default memory file: {default_memory}")

        except Exception as e:
            logging.error(f"Error ensuring defaults: {str(e)}")

    def _get_full_path(self, directory_name: str, file_name: str = None) -> str:
        """Get full filesystem path."""
        if file_name:
            return os.path.join(self.base_path, directory_name, file_name)
        return os.path.join(self.base_path, directory_name)

    def set_memory_context(self, guid: Optional[str] = None) -> bool:
        if not guid:
            self.current_guid = None
            self.current_memory_path = self.shared_memory_path
            return True

        if guid == self.DEFAULT_MARKER_GUID:
            logging.debug("Default marker GUID detected - using shared memory (this is expected)")
            self.current_guid = None
            self.current_memory_path = self.shared_memory_path
            return True

        guid_pattern = re.compile(
            r\'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$\',
            re.IGNORECASE
        )
        if not guid_pattern.match(guid):
            logging.warning(f"Invalid GUID format: {guid}. Using shared memory.")
            self.current_guid = None
            self.current_memory_path = self.shared_memory_path
            return False

        try:
            guid_dir = f"memory/{guid}"
            guid_file = "user_memory.json"
            file_path = self._get_full_path(guid_dir, guid_file)

            if os.path.exists(file_path):
                self.current_guid = guid
                self.current_memory_path = guid_dir
                return True
            else:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, \'w\') as f:
                    json.dump({}, f)
                logging.info(f"Created new memory file for GUID: {guid}")
                self.current_guid = guid
                self.current_memory_path = guid_dir
                return True

        except Exception as e:
            logging.error(f"Error setting memory context for GUID {guid}: {str(e)}")
            self.current_guid = None
            self.current_memory_path = self.shared_memory_path
            return False

    def read_json(self) -> dict:
        """Read from either GUID-specific memory or shared memories."""
        if self.current_guid and self.current_memory_path != self.shared_memory_path:
            try:
                return self._read_guid_memory()
            except Exception:
                self.current_guid = None
                self.current_memory_path = self.shared_memory_path
                return self._read_shared_memory()
        else:
            return self._read_shared_memory()

    def _read_shared_memory(self) -> dict:
        """Read from shared memory location."""
        try:
            file_path = self._get_full_path(self.shared_memory_path, self.default_file_name)
            with open(file_path, \'r\') as f:
                content = f.read()
            return safe_json_loads(content)
        except FileNotFoundError:
            logging.warning("Shared memory file not found, recreating...")
            self._ensure_defaults()
            return {}
        except Exception as e:
            logging.error(f"Error reading from shared memory: {str(e)}")
            return {}

    def _read_guid_memory(self) -> dict:
        """Read from GUID-specific memory location."""
        try:
            file_path = self._get_full_path(self.current_memory_path, "user_memory.json")
            with open(file_path, \'r\') as f:
                content = f.read()
            return safe_json_loads(content)
        except Exception as e:
            logging.error(f"Error reading from GUID memory: {str(e)}")
            raise

    def write_json(self, data: dict):
        """Write to either GUID-specific memory or shared memories."""
        if self.current_guid and self.current_memory_path != self.shared_memory_path:
            try:
                self._write_guid_memory(data)
            except Exception:
                self.current_guid = None
                self.current_memory_path = self.shared_memory_path
                self._write_shared_memory(data)
        else:
            self._write_shared_memory(data)

    def _write_shared_memory(self, data: dict):
        """Write to shared memory location."""
        try:
            file_path = self._get_full_path(self.shared_memory_path, self.default_file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, \'w\') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logging.error(f"Error writing to shared memory: {str(e)}")
            raise

    def _write_guid_memory(self, data: dict):
        """Write to GUID-specific memory location."""
        try:
            file_path = self._get_full_path(self.current_memory_path, "user_memory.json")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, \'w\') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logging.error(f"Error writing to GUID memory: {str(e)}")
            raise

    def ensure_directory_exists(self, directory_name: str) -> bool:
        try:
            if not directory_name:
                return False
            full_path = self._get_full_path(directory_name)
            os.makedirs(full_path, exist_ok=True)
            logging.debug(f"Ensured directory exists: {full_path}")
            return True
        except Exception as e:
            logging.error(f"Error ensuring directory exists: {str(e)}")
            return False

    def write_file(self, directory_name: str, file_name: str, content: Union[str, bytes, Any]) -> bool:
        try:
            file_path = self._get_full_path(directory_name, file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            if isinstance(content, (bytes, bytearray)):
                binary_content = content
                mode = \'wb\'
            elif hasattr(content, \'read\') and callable(content.read):
                content.seek(0)
                binary_content = content.read()
                if isinstance(binary_content, (bytes, bytearray)):
                    mode = \'wb\'
                else:
                    binary_content = str(binary_content)
                    mode = \'w\'
            else:
                binary_content = str(content)
                mode = \'w\'

            with open(file_path, mode) as f:
                f.write(binary_content)

            logging.debug(f"Wrote file: {file_path}")
            return True

        except Exception as e:
            logging.error(f"Error writing file: {str(e)}")
            return False

    def read_file(self, directory_name: str, file_name: str) -> Optional[Union[str, bytes]]:
        try:
            file_path = self._get_full_path(directory_name, file_name)

            binary_extensions = (\'.pptx\', \'.docx\', \'.xlsx\', \'.pdf\', \'.zip\', \'.jpg\', \'.png\', \'.gif\', \'.jpeg\', \'.webp\')
            if file_name.lower().endswith(binary_extensions):
                return self.read_file_binary(directory_name, file_name)

            with open(file_path, \'r\', encoding=\'utf-8\') as f:
                return f.read()

        except UnicodeDecodeError:
            return self.read_file_binary(directory_name, file_name)
        except FileNotFoundError:
            logging.warning(f"File not found: {directory_name}/{file_name}")
            return None
        except Exception as e:
            logging.error(f"Error reading file: {str(e)}")
            return None

    def read_file_binary(self, directory_name: str, file_name: str) -> Optional[bytes]:
        try:
            file_path = self._get_full_path(directory_name, file_name)
            with open(file_path, \'rb\') as f:
                return f.read()
        except FileNotFoundError:
            logging.warning(f"Binary file not found: {directory_name}/{file_name}")
            return None
        except Exception as e:
            logging.error(f"Error reading binary file: {str(e)}")
            return None

    def list_files(self, directory_name: str, auto_create: bool = True) -> List[LocalFileItem]:
        try:
            dir_path = self._get_full_path(directory_name)
            if not os.path.exists(dir_path):
                if auto_create:
                    logging.info(f"Directory not found, creating: {directory_name}")
                    os.makedirs(dir_path, exist_ok=True)
                    return []
                else:
                    logging.warning(f"Directory not found: {directory_name}")
                    return []

            items = []
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                is_dir = os.path.isdir(item_path)
                items.append(LocalFileItem(item, is_directory=is_dir))
            return items

        except Exception as e:
            logging.error(f"Error listing files: {str(e)}")
            return []

    def delete_file(self, directory_name: str, file_name: str) -> bool:
        try:
            file_path = self._get_full_path(directory_name, file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Deleted file: {file_path}")
                return True
            else:
                logging.warning(f"File not found for deletion: {directory_name}/{file_name}")
                return False
        except Exception as e:
            logging.error(f"Error deleting file: {str(e)}")
            return False

    def file_exists(self, directory_name: str, file_name: str) -> bool:
        try:
            file_path = self._get_full_path(directory_name, file_name)
            return os.path.exists(file_path)
        except Exception as e:
            logging.error(f"Error checking file existence: {str(e)}")
            return False
'''

TEMPLATE_RESULT = '''"""
Result Type for Explicit Error Handling

A minimal, pragmatic Result type that surfaces failures instead of silently
swallowing them. Based on functional programming patterns but kept simple
for Python.

Usage:
    from utils.result import Result, Success, Failure

    def load_something() -> Result:
        try:
            data = do_risky_thing()
            return Success(data)
        except Exception as e:
            return Failure(f"Failed to load: {e}")

    result = load_something()
    if result.is_success:
        print(result.value)
    else:
        print(f"Error: {result.error}")
"""

from dataclasses import dataclass
from typing import TypeVar, Generic, Callable, List, Tuple, Optional, Union

T = TypeVar(\'T\')
E = TypeVar(\'E\')
U = TypeVar(\'U\')


@dataclass(frozen=True)
class Success(Generic[T]):
    """Represents a successful result containing a value."""
    value: T

    @property
    def is_success(self) -> bool:
        return True

    @property
    def is_failure(self) -> bool:
        return False

    def map(self, f: Callable[[T], U]) -> \'Result[U, E]\':
        return Success(f(self.value))

    def flat_map(self, f: Callable[[T], \'Result[U, E]\']) -> \'Result[U, E]\':
        return f(self.value)

    def get_or_else(self, default: T) -> T:
        return self.value

    def fold(self, on_failure: Callable[[E], U], on_success: Callable[[T], U]) -> U:
        return on_success(self.value)

    def __repr__(self) -> str:
        return f"Success({self.value!r})"


@dataclass(frozen=True)
class Failure(Generic[E]):
    """Represents a failed result containing an error."""
    error: E

    @property
    def is_success(self) -> bool:
        return False

    @property
    def is_failure(self) -> bool:
        return True

    def map(self, f: Callable) -> \'Result[T, E]\':
        return self

    def flat_map(self, f: Callable) -> \'Result[T, E]\':
        return self

    def get_or_else(self, default: T) -> T:
        return default

    def fold(self, on_failure: Callable[[E], U], on_success: Callable[[T], U]) -> U:
        return on_failure(self.error)

    def __repr__(self) -> str:
        return f"Failure({self.error!r})"


Result = Union[Success[T], Failure[E]]


@dataclass(frozen=True)
class AgentLoadError:
    """Error that occurred while loading an agent."""
    agent_name: str
    source: str
    error_type: str
    message: str

    def __str__(self) -> str:
        return f"[{self.source}] {self.agent_name}: {self.error_type} - {self.message}"


@dataclass(frozen=True)
class APIError:
    """Error from OpenAI API call."""
    error_type: str
    message: str
    status_code: Optional[int] = None
    retryable: bool = False

    def __str__(self) -> str:
        code = f" ({self.status_code})" if self.status_code else ""
        retry = " [retryable]" if self.retryable else ""
        return f"{self.error_type}{code}: {self.message}{retry}"


def partition_results(results: List) -> Tuple[List, List]:
    successes = []
    failures = []
    for result in results:
        if isinstance(result, Success):
            successes.append(result.value)
        else:
            failures.append(result.error)
    return successes, failures


def sequence_results(results: List) -> Union[\'Success\', \'Failure\']:
    successes, failures = partition_results(results)
    if failures:
        return Failure(failures)
    return Success(successes)


def try_result(f: Callable, error_mapper: Callable) -> Union[\'Success\', \'Failure\']:
    try:
        return Success(f())
    except Exception as e:
        return Failure(error_mapper(e))
'''

TEMPLATE_FUNCTION_APP = '''import azure.functions as func
import logging
import json
import os
import importlib
import importlib.util
import inspect
import sys
import re
from agents.basic_agent import BasicAgent
from openai import AzureOpenAI, APIError as OpenAIAPIError, RateLimitError, AuthenticationError, APITimeoutError, BadRequestError
from azure.identity import ChainedTokenCredential, ManagedIdentityCredential, AzureCliCredential, get_bearer_token_provider
from datetime import datetime
import time


def safe_json_loads(s):
    if not s:
        return {}
    try:
        if isinstance(s, (dict, list)):
            return s
        return json.loads(s)
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON: {s}"}


def ensure_string_content(message):
    if message is None:
        return {"role": "user", "content": ""}
    if not isinstance(message, dict):
        return {"role": "user", "content": str(message) if message is not None else ""}
    message = message.copy()
    if \'role\' not in message:
        message[\'role\'] = \'user\'
    if \'content\' in message:
        message[\'content\'] = str(message[\'content\']) if message[\'content\'] is not None else \'\'
    else:
        message[\'content\'] = \'\'
    return message


def build_cors_response(origin):
    return {
        "Access-Control-Allow-Origin": str(origin) if origin else "*",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "86400",
    }


def load_agents_from_folder():
    agents_directory = os.path.join(os.path.dirname(__file__), "agents")
    agent_files = [f for f in os.listdir(agents_directory)
                   if f.endswith(".py") and f not in ["__init__.py", "basic_agent.py"]]
    declared_agents = {}
    for file in agent_files:
        module_name = file[:-3]
        try:
            module = importlib.import_module(f\'agents.{module_name}\')
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BasicAgent) and obj is not BasicAgent:
                    agent_instance = obj()
                    declared_agents[agent_instance.name] = agent_instance
        except Exception as e:
            logging.error(f"Failed to load agent {file}: {e}")
    logging.info(f"Loaded {len(declared_agents)} agent(s): {list(declared_agents.keys())}")
    return declared_agents


class Assistant:
    def __init__(self, declared_agents):
        self.config = {
            \'assistant_name\': os.environ.get(\'ASSISTANT_NAME\', \'RAPP Agent\'),
            \'characteristic_description\': os.environ.get(\'CHARACTERISTIC_DESCRIPTION\', \'AI assistant\')
        }
        api_key = os.environ.get(\'AZURE_OPENAI_API_KEY\')
        if api_key:
            self.client = AzureOpenAI(
                azure_endpoint=os.environ[\'AZURE_OPENAI_ENDPOINT\'],
                api_key=api_key,
                api_version=os.environ.get(\'AZURE_OPENAI_API_VERSION\', \'2025-01-01-preview\')
            )
        else:
            if os.environ.get(\'WEBSITE_INSTANCE_ID\'):
                credential = ManagedIdentityCredential()
            else:
                credential = ChainedTokenCredential(ManagedIdentityCredential(), AzureCliCredential())
            token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
            self.client = AzureOpenAI(
                azure_endpoint=os.environ[\'AZURE_OPENAI_ENDPOINT\'],
                azure_ad_token_provider=token_provider,
                api_version=os.environ.get(\'AZURE_OPENAI_API_VERSION\', \'2025-01-01-preview\')
            )
        self.known_agents = {a.name: a for a in declared_agents.values() if hasattr(a, \'name\')}

    def get_agent_tools(self):
        tools = []
        for agent in self.known_agents.values():
            if hasattr(agent, \'metadata\'):
                tools.append({"type": "function", "function": agent.metadata})
        return tools

    def prepare_messages(self, conversation_history):
        messages = [{
            "role": "system",
            "content": f"You are {self.config[\'assistant_name\']}, an AI assistant. "
                       f"Current date: {datetime.now().strftime(\'%A, %B %d, %Y at %I:%M %p\')}. "
                       f"You have access to specialized agents as tools. "
                       f"Be honest about agent usage - only report results from actual tool calls."
        }]
        for msg in (conversation_history or []):
            messages.append(ensure_string_content(msg))
        return messages

    def get_response(self, prompt, conversation_history):
        messages = self.prepare_messages(conversation_history)
        messages.append(ensure_string_content({"role": "user", "content": prompt}))
        agent_logs = []
        deployment_name = os.environ.get(\'AZURE_OPENAI_DEPLOYMENT_NAME\', \'gpt-deployment\')

        for _ in range(3):  # max tool-calling rounds
            try:
                tools = self.get_agent_tools()
                kwargs = {"model": deployment_name, "messages": messages}
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"
                response = self.client.chat.completions.create(**kwargs)
            except RateLimitError:
                return "Rate limited. Please try again.", ""
            except AuthenticationError:
                return "Authentication error. Check your Azure OpenAI credentials.", ""
            except Exception as e:
                return f"API error: {e}", ""

            msg = response.choices[0].message
            if not msg.tool_calls:
                return msg.content or "", "\\n".join(agent_logs)

            tool_call = msg.tool_calls[0]
            agent_name = tool_call.function.name
            agent = self.known_agents.get(agent_name)
            if not agent:
                return f"Agent \'{agent_name}\' not found.", ""

            try:
                params = safe_json_loads(tool_call.function.arguments or "{}")
                sanitized = {k: ("" if v is None else v) for k, v in params.items()}
                result = str(agent.perform(**sanitized))
                agent_logs.append(f"Called {agent_name}: {result[:200]}")
            except Exception as e:
                result = f"Error: {e}"
                agent_logs.append(f"Error calling {agent_name}: {e}")

            messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
                {"id": tool_call.id, "type": "function", "function": {"name": agent_name, "arguments": tool_call.function.arguments or "{}"}}
            ]})
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

        return "Max tool-calling rounds reached.", "\\n".join(agent_logs)


app = func.FunctionApp()

@app.route(route="rapp_function", auth_level=func.AuthLevel.FUNCTION)
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(\'RAPP function processed a request.\')
    origin = req.headers.get(\'origin\')
    cors_headers = build_cors_response(origin)

    if req.method == \'OPTIONS\':
        return func.HttpResponse(status_code=200, headers=cors_headers)

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON", status_code=400, headers=cors_headers)

    user_input = str(req_body.get(\'user_input\', \'\'))
    conversation_history = req_body.get(\'conversation_history\', [])
    if not user_input.strip():
        return func.HttpResponse(json.dumps({"error": "Missing user_input"}), status_code=400, mimetype="application/json", headers=cors_headers)

    try:
        agents = load_agents_from_folder()
        assistant = Assistant(agents)
        response, agent_logs = assistant.get_response(user_input, conversation_history)
        return func.HttpResponse(
            json.dumps({"assistant_response": response, "agent_logs": agent_logs}),
            mimetype="application/json", headers=cors_headers
        )
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json", headers=cors_headers)
'''

TEMPLATE_COPILOT_TRANSPILER_AGENT = '''"""
CopilotStudioTranspilerAgent (stripped) — Converts RAPP Python agents to native
Copilot Studio solutions without requiring a Function App backend.

This is a template stub included with projects scaffolded for the copilot_studio target.
It maps RAPP agent capabilities to:
  - Native Copilot Studio Topics
  - Power Automate Flows (for complex logic)
  - Native Connectors (Salesforce, SharePoint, Dataverse, Outlook, etc.)
  - Generative AI capabilities (replaces direct Azure OpenAI calls)
"""

import json
import os
import re
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from agents.basic_agent import BasicAgent

logger = logging.getLogger(__name__)

# =============================================================================
# CONNECTOR MAPPINGS
# =============================================================================

CONNECTOR_MAPPINGS = {
    "salesforce": {
        "connector_id": "shared_salesforce",
        "display_name": "Salesforce",
        "operations": {
            "query": "GetItems",
            "create": "PostItem",
            "update": "PatchItem",
            "get_by_id": "GetItem"
        }
    },
    "cosmos_db": {
        "connector_id": "shared_documentdb",
        "display_name": "Azure Cosmos DB",
        "alternative": "dataverse",
        "operations": {
            "query": "QueryDocuments",
            "create": "CreateDocument",
            "update": "ReplaceDocument"
        }
    },
    "sharepoint": {
        "connector_id": "shared_sharepointonline",
        "display_name": "SharePoint",
        "operations": {
            "get_files": "GetFileContent",
            "create_file": "CreateFile",
            "list_items": "GetItems"
        }
    },
    "azure_openai": {
        "connector_id": None,
        "display_name": "Generative AI (Native)",
        "note": "Handled by Copilot Studio\'s built-in AI capabilities"
    },
    "outlook": {
        "connector_id": "shared_office365",
        "display_name": "Office 365 Outlook",
        "operations": {
            "send_email": "SendEmail",
            "get_emails": "GetEmails"
        }
    }
}


class CopilotStudioTranspilerAgent(BasicAgent):
    """
    Transpiles RAPP Python agents to native Copilot Studio solutions.

    Actions: transpile, analyze, preview
    """

    def __init__(self):
        self.name = "CopilotStudioTranspiler"
        self.metadata = {
            "name": self.name,
            "description": "Converts RAPP Python agents to fully native Copilot Studio solutions without Function App dependency.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["transpile", "analyze", "preview"],
                        "description": "Action to perform"
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the RAPP agent to transpile"
                    },
                    "agent_file": {
                        "type": "string",
                        "description": "Path to the agent Python file (optional)"
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["solution", "yaml", "json"],
                        "description": "Output format"
                    },
                    "include_flows": {
                        "type": "boolean",
                        "description": "Generate Power Automate flows for complex actions"
                    }
                },
                "required": ["action"]
            }
        }
        super().__init__(name=self.name, metadata=self.metadata)
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_path = os.path.join(self.base_path, "transpiled", "copilot_studio_native")

    def perform(self, **kwargs) -> str:
        action = kwargs.get("action", "analyze")
        try:
            if action == "transpile":
                return self._transpile(**kwargs)
            elif action == "analyze":
                return self._analyze(**kwargs)
            elif action == "preview":
                return self._preview(**kwargs)
            else:
                return json.dumps({"status": "error", "error": f"Unknown action: {action}"})
        except Exception as e:
            logger.error(f"Transpiler error: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    def _parse_agent(self, agent_name: str, agent_file: str = None) -> Optional[Dict]:
        """Locate and parse an agent Python file."""
        search_dirs = [
            os.path.join(self.base_path, "agents"),
            self.base_path
        ]
        if agent_file:
            search_dirs.insert(0, os.path.dirname(agent_file))

        for directory in search_dirs:
            if not os.path.isdir(directory):
                continue
            for fname in os.listdir(directory):
                if not fname.endswith(".py"):
                    continue
                if agent_name.lower() in fname.lower():
                    fpath = os.path.join(directory, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            source = f.read()
                        return {"name": agent_name, "file": fpath, "source": source}
                    except Exception as e:
                        logger.warning(f"Could not read {fpath}: {e}")
        return None

    def _analyze_dependencies(self, agent_def: Dict) -> Dict:
        """Scan agent source for external dependency hints."""
        source = agent_def.get("source", "")
        connectors = []
        for key in CONNECTOR_MAPPINGS:
            if key in source.lower():
                connectors.append(CONNECTOR_MAPPINGS[key]["display_name"])
        uses_openai = "openai" in source.lower() or "azure_openai" in source.lower()
        return {
            "connectors": connectors,
            "uses_openai": uses_openai,
            "manual_config_required": ["Authentication", "Environment URL"] if connectors else []
        }

    def _generate_solution(self, agent_def: Dict, analysis: Dict, **kwargs) -> Dict:
        """Generate Copilot Studio component definitions."""
        name = agent_def["name"]
        solution = {
            f"{name}_agent.mcs.yml": f"# Agent: {name}\\n# Generated by HatchRappAgent\\n",
            f"{name}_settings.mcs.yml": f"# Settings for {name}\\n",
            f"{name}_botdefinition.json": json.dumps({
                "$kind": "BotDefinition",
                "entity": {"displayName": name, "state": "Active"},
                "components": []
            }, indent=2)
        }
        for connector in analysis.get("connectors", []):
            solution[f"connector_{connector.replace(' ', '_').lower()}.json"] = json.dumps({
                "connector": connector,
                "note": "Configure connection in Power Automate"
            }, indent=2)
        return solution

    def _save_solution(self, agent_name: str, solution: Dict, output_format: str = "solution") -> str:
        """Write solution files to disk."""
        out_dir = os.path.join(self.output_path, agent_name)
        os.makedirs(out_dir, exist_ok=True)
        for filename, content in solution.items():
            fpath = os.path.join(out_dir, filename)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content if isinstance(content, str) else json.dumps(content, indent=2))
        return out_dir

    def _transpile(self, **kwargs) -> str:
        agent_name = kwargs.get("agent_name")
        if not agent_name:
            return json.dumps({"status": "error", "error": "agent_name is required"})
        agent_def = self._parse_agent(agent_name, kwargs.get("agent_file"))
        if not agent_def:
            return json.dumps({"status": "error", "error": f"Could not find agent: {agent_name}"})
        analysis = self._analyze_dependencies(agent_def)
        solution = self._generate_solution(agent_def, analysis,
                                           include_flows=kwargs.get("include_flows", True))
        out_dir = self._save_solution(agent_name, solution, kwargs.get("output_format", "solution"))
        return json.dumps({
            "status": "success",
            "agent_name": agent_name,
            "output_directory": out_dir,
            "files_generated": list(solution.keys()),
            "connectors_required": analysis.get("connectors", [])
        }, indent=2)

    def _analyze(self, **kwargs) -> str:
        agent_name = kwargs.get("agent_name")
        if not agent_name:
            return json.dumps({"status": "error", "error": "agent_name is required"})
        agent_def = self._parse_agent(agent_name, kwargs.get("agent_file"))
        if not agent_def:
            return json.dumps({"status": "error", "error": f"Could not find agent: {agent_name}"})
        analysis = self._analyze_dependencies(agent_def)
        return json.dumps({
            "status": "success",
            "agent_name": agent_name,
            "analysis": analysis,
            "connectors_available": list(CONNECTOR_MAPPINGS.keys())
        }, indent=2)

    def _preview(self, **kwargs) -> str:
        agent_name = kwargs.get("agent_name")
        if not agent_name:
            return json.dumps({"status": "error", "error": "agent_name is required"})
        agent_def = self._parse_agent(agent_name, kwargs.get("agent_file"))
        if not agent_def:
            return json.dumps({"status": "error", "error": f"Could not find agent: {agent_name}"})
        analysis = self._analyze_dependencies(agent_def)
        solution = self._generate_solution(agent_def, analysis)
        preview = {k: f"[{len(v)} chars]" if isinstance(v, str) else v for k, v in solution.items()}
        return json.dumps({
            "status": "success",
            "agent_name": agent_name,
            "preview": preview
        }, indent=2)
'''

TEMPLATE_MCS_GENERATOR = '''"""
MCSGenerator (stripped) — Generates Copilot Studio agents in MCS format.

Included with projects scaffolded for the copilot_studio target.
Generates agent.mcs.yml, settings.mcs.yml, and botdefinition.json files
suitable for import via the Copilot Studio CLI.
"""

import os
import json
import uuid
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class MCSGenerator:
    """
    Generates Copilot Studio agent configurations in MCS format.

    Configures topics correctly to prevent "I\'m sorry, I\'m not sure how to help"
    by disabling Fallback/EndOfConversation and enabling generative AI orchestration.
    """

    ACTIVE_TOPICS = [
        "Conversation Start",
        "On Error"
    ]

    DISABLED_TOPICS = [
        "Fallback",
        "End of Conversation",
        "Multiple Topics Matched",
        "Escalate",
        "Greeting",
        "Goodbye",
        "Thank you",
        "Start Over",
        "Reset Conversation",
        "Sign in",
        "Lesson 1",
        "Lesson 2",
        "Lesson 3"
    ]

    def __init__(self, template_dir: str = None):
        if template_dir is None:
            project_root = Path(__file__).parent.parent
            template_dir = project_root / "templates" / "mcs"
        self.template_dir = Path(template_dir)

    def generate_schema_name(self, name: str, prefix: str = "rapp") -> str:
        clean_name = re.sub(r\'[^a-zA-Z0-9\\s]\', \'\', name)
        clean_name = clean_name.replace(\' \', \'_\')
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}_{clean_name}_{timestamp}"

    def escape_for_yaml(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace(\'\\\\\', \'\\\\\\\\\')
        text = text.replace(\'"\', \'\\\\"\'  )
        text = text.replace(\'\\n\', \'\\\\r\\\\n\')
        return text

    def _indent_text(self, text: str, spaces: int) -> str:
        if not text:
            return ""
        indent = " " * spaces
        lines = text.split(\'\\n\')
        return \'\\n\'.join(indent + line for line in lines)

    def generate_agent_mcs_yml(
        self,
        name: str,
        instructions: str,
        conversation_starters: List[Dict[str, str]] = None
    ) -> str:
        starters = conversation_starters or []
        yaml_content = f"""kind: GptComponentMetadata
displayName: {name}
instructions: |
{self._indent_text(instructions, 2)}
"""
        if starters:
            yaml_content += "conversationStarters:\\n"
            for starter in starters:
                yaml_content += f\'  - title: "{starter.get("title", "")}"\\n\'
                yaml_content += f\'    text: "{starter.get("text", "")}"\\n\'
        return yaml_content

    def generate_settings_mcs_yml(
        self,
        name: str,
        schema_name: str,
        auth_mode: str = "Integrated",
        channels: List[str] = None
    ) -> str:
        channels = channels or ["MsTeams"]
        yaml_content = f"""displayName: {name}
schemaName: {schema_name}
authenticationMode: {auth_mode}

gPTSettings:
  defaultSchemaName: {schema_name}.gpt.default

aISettings:
  useModelKnowledge: true
  isSemanticSearchEnabled: true
  isFileAnalysisEnabled: true
  contentModeration: Medium
  optInUseLatestModels: true
  generativeAnswersEnabled: true
  boostedConversationsEnabled: true

settings:
  orchestrationType: Generative

channels:
"""
        for channel in channels:
            yaml_content += f"  - channelId: {channel}\\n"
        return yaml_content

    def generate_bot_definition(
        self,
        name: str,
        schema_name: str,
        instructions: str,
        conversation_starters: List[Dict[str, str]] = None,
        publisher: str = "DefaultPublisher",
        bot_id: str = None
    ) -> Dict[str, Any]:
        bot_id = bot_id or str(uuid.uuid4())
        starters = conversation_starters or []

        gpt_id = str(uuid.uuid4())
        conv_start_id = str(uuid.uuid4())
        on_error_id = str(uuid.uuid4())
        fallback_id = str(uuid.uuid4())
        end_conv_id = str(uuid.uuid4())
        escalate_id = str(uuid.uuid4())
        multi_topics_id = str(uuid.uuid4())
        greeting_id = str(uuid.uuid4())
        goodbye_id = str(uuid.uuid4())

        starters_yaml = ""
        for starter in starters:
            starters_yaml += f"  - title: {starter.get(\'title\', \'\')}\\r\\n"
            starters_yaml += f"    text: {starter.get(\'text\', \'\')}\\r\\n"

        escaped_instructions = self.escape_for_yaml(instructions)

        components = [
            {
                "$kind": "GptComponent",
                "displayName": name,
                "id": gpt_id,
                "parentBotId": bot_id,
                "shareContext": {"$kind": "ContentShareContext"},
                "state": "Active",
                "status": "Active",
                "publisherUniqueName": publisher,
                "schemaName": f"{schema_name}.gpt.default",
                "metadata": f"kind: GptComponentMetadata\\r\\ndisplayName: {name}\\r\\ninstructions: |\\r\\n{self._indent_text(escaped_instructions, 2)}\\r\\nconversationStarters:\\r\\n{starters_yaml}"
            },
            {
                "$kind": "DialogComponent",
                "displayName": "Conversation Start",
                "id": conv_start_id,
                "parentBotId": bot_id,
                "shareContext": {"$kind": "ContentShareContext"},
                "state": "Active",
                "status": "Active",
                "publisherUniqueName": publisher,
                "schemaName": f"{schema_name}.topic.ConversationStart",
                "dialog": (
                    "kind: AdaptiveDialog\\r\\nbeginDialog:\\r\\n"
                    "  kind: OnConversationStart\\r\\n"
                    "  id: main\\r\\n"
                    "  actions:\\r\\n"
                    "    - kind: SetVariable\\r\\n"
                    "      id: setVariable_initHistory\\r\\n"
                    "      variable: Global.VarConversationHistory\\r\\n"
                    \'      value: "\\\\\\\"[]\\\\\\""\\r\\n\'
                )
            },
            {
                "$kind": "DialogComponent",
                "displayName": "On Error",
                "id": on_error_id,
                "parentBotId": bot_id,
                "shareContext": {"$kind": "ContentShareContext"},
                "state": "Active",
                "status": "Active",
                "publisherUniqueName": publisher,
                "schemaName": f"{schema_name}.topic.OnError",
                "dialog": "kind: AdaptiveDialog\\r\\nstartBehavior: UseLatestPublishedContentAndCancelOtherTopics\\r\\nbeginDialog:\\r\\n  kind: OnError\\r\\n  id: main\\r\\n  actions:\\r\\n    - kind: SendActivity\\r\\n      id: sendMessage_error\\r\\n      activity: I encountered an issue processing your request. Please try again.\\r\\n"
            },
            {
                "$kind": "DialogComponent",
                "displayName": "Fallback",
                "id": fallback_id,
                "parentBotId": bot_id,
                "shareContext": {"$kind": "ContentShareContext"},
                "state": "Inactive",
                "status": "Inactive",
                "publisherUniqueName": publisher,
                "schemaName": f"{schema_name}.topic.Fallback",
                "dialog": "kind: AdaptiveDialog\\r\\nbeginDialog:\\r\\n  kind: OnUnknownIntent\\r\\n  id: main\\r\\n  actions: []\\r\\n"
            },
            {
                "$kind": "DialogComponent",
                "displayName": "End of Conversation",
                "id": end_conv_id,
                "parentBotId": bot_id,
                "shareContext": {"$kind": "ContentShareContext"},
                "state": "Inactive",
                "status": "Inactive",
                "publisherUniqueName": publisher,
                "schemaName": f"{schema_name}.topic.EndofConversation",
                "dialog": "kind: AdaptiveDialog\\r\\nbeginDialog:\\r\\n  kind: OnSystemRedirect\\r\\n  id: main\\r\\n  actions: []\\r\\n"
            },
            {
                "$kind": "DialogComponent",
                "displayName": "Escalate",
                "id": escalate_id,
                "parentBotId": bot_id,
                "shareContext": {"$kind": "ContentShareContext"},
                "state": "Inactive",
                "status": "Inactive",
                "publisherUniqueName": publisher,
                "schemaName": f"{schema_name}.topic.Escalate",
                "dialog": "kind: AdaptiveDialog\\r\\nbeginDialog:\\r\\n  kind: OnEscalate\\r\\n  id: main\\r\\n  actions: []\\r\\n"
            },
            {
                "$kind": "DialogComponent",
                "displayName": "Multiple Topics Matched",
                "id": multi_topics_id,
                "parentBotId": bot_id,
                "shareContext": {"$kind": "ContentShareContext"},
                "state": "Inactive",
                "status": "Inactive",
                "publisherUniqueName": publisher,
                "schemaName": f"{schema_name}.topic.MultipleTopicsMatched",
                "dialog": "kind: AdaptiveDialog\\r\\nbeginDialog:\\r\\n  kind: OnSelectIntent\\r\\n  id: main\\r\\n  actions: []\\r\\n"
            },
            {
                "$kind": "DialogComponent",
                "displayName": "Greeting",
                "id": greeting_id,
                "parentBotId": bot_id,
                "shareContext": {"$kind": "ContentShareContext"},
                "state": "Inactive",
                "status": "Inactive",
                "publisherUniqueName": publisher,
                "schemaName": f"{schema_name}.topic.Greeting",
                "dialog": "kind: AdaptiveDialog\\r\\nbeginDialog:\\r\\n  kind: OnRecognizedIntent\\r\\n  id: main\\r\\n  intent:\\r\\n    displayName: Greeting\\r\\n    triggerQueries:\\r\\n      - Hello\\r\\n      - Hi\\r\\n  actions: []\\r\\n"
            },
            {
                "$kind": "DialogComponent",
                "displayName": "Goodbye",
                "id": goodbye_id,
                "parentBotId": bot_id,
                "shareContext": {"$kind": "ContentShareContext"},
                "state": "Inactive",
                "status": "Inactive",
                "publisherUniqueName": publisher,
                "schemaName": f"{schema_name}.topic.Goodbye",
                "dialog": "kind: AdaptiveDialog\\r\\nbeginDialog:\\r\\n  kind: OnRecognizedIntent\\r\\n  id: main\\r\\n  intent:\\r\\n    displayName: Goodbye\\r\\n    triggerQueries:\\r\\n      - Bye\\r\\n      - Goodbye\\r\\n  actions: []\\r\\n"
            }
        ]

        entity = {
            "$kind": "BotEntity",
            "displayName": name,
            "schemaName": schema_name,
            "cdsBotId": bot_id,
            "accessControlPolicy": "GroupMembership",
            "authenticationMode": "Integrated",
            "authenticationTrigger": "Always",
            "configuration": {
                "$kind": "BotConfiguration",
                "channels": [
                    {"$kind": "ChannelDefinition", "channelId": "MsTeams"}
                ],
                "gPTSettings": {
                    "$kind": "GPTSettings",
                    "defaultSchemaName": f"{schema_name}.gpt.default"
                },
                "isLightweightBot": False,
                "aISettings": {
                    "$kind": "AISettings",
                    "useModelKnowledge": True,
                    "isSemanticSearchEnabled": True,
                    "isFileAnalysisEnabled": True,
                    "contentModeration": "Medium",
                    "optInUseLatestModels": True,
                    "generativeAnswersEnabled": True,
                    "boostedConversationsEnabled": True
                },
                "settings": {
                    "orchestrationType": "Generative"
                }
            },
            "language": 1033,
            "runtimeProvider": "PowerVirtualAgents",
            "state": "Active",
            "status": 1
        }

        return {
            "$kind": "BotDefinition",
            "components": components,
            "entity": entity
        }

    def save_mcs_files(
        self,
        output_dir: str,
        name: str,
        instructions: str,
        conversation_starters: List[Dict[str, str]] = None,
        schema_name: str = None
    ) -> str:
        output_path = Path(output_dir)
        schema_name = schema_name or self.generate_schema_name(name)

        (output_path / "topics").mkdir(parents=True, exist_ok=True)
        (output_path / ".mcs").mkdir(parents=True, exist_ok=True)

        agent_yml = self.generate_agent_mcs_yml(name, instructions, conversation_starters)
        (output_path / "agent.mcs.yml").write_text(agent_yml, encoding=\'utf-8\')

        settings_yml = self.generate_settings_mcs_yml(name, schema_name)
        (output_path / "settings.mcs.yml").write_text(settings_yml, encoding=\'utf-8\')

        bot_def = self.generate_bot_definition(
            name=name,
            schema_name=schema_name,
            instructions=instructions,
            conversation_starters=conversation_starters
        )
        (output_path / ".mcs" / "botdefinition.json").write_text(
            json.dumps(bot_def, indent=2),
            encoding=\'utf-8\'
        )

        return str(output_path)


__all__ = [\'MCSGenerator\']
'''


# =============================================================================
# AGENT CLASS
# =============================================================================

class HatchRappAgent(BasicAgent):
    def __init__(self):
        self.name = 'HatchRapp'
        self.metadata = {
            "name": self.name,
            "description": (
                "Hatches a new RAPP project — scaffolds an Azure Functions or Copilot Studio "
                "native AI agent backend with memory agents, local testing, and Azure deployment. "
                "Use when the user wants to create, test, or deploy a new RAPP."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["scaffold", "test_local", "deploy", "status", "open_in_vscode"],
                        "description": "Action to perform on the RAPP project."
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Name for the project (used as directory name). Defaults to 'my_rapp'."
                    },
                    "target": {
                        "type": "string",
                        "enum": ["azure_functions", "copilot_studio"],
                        "description": (
                            "Deployment target. 'azure_functions' for Azure Function App backend, "
                            "'copilot_studio' for Copilot Studio native agents. "
                            "Defaults to 'azure_functions'."
                        )
                    }
                },
                "required": ["action"]
            }
        }
        super().__init__(name=self.name, metadata=self.metadata)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def perform(self, **kwargs) -> str:
        action = kwargs.get("action", "")
        raw_name = kwargs.get("project_name", "my_rapp") or "my_rapp"
        project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', raw_name)
        target = kwargs.get("target", "azure_functions") or "azure_functions"

        if action == "scaffold":
            return self._scaffold(project_name, target)
        elif action == "test_local":
            return self._test_local(project_name)
        elif action == "deploy":
            return self._deploy(project_name, target)
        elif action == "status":
            return self._status(project_name)
        elif action == "open_in_vscode":
            return self._open_in_vscode(project_name)
        else:
            return f"Unknown action '{action}'. Valid actions: scaffold, test_local, deploy, status, open_in_vscode"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _output_dir(self, project_name: str) -> str:
        return os.path.join(
            os.path.expanduser("~"),
            ".brainstem_data",
            "hatched_rapps",
            project_name
        )

    def _write_file(self, path: str, content: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    # ------------------------------------------------------------------
    # scaffold
    # ------------------------------------------------------------------

    def _scaffold(self, project_name: str, target: str) -> str:
        output_dir = self._output_dir(project_name)

        if os.path.exists(output_dir):
            return (
                f"Error: Project '{project_name}' already exists at {output_dir}.\n"
                f"Use action='status' to inspect it, or choose a different project_name."
            )

        try:
            # Prefer copying from rapp_swarm/ in the repo (source of truth)
            # Fall back to inline templates if not available
            brainstem_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            repo_root = os.path.dirname(brainstem_dir)
            swarms_src = os.path.join(repo_root, "rapp_swarm")
            use_repo = os.path.isfile(os.path.join(swarms_src, "function_app.py"))

            if use_repo:
                self._scaffold_from_repo(output_dir, swarms_src, target)
            else:
                self._scaffold_from_templates(output_dir, target)

            # Try to copy azuredeploy.json from the kody-w/RAPP repo
            # Strip repo-specific references so the template is generic
            brainstem_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            arm_src = os.path.join(os.path.dirname(brainstem_dir), "azuredeploy.json")
            if os.path.exists(arm_src):
                arm_dst = os.path.join(output_dir, "azuredeploy.json")
                with open(arm_src, "r") as f:
                    arm_content = f.read()
                # Replace repo-specific references with generic placeholders
                # so the scaffolded template points at the user's own org/repo
                # instead of the canonical kody-w/RAPP.
                arm_content = arm_content.replace(
                    "kody-w/RAPP", "<your-org>/<your-repo>"
                )
                arm_content = arm_content.replace("kody-w", "<your-org>")
                with open(arm_dst, "w") as f:
                    f.write(arm_content)
                arm_note = f"\n  azuredeploy.json   (copied from kody-w/RAPP)"
            else:
                arm_note = ""

        except Exception as e:
            return f"Error scaffolding project: {e}"

        # Build next steps based on target
        if target == "copilot_studio":
            next_steps = (
                "Next steps (Copilot Studio target):\n"
                "  1. Copy local.settings.template.json to local.settings.json and fill in your values.\n"
                "  2. Run: HatchRapp action=test_local to verify the Function App locally.\n"
                "  3. Use CopilotStudioTranspiler agent to convert agents to MCS format.\n"
                "  4. Import the generated .mcs.yml files via Copilot Studio CLI:\n"
                "       pac copilot import --environment <env-url> --path <mcs-dir>\n"
                "  5. Run: HatchRapp action=deploy project_name=" + project_name + " target=copilot_studio\n"
                "     for a full deployment guide."
            )
        else:
            next_steps = (
                "Next steps (Azure Functions target):\n"
                "  1. Copy local.settings.template.json to local.settings.json and fill in your values.\n"
                "  2. Install Azure Functions Core Tools if not already:\n"
                "       npm install -g azure-functions-core-tools@4\n"
                "  3. Create a Python virtual environment and install dependencies:\n"
                "       cd " + output_dir + "\n"
                "       python -m venv .venv && source .venv/bin/activate\n"
                "       pip install -r requirements.txt\n"
                "  4. Run: HatchRapp action=test_local project_name=" + project_name + "\n"
                "  5. When ready, run: HatchRapp action=deploy project_name=" + project_name + "\n"
                "     for Azure deployment instructions."
            )

        target_label = "Azure Functions" if target == "azure_functions" else "Copilot Studio"
        return (
            f"Project '{project_name}' scaffolded successfully ({target_label} target).\n"
            f"Location: {output_dir}\n\n"
            f"Files created:\n"
            f"  function_app.py\n"
            f"  host.json\n"
            f"  requirements.txt\n"
            f"  .funcignore\n"
            f"  local.settings.template.json{arm_note}\n"
            f"  agents/__init__.py\n"
            f"  agents/basic_agent.py\n"
            f"  agents/save_memory_agent.py\n"
            f"  agents/recall_memory_agent.py\n"
            + (
                "  agents/copilot_studio_transpiler_agent.py\n"
                if target == "copilot_studio" else ""
            )
            + "  utils/__init__.py\n"
            "  utils/result.py\n"
            "  utils/storage_factory.py\n"
            "  utils/local_file_storage.py\n"
            "  utils/environment.py\n"
            + (
                "  utils/mcs_generator.py\n"
                if target == "copilot_studio" else ""
            )
            + f"\n{next_steps}"
        )

    # ------------------------------------------------------------------
    # scaffold helpers
    # ------------------------------------------------------------------

    def _scaffold_from_repo(self, output_dir: str, src: str, target: str):
        """Copy files directly from rapp_swarm/ in the repo."""
        # Files to always copy
        always = [
            "function_app.py", "host.json", "requirements.txt",
            ".funcignore", "local.settings.template.json",
            "agents/__init__.py", "agents/basic_agent.py",
            "agents/save_memory_agent.py", "agents/recall_memory_agent.py",
            "utils/__init__.py", "utils/result.py", "utils/storage_factory.py",
            "utils/local_file_storage.py", "utils/environment.py",
        ]
        copilot_only = [
            "agents/copilot_studio_transpiler_agent.py",
            "utils/mcs_generator.py",
        ]
        to_copy = always + (copilot_only if target == "copilot_studio" else [])

        for rel in to_copy:
            src_path = os.path.join(src, rel)
            dst_path = os.path.join(output_dir, rel)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
            else:
                # Fall back to inline template if file missing from repo
                template_map = {
                    "function_app.py": TEMPLATE_FUNCTION_APP,
                    "host.json": TEMPLATE_HOST_JSON,
                    "requirements.txt": TEMPLATE_REQUIREMENTS,
                    ".funcignore": TEMPLATE_FUNCIGNORE,
                    "local.settings.template.json": TEMPLATE_LOCAL_SETTINGS,
                    "agents/__init__.py": TEMPLATE_AGENTS_INIT,
                    "agents/basic_agent.py": TEMPLATE_BASIC_AGENT,
                    # Legacy ContextMemory/ManageMemory templates were deleted —
                    # save_memory_agent.py and recall_memory_agent.py cover the
                    # same surface with cleaner names. The scaffolder now relies
                    # on copying from the repo (see rapp_brainstem/agents/).
                    "agents/copilot_studio_transpiler_agent.py": TEMPLATE_COPILOT_TRANSPILER_AGENT,
                    "utils/__init__.py": TEMPLATE_UTILS_INIT,
                    "utils/result.py": TEMPLATE_RESULT,
                    "utils/storage_factory.py": TEMPLATE_STORAGE_FACTORY,
                    "utils/local_file_storage.py": TEMPLATE_LOCAL_FILE_STORAGE,
                    "utils/environment.py": TEMPLATE_ENVIRONMENT,
                    "utils/mcs_generator.py": TEMPLATE_MCS_GENERATOR,
                }
                content = template_map.get(rel, "")
                self._write_file(dst_path, content)

    def _scaffold_from_templates(self, output_dir: str, target: str):
        """Write files from inline template constants (standalone fallback)."""
        agents_dir = os.path.join(output_dir, "agents")
        utils_dir = os.path.join(output_dir, "utils")
        os.makedirs(agents_dir, exist_ok=True)
        os.makedirs(utils_dir, exist_ok=True)

        # Root files
        self._write_file(os.path.join(output_dir, "function_app.py"), TEMPLATE_FUNCTION_APP)
        self._write_file(os.path.join(output_dir, "host.json"), TEMPLATE_HOST_JSON)
        self._write_file(os.path.join(output_dir, "requirements.txt"), TEMPLATE_REQUIREMENTS)
        self._write_file(os.path.join(output_dir, ".funcignore"), TEMPLATE_FUNCIGNORE)
        self._write_file(
            os.path.join(output_dir, "local.settings.template.json"),
            TEMPLATE_LOCAL_SETTINGS
        )

        # agents/
        self._write_file(os.path.join(agents_dir, "__init__.py"), TEMPLATE_AGENTS_INIT)
        self._write_file(os.path.join(agents_dir, "basic_agent.py"), TEMPLATE_BASIC_AGENT)
        self._write_file(
            os.path.join(agents_dir, "context_memory_agent.py"),
            TEMPLATE_CONTEXT_MEMORY_AGENT
        )
        self._write_file(
            os.path.join(agents_dir, "manage_memory_agent.py"),
            TEMPLATE_MANAGE_MEMORY_AGENT
        )

        # utils/
        self._write_file(os.path.join(utils_dir, "__init__.py"), TEMPLATE_UTILS_INIT)
        self._write_file(os.path.join(utils_dir, "result.py"), TEMPLATE_RESULT)
        self._write_file(os.path.join(utils_dir, "storage_factory.py"), TEMPLATE_STORAGE_FACTORY)
        self._write_file(
            os.path.join(utils_dir, "local_file_storage.py"),
            TEMPLATE_LOCAL_FILE_STORAGE
        )
        self._write_file(os.path.join(utils_dir, "environment.py"), TEMPLATE_ENVIRONMENT)

        # Copilot Studio extras
        if target == "copilot_studio":
            self._write_file(
                os.path.join(agents_dir, "copilot_studio_transpiler_agent.py"),
                TEMPLATE_COPILOT_TRANSPILER_AGENT
            )
            self._write_file(
                os.path.join(utils_dir, "mcs_generator.py"),
                TEMPLATE_MCS_GENERATOR
            )

    # ------------------------------------------------------------------
    # test_local
    # ------------------------------------------------------------------

    def _test_local(self, project_name: str) -> str:
        output_dir = self._output_dir(project_name)

        if not os.path.exists(output_dir):
            return (
                f"Error: Project '{project_name}' not found at {output_dir}.\n"
                f"Run: HatchRapp action=scaffold project_name={project_name}"
            )

        # Check func CLI
        func_path = shutil.which("func")
        if not func_path:
            return (
                "Error: Azure Functions Core Tools ('func') not found in PATH.\n"
                "Install with: npm install -g azure-functions-core-tools@4\n"
                "Then re-run: HatchRapp action=test_local project_name=" + project_name
            )

        # Check local.settings.json
        settings_path = os.path.join(output_dir, "local.settings.json")
        if not os.path.exists(settings_path):
            template_path = os.path.join(output_dir, "local.settings.template.json")
            return (
                f"Error: local.settings.json not found in {output_dir}.\n"
                f"Copy the template and fill in your values:\n"
                f"  cp {template_path} {settings_path}\n"
                f"Then edit {settings_path} with your Azure OpenAI credentials."
            )

        # Start func start
        try:
            proc = subprocess.Popen(
                [func_path, "start"],
                cwd=output_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
        except Exception as e:
            return f"Error starting func: {e}"

        # Wait up to 15 seconds for "Host started"
        deadline = time.time() + 15
        output_lines = []
        host_started = False

        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue
            output_lines.append(line.rstrip())
            if "Host started" in line or "Functions:" in line:
                host_started = True
                break

        if host_started:
            return (
                f"Azure Functions host started for '{project_name}'.\n"
                f"Endpoint: http://localhost:7071/api/rapp_function\n\n"
                f"Test with curl:\n"
                f"  curl -X POST http://localhost:7071/api/rapp_function \\\n"
                f"    -H 'Content-Type: application/json' \\\n"
                f"    -d '{{\"user_input\": \"Hello, what can you do?\", \"conversation_history\": []}}'\n\n"
                f"Host output (last few lines):\n"
                + "\n".join(output_lines[-10:])
                + f"\n\nProcess PID: {proc.pid} (running in background)"
            )
        else:
            proc.terminate()
            return (
                f"Warning: func host did not report 'Host started' within 15 seconds.\n"
                f"Output so far:\n"
                + "\n".join(output_lines[-20:])
                + "\n\nThe process has been terminated. Check for errors above.\n"
                "Common issues:\n"
                "  - Missing or invalid local.settings.json values\n"
                "  - Port 7071 already in use\n"
                "  - Python virtual environment not activated\n"
                "  - Missing pip packages (run: pip install -r requirements.txt)"
            )

    # ------------------------------------------------------------------
    # deploy
    # ------------------------------------------------------------------

    def _deploy(self, project_name: str, target: str) -> str:
        output_dir = self._output_dir(project_name)

        if not os.path.exists(output_dir):
            return (
                f"Error: Project '{project_name}' not found at {output_dir}.\n"
                f"Run: HatchRapp action=scaffold project_name={project_name}"
            )

        if target == "copilot_studio":
            return (
                f"Copilot Studio Deployment Guide for '{project_name}'\n"
                f"Project path: {output_dir}\n\n"
                "Step 1 — Install Copilot Studio CLI (pac)\n"
                "  winget install Microsoft.PowerAppsCLI\n"
                "  # or: dotnet tool install -g Microsoft.PowerApps.CLI\n\n"
                "Step 2 — Authenticate\n"
                "  pac auth create --environment <your-environment-url>\n\n"
                "Step 3 — Transpile RAPP agents to MCS format\n"
                "  In the brainstem, ask: 'Transpile my agents to Copilot Studio format'\n"
                "  (Uses CopilotStudioTranspiler agent in agents/ directory)\n\n"
                "Step 4 — Import to Copilot Studio\n"
                "  pac copilot import \\\n"
                "    --environment <your-environment-url> \\\n"
                "    --path <path-to-mcs-output-dir>\n\n"
                "Step 5 — Publish\n"
                "  pac copilot publish --environment <your-environment-url>\n\n"
                "Notes:\n"
                "  - MCS files are generated by CopilotStudioTranspilerAgent into agents/transpiled/\n"
                "  - Review botdefinition.json before importing\n"
                "  - The MCSGenerator in utils/mcs_generator.py disables Fallback/EndOfConversation\n"
                "    topics to prevent 'I'm sorry, I'm not sure how to help' messages\n"
                "  - useModelKnowledge: true is required for generative AI to handle open-ended queries"
            )
        else:
            # Azure Functions
            arm_path = os.path.join(output_dir, "azuredeploy.json")
            arm_note = (
                f"  ARM template: {arm_path}\n"
                "  Deploy with:\n"
                "    az deployment group create \\\n"
                "      --resource-group <your-rg> \\\n"
                "      --template-file azuredeploy.json \\\n"
                "      --parameters functionAppName=<app-name> storageAccountName=<storage>\n"
            ) if os.path.exists(arm_path) else (
                "  (azuredeploy.json not found — deploy manually via Azure Portal or az CLI)\n"
            )

            return (
                f"Azure Functions Deployment Guide for '{project_name}'\n"
                f"Project path: {output_dir}\n\n"
                "Prerequisites:\n"
                "  - Azure CLI: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli\n"
                "  - Azure Functions Core Tools v4\n"
                "  - An Azure subscription with a resource group\n\n"
                "Step 1 — Login to Azure\n"
                "  az login\n"
                "  az account set --subscription <your-subscription-id>\n\n"
                "Step 2 — Create resources (skip if using ARM template)\n"
                "  az group create --name <your-rg> --location eastus\n"
                "  az storage account create --name <storage> --resource-group <your-rg> --sku Standard_LRS\n"
                "  az functionapp create \\\n"
                "    --resource-group <your-rg> \\\n"
                "    --consumption-plan-location eastus \\\n"
                "    --runtime python \\\n"
                "    --runtime-version 3.11 \\\n"
                "    --functions-version 4 \\\n"
                "    --name <app-name> \\\n"
                "    --storage-account <storage>\n\n"
                "Step 3 — Deploy with ARM template (optional)\n"
                + arm_note
                + "\nStep 4 — Configure app settings\n"
                "  az functionapp config appsettings set \\\n"
                "    --name <app-name> --resource-group <your-rg> \\\n"
                "    --settings \\\n"
                "      AZURE_OPENAI_API_KEY=<key> \\\n"
                "      AZURE_OPENAI_ENDPOINT=https://<service>.openai.azure.com/ \\\n"
                "      AZURE_OPENAI_DEPLOYMENT_NAME=<deployment> \\\n"
                "      AZURE_STORAGE_ACCOUNT_NAME=<storage> \\\n"
                "      AZURE_FILES_SHARE_NAME=<share>\n\n"
                "Step 5 — Publish code\n"
                f"  cd {output_dir}\n"
                "  func azure functionapp publish <app-name> --python\n\n"
                "Step 6 — Get function URL\n"
                "  az functionapp function show \\\n"
                "    --name <app-name> --resource-group <your-rg> \\\n"
                "    --function-name rapp_function --query invokeUrlTemplate -o tsv\n\n"
                "Your endpoint will be:\n"
                "  https://<app-name>.azurewebsites.net/api/rapp_function?code=<function-key>"
            )

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------

    def _status(self, project_name: str) -> str:
        output_dir = self._output_dir(project_name)

        if not os.path.exists(output_dir):
            return (
                f"Project '{project_name}' does not exist.\n"
                f"Expected location: {output_dir}\n"
                f"Run: HatchRapp action=scaffold project_name={project_name} to create it."
            )

        # Walk and collect all files
        all_files = []
        for root, dirs, files in os.walk(output_dir):
            # Skip hidden and pycache dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for fname in sorted(files):
                rel = os.path.relpath(os.path.join(root, fname), output_dir)
                all_files.append(rel)

        has_settings = os.path.exists(os.path.join(output_dir, "local.settings.json"))
        has_venv = os.path.exists(os.path.join(output_dir, ".venv"))

        settings_note = (
            "local.settings.json: PRESENT (ready for local testing)"
            if has_settings
            else "local.settings.json: MISSING (copy from local.settings.template.json)"
        )

        lines = [
            f"Status for project '{project_name}'",
            f"Location: {output_dir}",
            "",
            settings_note,
            f"Virtual environment: {'PRESENT' if has_venv else 'NOT CREATED (run: python -m venv .venv)'}",
            "",
            f"Files ({len(all_files)} total):",
        ]
        for f in all_files:
            lines.append(f"  {f}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # open_in_vscode
    # ------------------------------------------------------------------

    def _open_in_vscode(self, project_name: str) -> str:
        output_dir = self._output_dir(project_name)

        if not os.path.exists(output_dir):
            return (
                f"Project '{project_name}' does not exist at {output_dir}.\n"
                f"Run: HatchRapp action=scaffold project_name={project_name} first."
            )

        return (
            f"To open '{project_name}' in VS Code, run:\n\n"
            f"  code \"{output_dir}\"\n\n"
            f"Or if 'code' is not in your PATH:\n"
            f"  open -a 'Visual Studio Code' \"{output_dir}\"  # macOS\n"
            f"  start code \"{output_dir}\"                    # Windows"
        )
