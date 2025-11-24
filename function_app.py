import azure.functions as func
import logging
import json
import os
import importlib
import importlib.util
import inspect
import sys
import re
from agents.basic_agent import BasicAgent
import uuid
from openai import AzureOpenAI
from datetime import datetime
import time
from utils.azure_file_storage import AzureFileStorageManager, safe_json_loads

# Default GUID to use when no specific user GUID is provided
# Memorable pattern related to "copilot" that follows UUID format rules
DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"

def ensure_string_content(message):
    """
    Ensures message content is converted to a string regardless of input type.
    Handles all edge cases including None, undefined, or missing content.
    """
    # Handle None or non-dict messages
    if message is None:
        return {"role": "user", "content": ""}
        
    if not isinstance(message, dict):
        # Convert whatever we have to string
        return {"role": "user", "content": str(message) if message is not None else ""}
    
    # Create a copy to avoid modifying the original
    message = message.copy()
    
    # Ensure we have a role
    if 'role' not in message:
        message['role'] = 'user'
    
    # Handle content - check if it exists and is not None
    if 'content' in message:
        content = message['content']
        # Convert to string, handling None case
        message['content'] = str(content) if content is not None else ''
    else:
        # No content key at all
        message['content'] = ''
    
    return message

def ensure_string_function_args(function_call):
    """
    Ensures function call arguments are properly stringified.
    Handles None and edge cases.
    """
    if not function_call:
        return None
    
    # Check if function_call has arguments attribute
    if not hasattr(function_call, 'arguments'):
        return None
        
    if function_call.arguments is None:
        return None
        
    if isinstance(function_call.arguments, (dict, list)):
        return json.dumps(function_call.arguments)
    
    return str(function_call.arguments)

def build_cors_response(origin):
    """
    Builds CORS response headers.
    Safely handles None origin.
    """
    return {
        "Access-Control-Allow-Origin": str(origin) if origin else "*",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "86400",
    }

def load_agents_from_folder(user_guid=None):
    agents_directory = os.path.join(os.path.dirname(__file__), "agents")
    files_in_agents_directory = os.listdir(agents_directory)
    agent_files = [f for f in files_in_agents_directory if f.endswith(".py") and f not in ["__init__.py", "basic_agent.py"]]

    declared_agents = {}
    for file in agent_files:
        try:
            module_name = file[:-3]
            module = importlib.import_module(f'agents.{module_name}')
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BasicAgent) and obj is not BasicAgent:
                    agent_instance = obj()
                    declared_agents[agent_instance.name] = agent_instance
        except Exception as e:
            logging.error(f"Error loading agent {file}: {str(e)}")
            continue

    storage_manager = AzureFileStorageManager()

    # Load enabled agents list for this GUID
    enabled_agents = None
    if user_guid:
        try:
            agent_config_path = f"agent_config/{user_guid}"
            agent_config_content = storage_manager.read_file(agent_config_path, 'enabled_agents.json')
            if agent_config_content:
                enabled_agents = json.loads(agent_config_content)
        except Exception as e:
            logging.info(f"No agent config found for GUID {user_guid}, loading all agents: {str(e)}")

    try:
        agent_files = storage_manager.list_files('agents')

        for file in agent_files:
            if not file.name.endswith('_agent.py'):
                continue

            # Apply filter if enabled_agents list exists
            if enabled_agents is not None:
                if file.name not in enabled_agents:
                    continue

            try:
                file_content = storage_manager.read_file('agents', file.name)
                if file_content is None:
                    continue

                temp_dir = "/tmp/agents"
                os.makedirs(temp_dir, exist_ok=True)
                temp_file = f"{temp_dir}/{file.name}"

                with open(temp_file, 'w') as f:
                    f.write(file_content)

                if temp_dir not in sys.path:
                    sys.path.append(temp_dir)

                module_name = file.name[:-3]
                spec = importlib.util.spec_from_file_location(module_name, temp_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, BasicAgent) and
                        obj is not BasicAgent):
                        agent_instance = obj()
                        declared_agents[agent_instance.name] = agent_instance

                os.remove(temp_file)

            except Exception as e:
                logging.error(f"Error loading agent {file.name} from Azure File Share: {str(e)}")
                continue

    except Exception as e:
        logging.error(f"Error loading agents from Azure File Share: {str(e)}")

    # Load multi-agents from multi_agents folder
    try:
        multi_agent_files = storage_manager.list_files('multi_agents')

        for file in multi_agent_files:
            if not file.name.endswith('_agent.py'):
                continue

            # Apply filter if enabled_agents list exists
            if enabled_agents is not None:
                if file.name not in enabled_agents:
                    continue

            try:
                file_content = storage_manager.read_file('multi_agents', file.name)
                if file_content is None:
                    continue

                temp_dir = "/tmp/multi_agents"
                os.makedirs(temp_dir, exist_ok=True)
                temp_file = f"{temp_dir}/{file.name}"

                with open(temp_file, 'w') as f:
                    f.write(file_content)

                if temp_dir not in sys.path:
                    sys.path.append(temp_dir)

                # Also add the parent directory to sys.path so imports work
                parent_dir = "/tmp"
                if parent_dir not in sys.path:
                    sys.path.append(parent_dir)

                module_name = file.name[:-3]
                spec = importlib.util.spec_from_file_location(f"multi_agents.{module_name}", temp_file)
                module = importlib.util.module_from_spec(spec)
                
                # Create the multi_agents package if it doesn't exist
                import types
                if 'multi_agents' not in sys.modules:
                    multi_agents_module = types.ModuleType('multi_agents')
                    sys.modules['multi_agents'] = multi_agents_module
                
                # Add the module to the multi_agents package
                sys.modules[f"multi_agents.{module_name}"] = module
                spec.loader.exec_module(module)

                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, BasicAgent) and
                        obj is not BasicAgent):
                        agent_instance = obj()
                        declared_agents[agent_instance.name] = agent_instance
                        logging.info(f"Loaded multi-agent: {agent_instance.name}")

                os.remove(temp_file)

            except Exception as e:
                logging.error(f"Error loading multi-agent {file.name} from Azure File Share: {str(e)}")
                continue

    except Exception as e:
        logging.error(f"Error loading multi-agents from Azure File Share: {str(e)}")

    return declared_agents

class Assistant:
    def __init__(self, declared_agents):
        self.config = {
            'assistant_name': str(os.environ.get('ASSISTANT_NAME', 'RAPP')),
            'characteristic_description': str(os.environ.get('CHARACTERISTIC_DESCRIPTION', 'Rapid Agent Prototyping Platform - A flexible AI agent framework'))
        }

        try:
            self.client = AzureOpenAI(
                api_key=os.environ['AZURE_OPENAI_API_KEY'],
                api_version=os.environ['AZURE_OPENAI_API_VERSION'],
                azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT']
            )
        except TypeError:
            self.client = AzureOpenAI(
                api_key=os.environ['AZURE_OPENAI_API_KEY'],
                azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT']
            )

        self.known_agents = self.reload_agents(declared_agents)
        
        # Set the default user GUID instead of None
        self.user_guid = DEFAULT_USER_GUID
        
        self.shared_memory = None
        self.user_memory = None
        self.storage_manager = AzureFileStorageManager()

        # Initialize with the default user GUID memory
        self._initialize_context_memory(DEFAULT_USER_GUID)

    def _check_first_message_for_guid(self, conversation_history):
        """Check if the first message contains only a GUID"""
        if not conversation_history or len(conversation_history) == 0:
            return None
            
        first_message = conversation_history[0]
        if first_message.get('role') == 'user':
            content = first_message.get('content')
            if content is None:
                return None
            content = str(content).strip()
            guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
            if guid_pattern.match(content):
                return content
        return None

    def _initialize_context_memory(self, user_guid=None):
        """Initialize context memory with separate shared and user-specific memories"""
        try:
            context_memory_agent = self.known_agents.get('ContextMemory')
            if not context_memory_agent:
                self.shared_memory = "No shared context memory available."
                self.user_memory = "No specific context memory available."
                return

            # Always get shared memories with full_recall=True to ensure complete context
            self.storage_manager.set_memory_context(None)  # Reset to shared context
            self.shared_memory = str(context_memory_agent.perform(full_recall=True))

            # If user_guid provided, get user-specific memories with full_recall=True
            # If no user_guid is provided, fall back to the default GUID
            if not user_guid:
                user_guid = DEFAULT_USER_GUID

            self.storage_manager.set_memory_context(user_guid)
            self.user_memory = str(context_memory_agent.perform(user_guid=user_guid, full_recall=True))

        except Exception as e:
            logging.warning(f"Error initializing context memory: {str(e)}")
            self.shared_memory = "Context memory initialization failed."
            self.user_memory = "Context memory initialization failed."

    def _extract_demo_state_from_history(self, conversation_history):
        """
        Extract active demo state from conversation history (stateless approach).
        Returns: (demo_name, current_step, demo_steps_list) or (None, 0, None)
        """
        if not conversation_history:
            return None, 0, None

        # Look backwards through conversation for the most recent demo-related system message
        for message in reversed(conversation_history):
            if message.get('role') == 'system':
                content = str(message.get('content', ''))

                # Check for demo completion or exit
                if 'DemoCompletion' in content or 'Demo finished' in content or 'DemoExit' in content:
                    return None, 0, None

                # Check for demo activation or continuation
                # Format: "Performed Bot_342_Morning_Greeting_Demo and got result: Demo activated - Step 1 of 5"
                # Format: "Performed Bot_342_Morning_Greeting_Demo and got result: Step 2 of 5 - ..."
                match = re.search(r'Performed (\S+) and got result:.*Step (\d+) of (\d+)', content)
                if match:
                    demo_name = match.group(1)
                    current_step = int(match.group(2))
                    total_steps = int(match.group(3))

                    # Load the demo data to get all steps
                    try:
                        demo_content = self.storage_manager.read_file('demos', f'{demo_name}.json')
                        if demo_content:
                            demo_data = json.loads(demo_content)
                            demo_steps = demo_data.get('conversation_flow', [])
                            logging.info(f"Extracted demo state from history: {demo_name}, step {current_step}/{len(demo_steps)}")
                            return demo_name, current_step, demo_steps
                    except Exception as e:
                        logging.error(f"Error loading demo {demo_name}: {str(e)}")
                        return None, 0, None

        return None, 0, None

    def extract_user_guid(self, text):
        """Try to extract a GUID from user input, but only if it's the entire message"""
        if text is None:
            return None

        text_str = str(text).strip()

        # Only match if the entire message is just a GUID
        guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        match = guid_pattern.match(text_str)
        if match:
            return match.group(0)

        # Also allow labeled GUIDs for explicit behavior
        labeled_guid_pattern = re.compile(r'^guid[:=\s]+([0-9a-f-]{36})$', re.IGNORECASE)
        match = labeled_guid_pattern.match(text_str)
        if match:
            return match.group(1)

        return None

    def check_demo_trigger(self, user_message):
        """Check if user message matches any demo trigger phrases (stateless)"""
        try:
            # List all demo files
            demo_files = self.storage_manager.list_files('demos')

            user_message_lower = user_message.lower().strip()

            for file in demo_files:
                if not file.name.endswith('.json'):
                    continue

                try:
                    # Read demo file
                    demo_content = self.storage_manager.read_file('demos', file.name)
                    if not demo_content:
                        continue

                    demo_data = json.loads(demo_content)
                    trigger_phrases = demo_data.get('trigger_phrases', [])

                    # Check if user message matches any trigger phrase
                    for phrase in trigger_phrases:
                        if phrase.lower().strip() == user_message_lower:
                            # Found a match!
                            demo_name = file.name.replace('.json', '')
                            conversation_flow = demo_data.get('conversation_flow', [])

                            logging.info(f"Triggered demo: {demo_name} with {len(conversation_flow)} steps")

                            return {
                                'triggered': True,
                                'demo_name': demo_name,
                                'demo_data': demo_data,
                                'conversation_flow': conversation_flow
                            }

                except Exception as e:
                    logging.error(f"Error checking demo {file.name}: {str(e)}")
                    continue

            return {'triggered': False}

        except Exception as e:
            logging.error(f"Error in check_demo_trigger: {str(e)}")
            return {'triggered': False}

    def get_agent_metadata(self):
        agents_metadata = []
        for agent in self.known_agents.values():
            if hasattr(agent, 'metadata'):
                agents_metadata.append(agent.metadata)
        return agents_metadata

    def reload_agents(self, agent_objects):
        known_agents = {}
        if isinstance(agent_objects, dict):
            for agent_name, agent in agent_objects.items():
                if hasattr(agent, 'name'):
                    known_agents[agent.name] = agent
                else:
                    known_agents[str(agent_name)] = agent
        elif isinstance(agent_objects, list):
            for agent in agent_objects:
                if hasattr(agent, 'name'):
                    known_agents[agent.name] = agent
        else:
            logging.warning(f"Unexpected agent_objects type: {type(agent_objects)}")
        return known_agents

    def prepare_messages(self, conversation_history):
        if not isinstance(conversation_history, list):
            conversation_history = []
            
        messages = []
        current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # System message
        system_message = {
            "role": "system",
            "content": f"""
<identity>
You are an AI assistant named {str(self.config.get('assistant_name', 'Assistant'))}, part of the RAPP (Rapid Agent Prototyping Platform). You can operate via direct API, web interface, Microsoft Teams, or M365 Copilot depending on how users access you.
</identity>

<shared_memory_output>
These are memories accessible by all users of the system:
{str(self.shared_memory)}
</shared_memory_output>

<specific_memory_output>
These are memories specific to the current conversation:
{str(self.user_memory)}
</specific_memory_output>

<context_instructions>
- <shared_memory_output> represents common knowledge shared across all conversations
- <specific_memory_output> represents specific context for the current conversation
- Apply specific context with higher precedence than shared context
- Synthesize information from both contexts for comprehensive responses
</context_instructions>

<agent_usage>
IMPORTANT: You must be honest and accurate about agent usage:
- NEVER pretend or imply you've executed an agent when you haven't actually called it
- NEVER say "using my agent" unless you are actually making a function call to that agent
- NEVER fabricate success messages about data operations that haven't occurred
- If you need to perform an action and don't have the necessary agent, say so directly
- When a user requests an action, either:
  1. Call the appropriate agent and report actual results, or
  2. Say "I don't have the capability to do that" and suggest an alternative
  3. If no details are provided besides the request to run an agent, infer the necessary input parameters by "reading between the lines" of the conversation context so far
</agent_usage>

<response_format>
CRITICAL: You must structure your response in TWO distinct parts separated by the delimiter |||VOICE|||

1. FIRST PART (before |||VOICE|||): Your full formatted response
   - Use **bold** for emphasis
   - Use `code blocks` for technical content
   - Apply --- for horizontal rules to separate sections
   - Utilize > for important quotes or callouts
   - Format code with ```language syntax highlighting
   - Create numbered lists with proper indentation
   - Add personality when appropriate
   - Apply # ## ### headings for clear structure

2. SECOND PART (after |||VOICE|||): A concise voice response
   - Maximum 1-2 sentences
   - Pure conversational English with NO formatting
   - Extract only the most critical information
   - Sound like a colleague speaking casually over a cubicle wall
   - Be natural and conversational, not robotic
   - Focus on the key takeaway or action item
   - Example: "I found those Q3 sales figures - revenue's up 12 percent from last quarter." or "Sure, I'll pull up that customer data for you right now."

EXAMPLE FORMAT:
Here's the detailed analysis you requested:

**Key Findings:**
- Revenue increased by 12%
- Customer satisfaction scores improved

|||VOICE|||
Revenue's up 12 percent and customers are happier - looking good for Q3.
</response_format>
"""
        }
        messages.append(ensure_string_content(system_message))
        
        # Process conversation history - skip first message if it's just a GUID
        guid_only_first_message = self._check_first_message_for_guid(conversation_history)
        start_idx = 1 if guid_only_first_message else 0
        
        for i in range(start_idx, len(conversation_history)):
            messages.append(ensure_string_content(conversation_history[i]))
            
        return messages
    
    def get_openai_api_call(self, messages):
        try:
            # Get the deployment name from environment or use default
            deployment_name = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-deployment')
            
            response = self.client.chat.completions.create(
                model=deployment_name,
                messages=messages,
                functions=self.get_agent_metadata(),
                function_call="auto"
            )
            return response
        except Exception as e:
            logging.error(f"Error in OpenAI API call: {str(e)}")
            raise
    
    def parse_response_with_voice(self, content):
        """Parse the response to extract formatted and voice parts"""
        if not content:
            return "", ""
        
        # Split by the delimiter
        parts = content.split("|||VOICE|||")
        
        if len(parts) >= 2:
            # We have both parts
            formatted_response = parts[0].strip()
            voice_response = parts[1].strip()
        else:
            # No voice delimiter found, generate a simple voice response
            formatted_response = content.strip()
            # Extract a simple summary for voice
            sentences = formatted_response.split('.')
            if sentences:
                voice_response = sentences[0].strip() + "."
                # Remove any formatting from voice response
                voice_response = re.sub(r'\*\*|`|#|>|---|[\U00010000-\U0010ffff]|[\u2600-\u26FF]|[\u2700-\u27BF]', '', voice_response)
                voice_response = re.sub(r'\s+', ' ', voice_response).strip()
            else:
                voice_response = "I've completed your request."
        
        return formatted_response, voice_response

    def get_response(self, prompt, conversation_history, max_retries=3, retry_delay=2):
        # Check if this is a first-time initialization with just a GUID
        # or if a GUID is in the conversation history or current prompt
        guid_from_history = self._check_first_message_for_guid(conversation_history)
        guid_from_prompt = self.extract_user_guid(prompt)

        target_guid = guid_from_history or guid_from_prompt

        # Set or update the memory context if we have a GUID that's different from current
        if target_guid and target_guid != self.user_guid:
            self.user_guid = target_guid
            self._initialize_context_memory(self.user_guid)
            logging.info(f"User GUID updated to: {self.user_guid}")
        elif not self.user_guid:
            # If for some reason we don't have a user_guid, set it to the default
            self.user_guid = DEFAULT_USER_GUID
            self._initialize_context_memory(self.user_guid)
            logging.info(f"Using default User GUID: {self.user_guid}")

        # Ensure prompt is string
        prompt = str(prompt) if prompt is not None else ""

        # Skip processing if the prompt is just a GUID and we've already set the context
        if guid_from_prompt and prompt.strip() == guid_from_prompt and self.user_guid == guid_from_prompt:
            formatted = "I've successfully loaded your conversation memory. How can I assist you today?"
            voice = "I've loaded your memory - what can I help you with?"
            return formatted, voice, ""

        # Extract demo state from conversation history (stateless)
        active_demo, current_step, demo_steps = self._extract_demo_state_from_history(conversation_history)

        # Check for "exit demo" command
        if prompt.lower().strip() in ['exit demo', 'stop demo', 'end demo', 'cancel demo']:
            if active_demo:
                formatted = f"How can I help you?"
                voice = "What can I help you with?"
                return formatted, voice, f"Performed DemoExit and got result: {active_demo} terminated by user"
            else:
                formatted = "How can I help you?"
                voice = "What can I help you with?"
                return formatted, voice, ""

        # Check for demo trigger FIRST (before any LLM processing)
        trigger_result = self.check_demo_trigger(prompt)
        if trigger_result.get('triggered'):
            demo_data = trigger_result.get('demo_data', {})
            demo_name = trigger_result.get('demo_name', '')
            conversation_flow = trigger_result.get('conversation_flow', [])

            # Demo just triggered - call ScriptedDemoAgent for step 1 canned response
            total_steps = len(conversation_flow)

            # Call ScriptedDemoAgent to get the canned response for step 1
            scripted_demo_agent = self.known_agents.get('ScriptedDemo')
            if scripted_demo_agent:
                try:
                    canned_response = scripted_demo_agent.perform(
                        action='respond',
                        demo_name=demo_name,
                        user_input=prompt,
                        user_guid=self.user_guid
                    )

                    # Return clean canned response without demo meta-information
                    formatted = canned_response

                    # Extract voice from the canned response
                    voice_sentences = canned_response.split('.')[:2]
                    voice = '.'.join(voice_sentences).strip()
                    voice = re.sub(r'\*\*|`|#|>|---|[\U00010000-\U0010ffff]|[\u2600-\u26FF]|[\u2700-\u27BF]', '', voice)
                    voice = re.sub(r'\s+', ' ', voice).strip()

                    return formatted, voice, f"Performed {demo_name} and got result: Demo activated - Step 1 of {total_steps}"

                except Exception as e:
                    logging.error(f"Error calling ScriptedDemoAgent on trigger: {str(e)}")
                    # Fall back to generic activation message
                    formatted = f"I apologize, but I encountered an error retrieving the demo response. Let me help you with that request."
                    voice = f"I encountered an error, but let me help you with that."
                    return formatted, voice, f"Performed {demo_name} and got result: Demo activated - Step 1 (Error)"
            else:
                # ScriptedDemoAgent not available - use generic message
                formatted = f"Let me help you with that!"
                voice = f"Let me help you with that."
                return formatted, voice, f"Performed {demo_name} and got result: Demo activated - Step 1 of {total_steps}"

        # Check if we're in an active demo (continuing a scripted conversation)
        if active_demo and demo_steps:
            # We're continuing an active demo - call ScriptedDemoAgent to get canned response
            next_step_num = current_step + 1
            total_steps = len(demo_steps)

            if next_step_num > total_steps:
                # Demo is complete
                formatted = f"How else can I help you today?"
                voice = "What else can I help you with?"
                return formatted, voice, f"Performed DemoCompletion and got result: {active_demo} finished successfully"

            logging.info(f"Continuing demo {active_demo}: step {next_step_num}/{total_steps}")

            # Call ScriptedDemoAgent to get the canned response
            scripted_demo_agent = self.known_agents.get('ScriptedDemo')
            if scripted_demo_agent:
                try:
                    # Call the agent with the user input
                    canned_response = scripted_demo_agent.perform(
                        action='respond',
                        demo_name=active_demo,
                        user_input=prompt,
                        user_guid=self.user_guid
                    )

                    # Return clean canned response without demo meta-information
                    formatted = canned_response

                    # Extract voice from the canned response (first sentence or two)
                    voice_sentences = canned_response.split('.')[:2]
                    voice = '.'.join(voice_sentences).strip()
                    # Remove markdown formatting from voice
                    voice = re.sub(r'\*\*|`|#|>|---|[\U00010000-\U0010ffff]|[\u2600-\u26FF]|[\u2700-\u27BF]', '', voice)
                    voice = re.sub(r'\s+', ' ', voice).strip()

                    agent_log = f"Performed {active_demo} and got result: Step {next_step_num} of {total_steps} - Returned canned response"
                    return formatted, voice, agent_log

                except Exception as e:
                    logging.error(f"Error calling ScriptedDemoAgent: {str(e)}")
                    # Fall back to generic response
                    formatted = f"I apologize, but I encountered an error. Let me help you with that."
                    voice = "Sorry, I hit an error. Let me help you with that."
                    return formatted, voice, f"Performed {active_demo} and got result: Error - {str(e)}"
            else:
                # ScriptedDemoAgent not loaded
                formatted = "I'm sorry, I'm unable to access the demo script right now. How else can I help you?"
                voice = "The demo script isn't available right now. How else can I help?"
                return formatted, voice, "Performed DemoError and got result: ScriptedDemo agent not found"
        
        messages = self.prepare_messages(conversation_history)
        messages.append(ensure_string_content({"role": "user", "content": prompt}))

        agent_logs = []
        retry_count = 0
        needs_follow_up = False

        while retry_count < max_retries:
            try:
                response = self.get_openai_api_call(messages)
                assistant_msg = response.choices[0].message
                msg_contents = assistant_msg.content or ""  # Ensure content is never None

                if not assistant_msg.function_call:
                    formatted_response, voice_response = self.parse_response_with_voice(msg_contents)
                    return formatted_response, voice_response, "\n".join(map(str, agent_logs))

                agent_name = str(assistant_msg.function_call.name)
                agent = self.known_agents.get(agent_name)

                if not agent:
                    return f"Agent '{agent_name}' does not exist", "I couldn't find that agent.", ""

                # Process function call arguments
                json_data = ensure_string_function_args(assistant_msg.function_call)
                logging.info(f"JSON data before parsing: {json_data}")

                try:
                    agent_parameters = safe_json_loads(json_data)
                    
                    # Sanitize parameters - ensure none are undefined or None
                    sanitized_parameters = {}
                    for key, value in agent_parameters.items():
                        if value is None:
                            sanitized_parameters[key] = ""  # Convert None to empty string
                        else:
                            sanitized_parameters[key] = value
                    
                    # Add user_guid to agent parameters if agent accepts it
                    # Always use the current user_guid (which might be the default)
                    if agent_name in ['ManageMemory', 'ContextMemory']:
                        sanitized_parameters['user_guid'] = self.user_guid
                    
                    # Always perform agent call - no caching
                    result = agent.perform(**sanitized_parameters)
                    
                    # Ensure result is a string
                    if result is None:
                        result = "Agent completed successfully"
                    else:
                        result = str(result)
                        
                    agent_logs.append(f"Performed {agent_name} and got result: {result}")
                        
                except Exception as e:
                    return f"Error parsing parameters: {str(e)}", "I hit an error processing that.", ""

                # Add the function result to messages
                messages.append({
                    "role": "function",
                    "name": agent_name,
                    "content": result
                })
                
                # EVALUATION: Check if we need a follow-up function call
                try:
                    result_json = json.loads(result)
                    # Look for error indicators or incomplete data flags
                    needs_follow_up = False
                    if isinstance(result_json, dict):
                        # Check for error indicators
                        if result_json.get('error') or result_json.get('status') == 'incomplete':
                            needs_follow_up = True
                        # Check for specific indicators that another action is needed
                        if result_json.get('requires_additional_action') == True:
                            needs_follow_up = True
                except:
                    # If we can't parse the result as JSON, assume no follow-up needed
                    needs_follow_up = False
                
                # If we don't need a follow-up, get the final response and return
                if not needs_follow_up:
                    final_response = self.get_openai_api_call(messages)
                    final_msg = final_response.choices[0].message
                    final_content = final_msg.content or ""  # Ensure content is never None
                    formatted_response, voice_response = self.parse_response_with_voice(final_content)
                    return formatted_response, voice_response, "\n".join(map(str, agent_logs))

            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    logging.warning(f"Error occurred: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logging.error(f"Max retries reached. Error: {str(e)}")
                    return "An error occurred. Please try again.", "Something went wrong - try again.", ""

        return "Service temporarily unavailable. Please try again later.", "Service is down - try again later.", ""

app = func.FunctionApp()

@app.route(route="agent_manager", auth_level=func.AuthLevel.FUNCTION)
def agent_manager(req: func.HttpRequest) -> func.HttpResponse:
    """
    Agent Management API

    Endpoints:
    - GET /api/agent_manager?action=list_agents - List all available agents
    - GET /api/agent_manager?action=get_config&user_guid=xxx - Get user's agent configuration
    - POST /api/agent_manager with action=save_config - Save agent configuration
    - GET /api/agent_manager?action=list_presets - List agent combination presets
    - POST /api/agent_manager with action=save_preset - Save new preset
    """
    logging.info('Agent Manager API called')

    origin = req.headers.get('origin')
    cors_headers = build_cors_response(origin)

    if req.method == 'OPTIONS':
        return func.HttpResponse(
            status_code=200,
            headers=cors_headers
        )

    try:
        action = req.params.get('action', '')

        if req.method == 'GET':
            if action == 'list_agents':
                return handle_list_agents(cors_headers)
            elif action == 'get_config':
                user_guid = req.params.get('user_guid', DEFAULT_USER_GUID)
                return handle_get_config(user_guid, cors_headers)
            elif action == 'list_presets':
                return handle_list_presets(cors_headers)
            elif action == 'get_metadata_preview':
                # Get metadata preview for selected agents
                try:
                    req_body = req.get_json()
                    selected_agents = req_body.get('selected_agents', [])
                    return handle_metadata_preview(selected_agents, cors_headers)
                except:
                    return func.HttpResponse(
                        json.dumps({"error": "Invalid request body"}),
                        status_code=400,
                        mimetype="application/json",
                        headers=cors_headers
                    )
            else:
                return func.HttpResponse(
                    json.dumps({"error": "Unknown action"}),
                    status_code=400,
                    mimetype="application/json",
                    headers=cors_headers
                )

        elif req.method == 'POST':
            try:
                req_body = req.get_json()
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": "Invalid JSON"}),
                    status_code=400,
                    mimetype="application/json",
                    headers=cors_headers
                )

            if action == 'save_config':
                return handle_save_config(req_body, cors_headers)
            elif action == 'save_preset':
                return handle_save_preset(req_body, cors_headers)
            else:
                return func.HttpResponse(
                    json.dumps({"error": "Unknown action"}),
                    status_code=400,
                    mimetype="application/json",
                    headers=cors_headers
                )

        else:
            return func.HttpResponse(
                json.dumps({"error": "Method not allowed"}),
                status_code=405,
                mimetype="application/json",
                headers=cors_headers
            )

    except Exception as e:
        logging.error(f"Error in agent_manager: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
            headers=cors_headers
        )

def handle_list_agents(cors_headers):
    """List all available agents with their metadata from manifest"""
    try:
        # Try to load from manifest first (faster and more comprehensive)
        manifest_path = os.path.join(os.path.dirname(__file__), 'agent_manifest.json')

        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.loads(f.read())

            # Convert manifest format to API format
            agent_list = []
            for agent_name, agent_info in manifest['agents'].items():
                agent_list.append({
                    'name': agent_info['name'],
                    'filename': agent_info['filename'],
                    'metadata': agent_info['metadata'],
                    'description': agent_info['description'] or agent_info.get('file_docstring', 'No description'),
                    'parameters': agent_info.get('parameters', {}),
                    'category': agent_info['category'],
                    'tags': agent_info.get('tags', []),
                    'use_cases': agent_info.get('use_cases', []),
                    'capabilities': agent_info.get('capabilities', [])
                })

            # Already sorted by category in manifest
            return func.HttpResponse(
                json.dumps({
                    'agents': agent_list,
                    'source': 'manifest',
                    'statistics': manifest.get('statistics', {})
                }),
                mimetype="application/json",
                headers=cors_headers
            )
        else:
            # Fallback to dynamic loading if manifest doesn't exist
            logging.warning("Manifest not found, falling back to dynamic agent loading")
            agents = load_agents_from_folder(user_guid=None)

            agent_list = []
            for agent_name, agent in agents.items():
                agent_info = {
                    'name': agent.name,
                    'metadata': agent.metadata,
                    'description': agent.metadata.get('description', 'No description available'),
                    'parameters': agent.metadata.get('parameters', {}),
                    'category': categorize_agent(agent.name)
                }
                agent_list.append(agent_info)

            # Sort by category then name
            agent_list.sort(key=lambda x: (x['category'], x['name']))

            return func.HttpResponse(
                json.dumps({
                    'agents': agent_list,
                    'source': 'dynamic'
                }),
                mimetype="application/json",
                headers=cors_headers
            )
    except Exception as e:
        logging.error(f"Error listing agents: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
            headers=cors_headers
        )

def handle_get_config(user_guid, cors_headers):
    """Get agent configuration for a specific user"""
    try:
        storage_manager = AzureFileStorageManager()

        # Read enabled agents config
        try:
            agent_config_path = f"agent_config/{user_guid}"
            agent_config_content = storage_manager.read_file(agent_config_path, 'enabled_agents.json')
            if agent_config_content:
                enabled_agents = json.loads(agent_config_content)
            else:
                enabled_agents = None  # None means all agents enabled
        except:
            enabled_agents = None

        # Read custom settings if they exist
        try:
            settings_content = storage_manager.read_file(f"agent_config/{user_guid}", 'settings.json')
            if settings_content:
                settings = json.loads(settings_content)
            else:
                settings = {}
        except:
            settings = {}

        return func.HttpResponse(
            json.dumps({
                'user_guid': user_guid,
                'enabled_agents': enabled_agents,
                'settings': settings
            }),
            mimetype="application/json",
            headers=cors_headers
        )
    except Exception as e:
        logging.error(f"Error getting config: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
            headers=cors_headers
        )

def handle_save_config(req_body, cors_headers):
    """Save agent configuration for a user"""
    try:
        user_guid = req_body.get('user_guid', DEFAULT_USER_GUID)
        enabled_agents = req_body.get('enabled_agents', None)
        settings = req_body.get('settings', {})

        storage_manager = AzureFileStorageManager()

        # Save enabled agents list
        if enabled_agents is not None:
            agent_config_path = f"agent_config/{user_guid}"
            storage_manager.write_file(
                agent_config_path,
                'enabled_agents.json',
                json.dumps(enabled_agents, indent=2)
            )

        # Save settings
        if settings:
            storage_manager.write_file(
                f"agent_config/{user_guid}",
                'settings.json',
                json.dumps(settings, indent=2)
            )

        return func.HttpResponse(
            json.dumps({
                'success': True,
                'message': 'Configuration saved successfully'
            }),
            mimetype="application/json",
            headers=cors_headers
        )
    except Exception as e:
        logging.error(f"Error saving config: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
            headers=cors_headers
        )

def handle_list_presets(cors_headers):
    """List all agent combination presets from manifest or storage"""
    try:
        # Try to load from manifest first (includes auto-generated presets)
        manifest_path = os.path.join(os.path.dirname(__file__), 'agent_manifest.json')

        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.loads(f.read())
                presets = manifest.get('suggested_presets', [])

            # Also try to add custom presets from storage
            storage_manager = AzureFileStorageManager()
            try:
                presets_content = storage_manager.read_file('agent_config', 'presets.json')
                if presets_content:
                    custom_presets = json.loads(presets_content)
                    # Add custom presets that aren't auto-generated
                    for preset in custom_presets:
                        if not preset.get('auto_generated', False):
                            presets.append(preset)
            except:
                pass

            return func.HttpResponse(
                json.dumps({
                    'presets': presets,
                    'source': 'manifest'
                }),
                mimetype="application/json",
                headers=cors_headers
            )
        else:
            # Fallback to storage or defaults
            storage_manager = AzureFileStorageManager()

            try:
                presets_content = storage_manager.read_file('agent_config', 'presets.json')
                if presets_content:
                    presets = json.loads(presets_content)
                else:
                    presets = get_default_presets()
            except:
                presets = get_default_presets()

            return func.HttpResponse(
                json.dumps({
                    'presets': presets,
                    'source': 'storage'
                }),
                mimetype="application/json",
                headers=cors_headers
            )
    except Exception as e:
        logging.error(f"Error listing presets: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
            headers=cors_headers
        )

def handle_save_preset(req_body, cors_headers):
    """Save a new agent combination preset"""
    try:
        preset_name = req_body.get('name')
        preset_description = req_body.get('description')
        preset_agents = req_body.get('agents', [])
        preset_settings = req_body.get('settings', {})

        if not preset_name:
            return func.HttpResponse(
                json.dumps({"error": "Preset name is required"}),
                status_code=400,
                mimetype="application/json",
                headers=cors_headers
            )

        storage_manager = AzureFileStorageManager()

        # Read existing presets
        try:
            presets_content = storage_manager.read_file('agent_config', 'presets.json')
            if presets_content:
                presets = json.loads(presets_content)
            else:
                presets = get_default_presets()
        except:
            presets = get_default_presets()

        # Add new preset
        presets.append({
            'name': preset_name,
            'description': preset_description,
            'agents': preset_agents,
            'settings': preset_settings,
            'created_at': datetime.now().isoformat()
        })

        # Save back
        storage_manager.write_file(
            'agent_config',
            'presets.json',
            json.dumps(presets, indent=2)
        )

        return func.HttpResponse(
            json.dumps({
                'success': True,
                'message': 'Preset saved successfully'
            }),
            mimetype="application/json",
            headers=cors_headers
        )
    except Exception as e:
        logging.error(f"Error saving preset: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
            headers=cors_headers
        )

def handle_metadata_preview(selected_agents, cors_headers):
    """Generate metadata preview for selected agents"""
    try:
        # Load all agents
        all_agents = load_agents_from_folder(user_guid=None)

        # Filter to selected agents
        metadata_list = []
        for agent_name in selected_agents:
            agent = all_agents.get(agent_name)
            if agent and hasattr(agent, 'metadata'):
                metadata_list.append(agent.metadata)

        return func.HttpResponse(
            json.dumps({
                'metadata': metadata_list,
                'count': len(metadata_list)
            }),
            mimetype="application/json",
            headers=cors_headers
        )
    except Exception as e:
        logging.error(f"Error generating metadata preview: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
            headers=cors_headers
        )

def categorize_agent(agent_name):
    """Categorize agents for better organization"""
    categories = {
        'Memory': ['ContextMemory', 'ManageMemory'],
        'Commerce': ['OrderVerification'],
        'Utilities': ['GithubAgentLibraryManager', 'ScriptedDemo'],
        'Analysis': ['ContractAnalysis', 'PromptPlayground'],
    }

    for category, agents in categories.items():
        if agent_name in agents:
            return category

    return 'Other'

def get_default_presets():
    """Get default agent combination presets"""
    return [
        {
            'name': 'Full Suite',
            'description': 'All agents enabled for maximum functionality',
            'agents': None,  # None means all agents
            'settings': {},
            'icon': '🌟'
        },
        {
            'name': 'Customer Service',
            'description': 'Memory and order verification for customer interactions',
            'agents': ['context_memory_agent.py', 'manage_memory_agent.py', 'order_verification_agent.py'],
            'settings': {
                'enable_upsell': True,
                'business_type': 'fast_food'
            },
            'icon': '🛒'
        },
        {
            'name': 'Memory Only',
            'description': 'Just memory agents for conversation context',
            'agents': ['context_memory_agent.py', 'manage_memory_agent.py'],
            'settings': {},
            'icon': '🧠'
        },
        {
            'name': 'Analytics Suite',
            'description': 'Contract analysis and prompt playground for advanced users',
            'agents': ['contract_analysis_agent.py', 'prompt_playground_agent.py', 'context_memory_agent.py'],
            'settings': {},
            'icon': '📊'
        },
        {
            'name': 'Demo Mode',
            'description': 'Scripted demo agent for presentations',
            'agents': ['scripted_demo_agent.py', 'context_memory_agent.py'],
            'settings': {},
            'icon': '🎬'
        }
    ]

@app.route(route="businessinsightbot_function", auth_level=func.AuthLevel.FUNCTION)
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    origin = req.headers.get('origin')
    cors_headers = build_cors_response(origin)

    if req.method == 'OPTIONS':
        return func.HttpResponse(
            status_code=200,
            headers=cors_headers
        )

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            "Invalid JSON in request body",
            status_code=400,
            headers=cors_headers
        )

    if not req_body:
        return func.HttpResponse(
            "Missing JSON payload in request body",
            status_code=400,
            headers=cors_headers
        )

    # Ensure user_input is string, handle None case
    user_input = req_body.get('user_input')
    if user_input is None:
        user_input = ""
    else:
        user_input = str(user_input)
    
    # Ensure conversation_history is list and contents are properly formatted
    conversation_history = req_body.get('conversation_history', [])
    if not isinstance(conversation_history, list):
        conversation_history = []
    
    # Extract user_guid if provided in the request
    user_guid = req_body.get('user_guid')

    # Check for image_data in request - handle image upload first
    image_data = req_body.get('image_data')
    if image_data:
        try:
            # Import UploadImageAgent
            from agents.upload_image_agent import UploadImageAgent

            upload_agent = UploadImageAgent()
            # Extract filename from user_input if present
            filename = None
            if "upload this image:" in user_input.lower():
                parts = user_input.split("upload this image:", 1)
                if len(parts) > 1:
                    filename = parts[1].strip()

            # Upload the image
            upload_result = upload_agent.perform(
                image_data=image_data,
                filename=filename
            )

            # Return the upload result immediately
            return func.HttpResponse(
                json.dumps({
                    "assistant_response": upload_result,
                    "voice_response": "Image uploaded successfully",
                    "agent_logs": "UploadImage agent executed",
                    "user_guid": user_guid or DEFAULT_USER_GUID
                }),
                status_code=200,
                mimetype="application/json",
                headers=cors_headers
            )
        except Exception as e:
            logging.error(f"Error uploading image: {str(e)}")
            return func.HttpResponse(
                json.dumps({
                    "assistant_response": f"Error uploading image: {str(e)}",
                    "voice_response": "Image upload failed",
                    "agent_logs": f"UploadImage error: {str(e)}",
                    "user_guid": user_guid or DEFAULT_USER_GUID
                }),
                status_code=500,
                mimetype="application/json",
                headers=cors_headers
            )

    # Skip validation if input is just a GUID to load memory
    is_guid_only = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', user_input.strip(), re.IGNORECASE)

    # Validate user input for non-GUID requests
    if not is_guid_only and not user_input.strip():
        return func.HttpResponse(
            json.dumps({
                "error": "Missing or empty user_input in JSON payload"
            }),
            status_code=400,
            mimetype="application/json",
            headers=cors_headers
        )

    try:
        agents = load_agents_from_folder(user_guid)
        # Create a new Assistant instance for each request
        assistant = Assistant(agents)
        
        # Set user_guid if provided in the request or found in input
        if user_guid:
            assistant.user_guid = user_guid
            assistant._initialize_context_memory(user_guid)
        elif is_guid_only:
            assistant.user_guid = user_input.strip()
            assistant._initialize_context_memory(user_input.strip())
        # Otherwise, the default GUID will be used (already set in __init__)
            
        assistant_response, voice_response, agent_logs = assistant.get_response(
            user_input, conversation_history)

        # Include GUID and voice response in output
        response = {
            "assistant_response": str(assistant_response),
            "voice_response": str(voice_response),
            "agent_logs": str(agent_logs),
            "user_guid": assistant.user_guid  # Return the GUID in use (could be default or provided)
        }

        return func.HttpResponse(
            json.dumps(response),
            mimetype="application/json",
            headers=cors_headers
        )
    except Exception as e:
        error_response = {
            "error": "Internal server error",
            "details": str(e)
        }
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json",
            headers=cors_headers
        )