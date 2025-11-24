"""
Agent Generator
===============

Purpose: Scaffolds new RAPP agents from templates with proper structure,
naming conventions, and best practices built-in.

This agent:
- Creates new agent files with proper BasicAgent inheritance
- Follows RAPP naming conventions automatically
- Includes all required methods with documentation
- Adds appropriate error handling and logging
- Generates corresponding test files

Usage:
    from .rapp.agents.agent_generator import AgentGenerator
    
    generator = AgentGenerator(client)
    result = generator.execute(
        "Create a new agent called 'email_summarizer' that summarizes emails",
        [],
        user_guid
    )
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple


class AgentGenerator:
    """Generate new RAPP agents from templates."""
    
    def __init__(self, client):
        self.client = client
        self.repo_root = Path(__file__).parent.parent.parent
        self.agents_dir = self.repo_root / "agents"
        self.demos_dir = self.repo_root / "demos"
        
    def get_name(self):
        return "agent_generator"
    
    def get_description(self):
        return """Generates new RAPP agents with proper structure, naming conventions, 
        and best practices. Provide agent name and description to create a fully 
        scaffolded agent file ready for customization."""
    
    def get_system_message(self):
        return """You are the Agent Generator for the RAPP platform.

Your role is to scaffold new agents with:
1. Proper BasicAgent inheritance
2. Correct naming conventions (snake_case files, PascalCase classes)
3. All required methods: __init__, get_name(), get_description(), get_system_message(), execute()
4. Error handling and logging patterns
5. Comprehensive docstrings and comments
6. Type hints for parameters and returns

When generating agents:
- Extract the agent name and purpose from user input
- Use snake_case for filenames and agent names
- Use PascalCase for class names
- Include helpful comments explaining each section
- Add appropriate error handling
- Follow RAPP coding patterns exactly

Ask for clarification if the agent purpose is unclear."""
    
    def execute(self, user_input: str, conversation_history: List[Dict], user_guid: str = None) -> Tuple[str, List[Dict]]:
        """Generate a new agent based on user specifications."""
        
        try:
            # Use AI to parse the request and generate agent code
            system_message = self.get_system_message()
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"""Generate a new RAPP agent based on this request:

{user_input}

Provide the following:
1. Agent filename (snake_case_agent.py)
2. Agent class name (PascalCaseAgent)
3. Agent routing name (snake_case)
4. Complete Python code for the agent
5. A brief description of what the agent does

Format your response as JSON:
{{
    "filename": "agent_name.py",
    "classname": "AgentName",
    "routing_name": "agent_name",
    "description": "Brief description",
    "code": "Complete Python code here"
}}
"""}
            ]
            
            response = self.client.chat.completions.create(
                model=os.getenv("OPENAI_DEPLOYMENT_NAME"),
                messages=messages,
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            
            # Try to parse the JSON response
            import json
            try:
                agent_spec = json.loads(result)
                
                # Create the agent file
                agent_path = self.agents_dir / agent_spec["filename"]
                
                if agent_path.exists():
                    output = f"⚠️  Agent file already exists: {agent_spec['filename']}\n\n"
                    output += "Generated code (not saved):\n\n"
                    output += "```python\n"
                    output += agent_spec["code"]
                    output += "\n```"
                else:
                    # Write the agent file
                    with open(agent_path, 'w') as f:
                        f.write(agent_spec["code"])
                    
                    output = f"✅ Successfully created new agent!\n\n"
                    output += f"**File:** `agents/{agent_spec['filename']}`\n"
                    output += f"**Class:** `{agent_spec['classname']}`\n"
                    output += f"**Routing Name:** `{agent_spec['routing_name']}`\n\n"
                    output += f"**Description:** {agent_spec['description']}\n\n"
                    output += "Next steps:\n"
                    output += "1. Review and customize the agent code\n"
                    output += "2. Test locally with ./run.sh\n"
                    output += "3. Create a demo file in demos/ directory\n"
                    output += "4. Update documentation if needed\n"
                    output += "5. Deploy to Azure when ready\n\n"
                    output += "The agent will be automatically loaded on next startup!"
                
            except json.JSONDecodeError:
                # AI didn't return valid JSON, return the raw response
                output = "Generated agent code:\n\n"
                output += result
                output += "\n\nPlease manually create the agent file in the agents/ directory."
            
            # Add to conversation history
            conversation_history.append({
                "role": "user",
                "content": user_input
            })
            conversation_history.append({
                "role": "assistant",
                "content": output
            })
            
            return output, conversation_history
            
        except Exception as e:
            logging.error(f"Agent Generator error: {str(e)}")
            error_msg = f"Error generating agent: {str(e)}\n\n"
            error_msg += "Please check the error and try again with more specific requirements."
            
            conversation_history.append({
                "role": "user",
                "content": user_input
            })
            conversation_history.append({
                "role": "assistant",
                "content": error_msg
            })
            return error_msg, conversation_history
