# Demo System Documentation

## Overview

The RAPP Agent Store includes an interactive demo system that allows users to "kick the tires" and experience agents before installing them. Demos are self-contained HTML files with embedded scripts that showcase real-world scenarios.

## Demo Architecture

### Existing Pattern (OG Agent Template Library)

Each agent stack has a demo HTML file with:
- **M365 Copilot design system** - Familiar Microsoft 365 interface
- **Embedded demo script** - JavaScript `demoScript` array with conversation flow
- **Demo controls** - Play, Pause, Reset, Skip buttons
- **Chat interface** - User and assistant messages with typing indicators
- **Agent result cards** - Structured data display for agent outputs

### File Structure

```
agent_stacks/
  {category}_stacks/
    {agent_name}_stack/
      demos/
        {agent_name}_demo.html    # Self-contained interactive demo
      agents/
        {agent_name}_agent.py     # Agent implementation
      metadata.json               # Stack metadata
```

### Demo Script Format

Demos use an embedded JavaScript `demoScript` array:

```javascript
const demoScript = [
    {
        type: 'conversation',
        messages: [
            {
                role: 'user',
                content: 'User message text',
                typingTime: 1500,    // Milliseconds to show typing indicator
                delay: 1000          // Delay before next message
            },
            {
                role: 'assistant',
                content: 'Agent response text',
                typingTime: 2000,
                delay: 1500,
                showResult: true,     // Show agent result card
                resultData: {         // Structured data to display
                    'Category Name': {
                        'Field 1': 'Value 1',
                        'Field 2': 'Value 2'
                    }
                }
            }
        ]
    }
];
```

## How Demos Work

### 1. Demo Discovery

The agent_store.html automatically discovers demos:

```javascript
// Generate demo URL from agent ID
const categoryDir = CATEGORY_TO_DIR[agent.category];
const agentIdWithUnderscores = agent.id.replace(/-/g, '_');
const stackName = agentIdWithUnderscores + '_stack';
const demoFileName = `${agentIdWithUnderscores}_demo.html`;
const demoUrl = `${GITHUB_CONFIG.rawUrl}/agent_stacks/${categoryDir}/${stackName}/demos/${demoFileName}`;

// Check if demo exists
const demoCheck = await fetch(demoUrl, { method: 'HEAD' });
if (demoCheck.ok) {
    // Demo is available!
}
```

### 2. Demo Launch

When users click "Launch Interactive Demo":
- Opens demo HTML file in new tab
- Demo loads from raw GitHub URL
- Works completely standalone
- No backend or installation required

### 3. Demo Playback

The demo HTML file:
1. Shows M365 Copilot interface with sidebar
2. Displays welcome screen with quick-start cards
3. Plays scripted conversation on button click
4. Shows typing indicators for realistic feel
5. Displays agent result cards with structured data
6. Supports pause, reset, and skip controls

## Creating New Demos

### Option 1: Using Existing Pattern (Recommended)

Copy an existing demo HTML file and customize:

```bash
# Copy template from existing demo
cp agent_stacks/slg_government_stacks/citizen_service_request_stack/demos/citizen_service_request_demo.html \
   agent_stacks/your_category_stacks/your_agent_stack/demos/your_agent_demo.html

# Edit the demo script and agent name
# Update demoScript array with your scenarios
# Change header title and welcome screen text
```

### Option 2: Using JSON Template (Alternative)

Use the demo_template.html and demo_template.json pattern:

1. Create JSON file with demo script:
```json
{
  "demo_name": "Your_Agent_Demo",
  "agent_name": "YourAgent",
  "description": "Interactive demonstration",
  "conversation_flow": [
    {
      "step_number": 1,
      "user_message": "Show me what you can do",
      "agent_response": [
        {
          "type": "text",
          "content": "I can help you with X, Y, and Z..."
        }
      ]
    }
  ]
}
```

2. Create HTML file that loads JSON:
```html
<script>
const DEMO_JSON_PATH = 'AI-Agent-Templates/agent_stacks/your_category/your_agent_stack/demos/your_agent_demo.json';
// Demo loader will fetch and play the JSON script
</script>
```

## Demo Best Practices

### Content Guidelines

1. **Show Real Scenarios** - Use realistic use cases that users will encounter
2. **Progressive Complexity** - Start simple, then show advanced features
3. **Clear Value** - Demonstrate concrete benefits and outcomes
4. **Structured Data** - Use agent result cards to show organized information
5. **Quick Duration** - Keep demos under 3 minutes (5-8 conversation steps)

### Technical Guidelines

1. **Self-Contained** - Demo HTML should work standalone without dependencies
2. **Mobile Responsive** - Test on different screen sizes
3. **Fast Loading** - Minimize external resources
4. **Clear Controls** - Make demo buttons obvious and functional
5. **Error Handling** - Gracefully handle edge cases

### Example Demo Structure

```
Step 1: User asks initial question
  → Show typing indicator
  → Agent provides overview response

Step 2: User requests specific action
  → Show typing indicator
  → Agent confirms and processes request
  → Display agent result card with structured data

Step 3: User asks follow-up question
  → Show typing indicator
  → Agent provides detailed insights
  → Display additional data

Step 4: Demo complete
  → Show completion message
  → Provide next steps / call-to-action
```

## Integration with Agent Store

### Automatic Demo Detection

The agent_store.html automatically:
1. Checks for demo files when loading agent details
2. Adds "🎮 Interactive Demo" section if demo exists
3. Provides "Launch Interactive Demo" button
4. Opens demo in new tab when clicked

### Demo Button Placement

Demos appear in two places:
1. **Agent Detail Modal** - Full demo section with description
2. **Modal Action Buttons** - Quick "Try Demo" button

### Demo URL Format

Raw GitHub URLs are used for direct access:
```
https://raw.githubusercontent.com/kody-w/RAPP/main/AI-Agent-Templates/agent_stacks/{category}/{stack}/demos/{demo}.html
```

This allows demos to run directly without GitHub's blob viewer wrapper.

## Troubleshooting

### Demo Not Showing

1. Check file naming convention:
   - Agent ID: `citizen-service-request`
   - Stack name: `citizen_service_request_stack`
   - Demo file: `citizen_service_request_demo.html`

2. Verify file location:
   - Must be in `demos/` folder inside stack
   - Path must match category structure

3. Check console logs:
   - `✅ Demo found for {agent-id}` - Success
   - `ℹ️ No demo available for {agent-id}` - File not found

### Demo Not Playing

1. Check `demoScript` format:
   - Must be valid JavaScript array
   - Messages need `type`, `content`, `typingTime`, `delay`

2. Verify message types:
   - Use `role: 'user'` or `role: 'assistant'`
   - Or use `type: 'user'` or `type: 'agent'`

3. Check result data structure:
   - Nested objects are supported
   - Arrays are joined with `<br>`

### Demo 404 Error

1. Verify GitHub repository settings:
   - Repository must be public
   - Raw URLs must be accessible

2. Check GITHUB_CONFIG in agent_store.html:
   - `owner: 'kody-w'`
   - `repo: 'RAPP'`
   - `branch: 'main'`

3. Test raw URL directly:
   - Copy demo URL from console
   - Open in browser
   - Should show HTML source

## Demo Examples

### Simple Demo (2 steps)
- User: "What can you help with?"
- Agent: Overview response with capabilities list
- User: "Show me an example"
- Agent: Detailed example with result card

### Complex Demo (4+ steps)
- User: Reports issue
- Agent: Acknowledges and gathers details
- Agent: Shows processing result card
- User: Asks follow-up question
- Agent: Provides additional insights with data
- User: Thanks agent
- Agent: Confirms completion and next steps

## Future Enhancements

### Potential Improvements

1. **Demo Templates** - More starting templates for common scenarios
2. **Demo Builder** - GUI tool to create demos without coding
3. **Interactive Inputs** - Allow users to type custom messages
4. **Branch Navigation** - Multiple paths based on user choices
5. **Live API Mode** - Option to connect to real agent backend
6. **Demo Analytics** - Track which demos are most popular
7. **Embedded Demos** - Show demos inline in agent store modal

### JSON-Based Future

While the current pattern uses embedded scripts, the JSON template system (demo_template.json + demo_template.html) provides a path forward for:
- Easier demo creation (just edit JSON)
- Centralized demo management
- Automated demo generation from agent metadata
- Multi-language demo support
- Version control for demo content

---

## Quick Reference

### Demo File Naming
```
{agent_id_with_underscores}_demo.html
```

### Demo URL Pattern
```
https://raw.githubusercontent.com/{owner}/{repo}/{branch}/AI-Agent-Templates/agent_stacks/{category}/{stack}/demos/{demo}.html
```

### Key Files
- `demo_template.html` - JSON-based demo player
- `demo_template.json` - Demo script template
- `agent_store.html:2935` - Demo detection logic
- `citizen_service_request_demo.html` - Example embedded script demo

### Console Commands
```javascript
// Test demo URL
fetch('https://raw.githubusercontent.com/kody-w/RAPP/main/AI-Agent-Templates/agent_stacks/slg_government_stacks/citizen_service_request_stack/demos/citizen_service_request_demo.html')

// Check all available demos
grep -r "_demo.html" AI-Agent-Templates/agent_stacks/
```

---

**Last Updated:** 2025-11-24
**Pattern Source:** Original Agent Template Library
**Maintainer:** RAPP Team
