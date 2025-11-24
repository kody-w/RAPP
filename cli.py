#!/usr/bin/env python3
"""
RAPP CLI - Command Line Interface for RAPP Azure Function

Usage:
    python cli.py                           # Interactive mode with default user
    python cli.py --user-guid <guid>        # Interactive mode with specific user
    python cli.py --message "Hello"         # Single message mode
    python cli.py --endpoint <url>          # Use custom endpoint
"""

import argparse
import requests
from typing import List, Dict, Optional

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class RAPPClient:
    def __init__(self, endpoint_url: str, user_guid: Optional[str] = None):
        """
        Initialize RAPP CLI client

        Args:
            endpoint_url: Full URL to the Azure Function endpoint (including code parameter if using Azure)
            user_guid: Optional user GUID for multi-user support
        """
        self.endpoint_url = endpoint_url
        self.user_guid = user_guid or "c0p110t0-aaaa-bbbb-cccc-123456789abc"
        self.conversation_history: List[Dict] = []

    def send_message(self, user_input: str) -> Dict:
        """
        Send a message to the RAPP endpoint

        Args:
            user_input: The user's message

        Returns:
            Response dictionary from the API
        """
        payload = {
            "user_input": user_input,
            "conversation_history": self.conversation_history,
            "user_guid": self.user_guid
        }

        try:
            response = requests.post(
                self.endpoint_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120  # 2 minute timeout for long-running operations
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            return {
                "error": "Request timed out. The operation may be taking too long.",
                "assistant_response": "Sorry, the request timed out. Please try again."
            }
        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "assistant_response": f"Error communicating with RAPP: {str(e)}"
            }

    def update_conversation_history(self, user_input: str, assistant_response: str):
        """Update the conversation history with the latest exchange"""
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_response
        })

        # Keep only last 20 messages to prevent overflow (as per RAPP design)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print(f"{Colors.YELLOW}Conversation history cleared.{Colors.ENDC}")

    def print_response(self, response: Dict, show_logs: bool = False):
        """Pretty print the response"""
        if "error" in response:
            print(f"\n{Colors.RED}Error: {response['error']}{Colors.ENDC}\n")
            return

        assistant_response = response.get("assistant_response", "")
        voice_response = response.get("voice_response", "")
        agent_logs = response.get("agent_logs", "")
        user_guid = response.get("user_guid", "")

        # Print formatted response
        print(f"\n{Colors.BOLD}{Colors.CYAN}Assistant:{Colors.ENDC}")
        print(assistant_response)

        # Print voice response if different
        if voice_response and voice_response != assistant_response:
            print(f"\n{Colors.BOLD}{Colors.GREEN}Voice Response:{Colors.ENDC}")
            print(voice_response)

        # Print agent logs if requested
        if show_logs and agent_logs:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}Agent Logs:{Colors.ENDC}")
            print(agent_logs)

        # Print user GUID
        if user_guid:
            print(f"\n{Colors.BLUE}[User: {user_guid}]{Colors.ENDC}")

        print()  # Empty line for spacing


def interactive_mode(client: RAPPClient, show_logs: bool = False):
    """Run the CLI in interactive chat mode"""
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("=" * 60)
    print("  RAPP CLI - Interactive Mode")
    print("=" * 60)
    print(f"{Colors.ENDC}")
    print(f"User GUID: {Colors.CYAN}{client.user_guid}{Colors.ENDC}")
    print(f"\nCommands:")
    print(f"  {Colors.GREEN}/clear{Colors.ENDC}     - Clear conversation history")
    print(f"  {Colors.GREEN}/logs{Colors.ENDC}      - Toggle agent logs display")
    print(f"  {Colors.GREEN}/history{Colors.ENDC}   - Show conversation history")
    print(f"  {Colors.GREEN}/exit{Colors.ENDC}      - Exit the CLI")
    print(f"  {Colors.GREEN}/help{Colors.ENDC}      - Show this help message")
    print(f"\nType your message and press Enter to send.\n")

    while True:
        try:
            # Get user input
            user_input = input(f"{Colors.BOLD}You:{Colors.ENDC} ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ['/exit', '/quit', '/q']:
                print(f"{Colors.YELLOW}Goodbye!{Colors.ENDC}")
                break
            elif user_input.lower() == '/clear':
                client.clear_history()
                continue
            elif user_input.lower() == '/logs':
                show_logs = not show_logs
                status = "enabled" if show_logs else "disabled"
                print(f"{Colors.YELLOW}Agent logs {status}.{Colors.ENDC}")
                continue
            elif user_input.lower() == '/history':
                print(f"\n{Colors.BOLD}Conversation History:{Colors.ENDC}")
                if not client.conversation_history:
                    print("No conversation history yet.")
                else:
                    for msg in client.conversation_history:
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        color = Colors.GREEN if role == 'user' else Colors.CYAN
                        print(f"{color}{role.capitalize()}:{Colors.ENDC} {content[:100]}...")
                print()
                continue
            elif user_input.lower() == '/help':
                print(f"\n{Colors.BOLD}Available Commands:{Colors.ENDC}")
                print(f"  {Colors.GREEN}/clear{Colors.ENDC}     - Clear conversation history")
                print(f"  {Colors.GREEN}/logs{Colors.ENDC}      - Toggle agent logs display")
                print(f"  {Colors.GREEN}/history{Colors.ENDC}   - Show conversation history")
                print(f"  {Colors.GREEN}/exit{Colors.ENDC}      - Exit the CLI")
                print(f"  {Colors.GREEN}/help{Colors.ENDC}      - Show this help message\n")
                continue

            # Send message to RAPP
            response = client.send_message(user_input)

            # Display response
            client.print_response(response, show_logs=show_logs)

            # Update conversation history
            if "assistant_response" in response:
                client.update_conversation_history(user_input, response["assistant_response"])

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Goodbye!{Colors.ENDC}")
            break
        except Exception as e:
            print(f"{Colors.RED}Error: {str(e)}{Colors.ENDC}")


def single_message_mode(client: RAPPClient, message: str, show_logs: bool = False):
    """Send a single message and exit"""
    response = client.send_message(message)
    client.print_response(response, show_logs=show_logs)


def main():
    parser = argparse.ArgumentParser(
        description="RAPP CLI - Command Line Interface for RAPP Azure Function",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--endpoint",
        type=str,
        default="http://localhost:7071/api/businessinsightbot_function",
        help="Azure Function endpoint URL (including code parameter if using Azure)"
    )

    parser.add_argument(
        "--user-guid",
        type=str,
        default=None,
        help="User GUID for multi-user support (default: c0p110t0-aaaa-bbbb-cccc-123456789abc)"
    )

    parser.add_argument(
        "--message", "-m",
        type=str,
        default=None,
        help="Send a single message and exit (non-interactive mode)"
    )

    parser.add_argument(
        "--logs",
        action="store_true",
        help="Show agent logs in responses"
    )

    args = parser.parse_args()

    # Create client
    client = RAPPClient(endpoint_url=args.endpoint, user_guid=args.user_guid)

    # Run in appropriate mode
    if args.message:
        single_message_mode(client, args.message, show_logs=args.logs)
    else:
        interactive_mode(client, show_logs=args.logs)


if __name__ == "__main__":
    main()
