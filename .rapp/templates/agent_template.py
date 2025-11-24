"""
{{AGENT_NAME}} Agent
{{UNDERLINE}}

Purpose: {{PURPOSE}}

This agent provides:
- {{FEATURE_1}}
- {{FEATURE_2}}
- {{FEATURE_3}}

Author: {{AUTHOR}}
Created: {{DATE}}
"""

import logging
from typing import Dict, List, Tuple, Any, Optional
from agents.basic_agent import BasicAgent


class {{CLASS_NAME}}(BasicAgent):
    """{{DESCRIPTION}}"""
    
    def __init__(self, client):
        """
        Initialize the {{AGENT_NAME}} agent.
        
        Args:
            client: OpenAI/Azure OpenAI client instance
        """
        super().__init__(client)
        self.client = client
        
        # Add any agent-specific initialization here
        # Example: self.max_retries = 3
        # Example: self.timeout = 30
        
    def get_name(self) -> str:
        """
        Return the agent's routing name (used for agent selection).
        This should be lowercase with underscores (snake_case).
        
        Returns:
            str: The agent's routing name
        """
        return "{{ROUTING_NAME}}"
    
    def get_description(self) -> str:
        """
        Return a clear description of what this agent does.
        This is used for agent selection and documentation.
        
        Returns:
            str: Human-readable description of agent capabilities
        """
        return """{{DESCRIPTION_TEXT}}"""
    
    def get_system_message(self) -> str:
        """
        Return the system message that defines the agent's behavior and personality.
        This message is sent to the AI model to set context and guidelines.
        
        Returns:
            str: System message for the AI model
        """
        return """You are {{AGENT_PERSONA}}.

Your role is to {{ROLE_DESCRIPTION}}.

Guidelines:
- {{GUIDELINE_1}}
- {{GUIDELINE_2}}
- {{GUIDELINE_3}}

When responding:
- {{RESPONSE_RULE_1}}
- {{RESPONSE_RULE_2}}
- {{RESPONSE_RULE_3}}

Always maintain {{TONE}} tone and provide {{OUTPUT_STYLE}} responses."""
    
    def execute(
        self, 
        user_input: str, 
        conversation_history: List[Dict[str, str]], 
        user_guid: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Execute the agent's main logic.
        
        This method:
        1. Processes the user input
        2. Accesses conversation history for context
        3. Performs agent-specific operations
        4. Generates a response
        5. Updates conversation history
        
        Args:
            user_input: The current user message/query
            conversation_history: List of previous messages in the conversation
            user_guid: Optional user identifier for personalized memory/context
            
        Returns:
            Tuple containing:
                - response (str): The agent's response text
                - updated_history (List[Dict]): Updated conversation history
        """
        try:
            logging.info(f"{{CLASS_NAME}} executing with input: {user_input[:100]}...")
            
            # Add user input to conversation history
            conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # ==================================================================
            # AGENT-SPECIFIC LOGIC GOES HERE
            # ==================================================================
            
            # Example: Load user-specific memory
            # from utils.azure_file_storage import AzureFileStorageManager
            # storage = AzureFileStorageManager()
            # user_context = storage.load_memory(user_guid, "context_key")
            
            # Example: Prepare messages for AI model
            messages = [
                {"role": "system", "content": self.get_system_message()}
            ]
            
            # Add conversation history (limit to recent messages to manage tokens)
            recent_history = conversation_history[-10:]  # Last 10 messages
            messages.extend(recent_history)
            
            # Example: Call AI model
            response = self.client.chat.completions.create(
                model=os.getenv("OPENAI_DEPLOYMENT_NAME"),
                messages=messages,
                temperature=0.7,  # Adjust based on agent needs
                max_tokens=1000   # Adjust based on expected response length
            )
            
            response_text = response.choices[0].message.content
            
            # Example: Save results to memory
            # storage.save_memory(user_guid, "results_key", {
            #     "timestamp": datetime.now().isoformat(),
            #     "result": response_text
            # })
            
            # ==================================================================
            # END AGENT-SPECIFIC LOGIC
            # ==================================================================
            
            # Add assistant response to conversation history
            conversation_history.append({
                "role": "assistant",
                "content": response_text
            })
            
            logging.info(f"{{CLASS_NAME}} completed successfully")
            return response_text, conversation_history
            
        except Exception as e:
            # Log the error
            logging.error(f"{{CLASS_NAME}} error: {str(e)}", exc_info=True)
            
            # Create user-friendly error message
            error_response = (
                f"I apologize, but I encountered an error while processing your request. "
                f"Error: {str(e)[:200]}"
            )
            
            # Add error to conversation history
            conversation_history.append({
                "role": "assistant",
                "content": error_response
            })
            
            return error_response, conversation_history
    
    # ==================================================================
    # HELPER METHODS (Optional)
    # ==================================================================
    
    def _helper_method_example(self, data: Any) -> Any:
        """
        Helper method for agent-specific operations.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed data
        """
        # Implement helper logic here
        pass
    
    def _validate_input(self, user_input: str) -> bool:
        """
        Validate user input before processing.
        
        Args:
            user_input: User's input text
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Add validation logic here
        if not user_input or len(user_input.strip()) == 0:
            return False
        return True
