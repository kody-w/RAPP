# PASTE THE CONTENT OF context_memory_agent.py HERE
# From the artifact "context_memory_agent.py - Memory Recall Agent"
import logging
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager

class ContextMemoryAgent(BasicAgent):
    def __init__(self):
        self.name = 'ContextMemory'
        self.metadata = {
            "name": self.name,
            "description": "Recalls PERSISTENT memories from the three-tier memory architecture. Can retrieve from: (1) USER-SPECIFIC memory (GUID-based, personal, cross-session), or (2) GLOBAL knowledge (universal, all users). NOTE: Session context (current conversation) is already available in the system prompt - this agent is for recalling LONG-TERM memories only.",
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
                        "description": "Optional list of keywords to filter memories by. Only messages containing these keywords will be included."
                    },
                    "full_recall": {
                        "type": "boolean",
                        "description": "Optional flag to return all memories without filtering. Default is false."
                    }
                },
                "required": []
            }
        }
        self.storage_manager = AzureFileStorageManager()
        super().__init__(name=self.name, metadata=self.metadata)
        
    def perform(self, **kwargs):
        user_guid = kwargs.get('user_guid')
        max_messages = kwargs.get('max_messages', 10)  # Default to 10 messages
        keywords = kwargs.get('keywords', [])
        full_recall = kwargs.get('full_recall', False)  # New parameter with default False
        
        # Default to full recall if no specific parameters were passed
        # This ensures initial memory loads return everything
        if 'max_messages' not in kwargs and 'keywords' not in kwargs:
            full_recall = True
        
        # Set memory context to the user's GUID if provided
        self.storage_manager.set_memory_context(user_guid)
            
        return self._recall_context(max_messages, keywords, full_recall)

    def _recall_context(self, max_messages, keywords, full_recall=False):
        # Read from memory storage
        memory_data = self.storage_manager.read_json()
        
        if not memory_data:
            if self.storage_manager.current_guid:
                return f"No USER-SPECIFIC memories found for GUID {self.storage_manager.current_guid}. (Note: Session context is already in the prompt, and global knowledge is separate.)"
            else:
                return "No GLOBAL knowledge memories stored yet. (Note: Session context and user-specific memories are in separate tiers.)"
                
        # For legacy format - UUIDs as keys are the ONLY format we support
        # Convert legacy format to a list we can process
        legacy_memories = []
        for key, value in memory_data.items():
            # Check if the key is a UUID and value is a dictionary
            if isinstance(value, dict) and 'message' in value:
                legacy_memories.append(value)
                
        # If no memories were found
        if not legacy_memories:
            return "No memories found for this session."
            
        return self._format_legacy_memories(legacy_memories, max_messages, keywords, full_recall)

    def _format_legacy_memories(self, memories, max_messages, keywords, full_recall=False):
        """Format memories from legacy storage format (UUIDs as keys)"""
        if not memories:
            return "No memories found in the format I understand."
            
        # For full recall, include all memories without filtering
        if full_recall:
            sorted_memories = sorted(
                memories,
                key=lambda x: (x.get('date', ''), x.get('time', '')),
                reverse=True
            )
            memory_lines = []
            for memory in sorted_memories:
                message = memory.get('message', '')
                theme = memory.get('theme', 'Unknown')
                date = memory.get('date', '')
                time = memory.get('time', '')
                
                # Format as a clean line
                if date and time:
                    memory_lines.append(f"• {message} (Theme: {theme}, Recorded: {date} {time})")
                else:
                    memory_lines.append(f"• {message} (Theme: {theme})")
                    
            if not memory_lines:
                return "No memories found."

            if self.storage_manager.current_guid:
                memory_tier = f"USER-SPECIFIC memory (GUID: {self.storage_manager.current_guid})"
            else:
                memory_tier = "GLOBAL knowledge (universal)"

            return f"All persistent memories from {memory_tier}:\n" + "\n".join(memory_lines)
            
        # Filter by keywords if provided
        if keywords and len(keywords) > 0:
            filtered_memories = []
            for memory in memories:
                content = str(memory.get('message', '')).lower()
                theme = str(memory.get('theme', '')).lower()
                
                if any(keyword.lower() in content for keyword in keywords) or \
                   any(keyword.lower() in theme for keyword in keywords):
                    filtered_memories.append(memory)
            
            if filtered_memories:
                memories = filtered_memories
            else:
                # If no matches, just use most recent
                memories = sorted(
                    memories,
                    key=lambda x: (x.get('date', ''), x.get('time', '')),
                    reverse=True
                )[:max_messages]
        else:
            # No keywords, just get most recent
            memories = sorted(
                memories,
                key=lambda x: (x.get('date', ''), x.get('time', '')),
                reverse=True
            )[:max_messages]
        
        # Format memory lines
        memory_lines = []
        for memory in memories:
            message = memory.get('message', '')
            theme = memory.get('theme', 'Unknown')
            date = memory.get('date', '')
            time = memory.get('time', '')
            
            # Format as a clean line
            if date and time:
                memory_lines.append(f"• {message} (Theme: {theme}, Recorded: {date} {time})")
            else:
                memory_lines.append(f"• {message} (Theme: {theme})")
                
        if not memory_lines:
            return "No matching memories found."

        if self.storage_manager.current_guid:
            memory_tier = f"USER-SPECIFIC memory (GUID: {self.storage_manager.current_guid})"
        else:
            memory_tier = "GLOBAL knowledge"

        return f"Persistent memories from {memory_tier}:\n" + "\n".join(memory_lines)
    
    def _summarize_memory_item(self, item):
        """Helper to summarize various memory item formats"""
        if isinstance(item, dict):
            if all(key in item for key in ['date', 'time', 'theme', 'message']):
                return f"On {item['date']} at {item['time']}, a memory was stored with the theme '{item['theme']}' and message '{item['message']}'."
        return None