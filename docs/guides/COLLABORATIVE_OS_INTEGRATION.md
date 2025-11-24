# Collaborative AI OS - Integration Guide

## Overview

The **Collaborative AI OS** is a shared workspace environment where both humans and AI assistants can interact with the same system in real-time. It combines the best features of JARVIS Protocol OS and Windows 95 emulation patterns into a unified, bidirectional collaboration platform.

**Location:** `localFirstTools/apps/ai-tools/collaborative-ai-os.html`

## Key Features

### 🤖 **Bidirectional AI Collaboration**
- AI can send commands to the OS
- User can see AI actions in real-time
- Shared activity feed logs all interactions
- Synchronized state between user and AI

### 🖥️ **Full OS Environment**
- Window management (drag, minimize, maximize, close)
- Taskbar with app launchers
- Multiple applications:
  - **Command Center**: Main AI command interface
  - **Activity Feed**: Real-time log of all user/AI actions
  - **Terminal**: Execute system commands
  - **File Manager**: Shared file system
  - **AI Chat**: Direct conversation with AI assistant
  - **Settings**: Configure RAPP connection

### 📊 **Activity Tracking**
- Every action logged with timestamp
- Visual distinction between user, AI, and system actions
- Persistent activity history with JSON export

### 🔌 **RAPP Backend Integration**
- Connects to RAPP backend for real AI processing
- Falls back to offline simulation when disconnected
- Configurable endpoint and user GUID
- Real-time connection status indicator

### 💾 **Local-First Design**
- All data stored in browser localStorage
- Complete JSON import/export functionality
- Works fully offline (with simulated AI responses)
- Self-contained single HTML file

## Accessing from Main Chat (index.html)

### Option 1: Quick Link Integration

Add this button to your main chat interface:

```html
<button onclick="window.open('localFirstTools/apps/ai-tools/collaborative-ai-os.html', '_blank')">
    🤖 Launch Collaborative OS
</button>
```

### Option 2: Chat Command

In your chat interface, add a command handler:

```javascript
// In your chat message processing
if (userInput.toLowerCase().includes('open os') ||
    userInput.toLowerCase().includes('launch os') ||
    userInput.toLowerCase().includes('collaborative os')) {
    window.open('localFirstTools/apps/ai-tools/collaborative-ai-os.html', '_blank');
    return "Opening Collaborative AI OS...";
}
```

### Option 3: Agent Command

Create an agent in your RAPP backend that can launch the OS:

```python
# agents/os_launcher_agent.py
from agents.basic_agent import BasicAgent

class OSLauncherAgent(BasicAgent):
    def __init__(self):
        self.name = 'LaunchOS'
        self.metadata = {
            "name": self.name,
            "description": "Opens the Collaborative AI OS workspace",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
        super().__init__(self.name, self.metadata)

    def perform(self, **kwargs):
        return """
        🤖 **Collaborative AI OS**

        I'm opening the shared workspace environment where we can collaborate in real-time.

        **What you can do:**
        - Send me commands through the Command Center
        - Watch me interact with the OS in the Activity Feed
        - Chat with me directly in the AI Chat window
        - Execute terminal commands together
        - Manage shared files

        The OS is opening in a new window...

        **Quick Start:**
        1. Look for the Command Center window
        2. Type a command like "open terminal" or "system status"
        3. Watch the activity feed to see my actions

        [Open Collaborative OS](../../localFirstTools/apps/ai-tools/collaborative-ai-os.html)
        """
```

### Option 4: Sidebar Menu

Add to your main chat's navigation:

```html
<nav class="sidebar">
    <a href="index.html">💬 Chat</a>
    <a href="agent_store.html">🛒 Agent Store</a>
    <a href="localFirstTools/apps/ai-tools/collaborative-ai-os.html" target="_blank">
        🤖 Collaborative OS
    </a>
    <a href="localFirstTools/index.html">🔧 Local Tools</a>
</nav>
```

## Usage Scenarios

### 1. **AI-Assisted System Administration**

**User:** "Analyze the current system state"

**AI:** *Opens terminal, runs diagnostics, creates report*

**Activity Feed:**
```
[AI] Opening terminal window
[AI] Executing: system status
[AI] Analyzing logs...
[AI] Report complete: System healthy, 3 windows open, 47 activities logged
```

### 2. **Collaborative File Management**

**User:** "Create a file called project-notes.txt"

**AI:** *Creates file, opens file manager*

**Activity Feed:**
```
[User] Requested: Create project-notes.txt
[AI] Creating file: project-notes.txt
[AI] File created successfully
[AI] Opening file manager
```

### 3. **Real-Time Command Execution**

**User:** Clicks quick action "System Status"

**AI:** *Executes command, displays results*

**Activity Feed:**
```
[User] Quick command: system status
[AI] System Status:
     - Windows: 4 open
     - Activities: 52 logged
     - Connection: Connected to RAPP
     - Memory: 1.2MB used
```

### 4. **Interactive Problem Solving**

**User:** "Help me debug why the connection keeps dropping"

**AI:**
```
[AI] Opening terminal for diagnostics
[AI] Checking connection logs...
[AI] Found issue: Timeout threshold too low
[AI] Creating fix-connection.sh script
[AI] Recommendation: Increase timeout to 30s
[AI] Would you like me to apply this fix?
```

## RAPP Backend Configuration

### Connection Setup

The Collaborative OS connects to RAPP backend at:
```
http://localhost:7071/api/businessinsightbot_function
```

You can change this in the Settings window or by editing:
```javascript
this.rappEndpoint = 'http://localhost:7071/api/businessinsightbot_function';
```

### AI Command Processing

When AI receives commands in the OS, it should respond with:

```json
{
  "assistant_response": "Executing your command...",
  "os_actions": [
    {
      "action": "open_window",
      "window": "terminal"
    },
    {
      "action": "execute_command",
      "command": "ls -la"
    }
  ]
}
```

The OS will parse `os_actions` and execute them automatically.

### Supported OS Actions

```javascript
{
  "action": "open_window",
  "window": "terminal|files|activity|ai-chat|settings|command-center"
}

{
  "action": "close_window",
  "window": "terminal"
}

{
  "action": "execute_command",
  "command": "any terminal command"
}

{
  "action": "create_file",
  "name": "filename.txt",
  "content": "file contents"
}

{
  "action": "log_activity",
  "message": "Custom activity message"
}

{
  "action": "show_notification",
  "title": "Notification Title",
  "message": "Notification body",
  "type": "success|error|info"
}
```

## Architecture

### Communication Flow

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│                 │         │                  │         │                 │
│  User Actions   │────────▶│  Collaborative   │────────▶│  RAPP Backend   │
│  (OS Interface) │         │       OS         │         │   (AI Agent)    │
│                 │         │                  │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        ▲                            │                            │
        │                            │                            │
        │                            ▼                            │
        │                   ┌──────────────────┐                 │
        │                   │                  │                 │
        │                   │  Activity Feed   │                 │
        │                   │  (Shared State)  │                 │
        │                   │                  │                 │
        │                   └──────────────────┘                 │
        │                            ▲                            │
        │                            │                            │
        └────────────────────────────┴────────────────────────────┘
                          AI Response & Actions
```

### State Management

All state is stored in localStorage:

```javascript
{
  "activities": [
    {
      "type": "user|ai|system",
      "message": "Activity description",
      "timestamp": 1234567890
    }
  ],
  "files": {
    "filename.txt": "file contents"
  },
  "settings": {
    "rappEndpoint": "http://localhost:7071/api/businessinsightbot_function",
    "userGUID": "collab-os-1234567890"
  }
}
```

## Customization

### Adding New Applications

Edit the `openApp()` method to add new windows:

```javascript
createMyApp() {
    return {
        title: '🎨 My Custom App',
        width: 800,
        height: 600,
        content: `
            <div>
                <h2>My Custom Application</h2>
                <p>Custom content here...</p>
            </div>
        `
    };
}
```

Then register it:

```javascript
const apps = {
    'my-app': this.createMyApp(),
    // ... existing apps
};
```

### Styling

All styles are inline in the `<style>` block. Key CSS variables:

```css
--primary-color: #00d4ff;
--ai-color: #00ff00;
--bg-dark: #0a0a0a;
--bg-medium: #1a1a2e;
--window-bg: rgba(20, 20, 40, 0.95);
```

### AI Personality

Customize AI responses in `simulateAIResponse()` for offline mode, or enhance your RAPP backend agents with OS-aware commands.

## Troubleshooting

### Connection Issues

**Problem:** "Disconnected" status in taskbar

**Solutions:**
1. Ensure RAPP is running: `./run.sh`
2. Check endpoint URL in Settings
3. Verify CORS headers in RAPP backend
4. Try reconnecting: Settings → Update Endpoint

### Window Management

**Problem:** Windows not draggable

**Solutions:**
1. Click and drag from title bar only
2. Avoid dragging from window controls
3. Use Maximize button for fullscreen

### Activity Feed Not Updating

**Problem:** Activities not showing in real-time

**Solutions:**
1. Refresh the Activity Feed window
2. Check localStorage is enabled
3. Export and re-import data to reset state

### AI Commands Not Working

**Problem:** AI doesn't respond to commands

**Solutions:**
1. Check RAPP connection status
2. Verify conversation history isn't corrupted
3. Try offline mode commands first
4. Review browser console for errors

## Advanced Integration

### Embedded Mode

Embed the OS in an iframe:

```html
<iframe src="localFirstTools/apps/ai-tools/collaborative-ai-os.html"
        style="width: 100%; height: 100vh; border: none;">
</iframe>
```

### PostMessage Communication

Send commands from parent window:

```javascript
const osFrame = document.getElementById('os-frame');
osFrame.contentWindow.postMessage({
    type: 'AI_COMMAND',
    command: 'open terminal'
}, '*');
```

Handle in OS:

```javascript
window.addEventListener('message', (event) => {
    if (event.data.type === 'AI_COMMAND') {
        collaborativeOS.sendAICommand(event.data.command);
    }
});
```

### REST API Integration

Create a backend endpoint that mirrors OS commands:

```python
@app.route('/os/command', methods=['POST'])
def os_command():
    command = request.json.get('command')
    # Process command
    # Send to AI
    # Return OS actions
    return jsonify({
        "response": "Command executed",
        "os_actions": [...]
    })
```

## Future Enhancements

### Planned Features

- [ ] Multi-user collaboration (WebRTC)
- [ ] Screen sharing between user and AI
- [ ] Voice commands via Web Speech API
- [ ] File upload/download from OS
- [ ] Plugin system for custom apps
- [ ] Mobile touch gestures
- [ ] Dark/light theme toggle
- [ ] Keyboard shortcuts reference
- [ ] Undo/redo for actions
- [ ] OS state snapshots

### Contributing

The Collaborative OS is designed to be extended. Key extension points:

1. **New Apps**: Add to `openApp()` method
2. **AI Actions**: Enhance `processAICommand()`
3. **Terminal Commands**: Extend `handleTerminalCommand()`
4. **RAPP Integration**: Add agents that understand OS context

## License & Credits

**Pattern Source:**
- JARVIS Protocol OS (jarvis-protocol-os.html)
- Windows 95 Emulator (windows95-emulator.html)
- Local First Tools philosophy

**Integration:**
- RAPP backend (function_app.py)
- Claude Code agents
- Microsoft 365 ecosystem

---

## Quick Reference Card

### Keyboard Shortcuts
- `ESC` - Close active window
- `Enter` - Submit command/chat

### Quick Commands
- "open terminal" - Launch terminal
- "show activity" - Open activity feed
- "list files" - Open file manager
- "system status" - Show system info

### RAPP Endpoints
- Main: `/api/businessinsightbot_function`
- OS Command: `/api/os_command` (custom)

### Data Locations
- localStorage: `collaborative-os-data`
- Export format: JSON
- File location: Apps downloads folder

---

**Ready to collaborate with AI in a shared workspace!** 🤖✨
