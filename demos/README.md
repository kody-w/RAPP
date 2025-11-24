# RAPP Demos and Examples

This directory contains demonstration files and example implementations for RAPP.

## Demo Python Scripts

### Enterprise Orchestration
- **demo_enterprise_orchestrator.py** - Full enterprise orchestration demo
- **demo_orchestrator_standalone.py** - Standalone orchestrator example

### Order Management
- **demo_order_agent.py** - Order processing agent demonstration
- **test_order_agent.py** - Order agent test suite

## Interactive Demos

### D&D Game Demos
- **dnd_visual_game.html** - D&D visual game interface
- **dnd_visual_game_ENHANCED.html** - Enhanced D&D game with additional features

## Running Demos

### Python Demos
All Python demos are standalone and can be run directly:

```bash
# Enterprise orchestrator demo
python demos/demo_enterprise_orchestrator.py

# Standalone orchestrator demo
python demos/demo_orchestrator_standalone.py

# Order agent demo
python demos/demo_order_agent.py
```

### HTML Demos
HTML demos can be opened directly in your browser:

```bash
# Open D&D game demo
open demos/dnd_visual_game.html

# Or use Python HTTP server
cd demos
python -m http.server 8000
# Then navigate to http://localhost:8000/dnd_visual_game.html
```

## Related Documentation

- **D&D Player Guide**: [/docs/guides/DND_PLAYER_GUIDE.md](/docs/guides/DND_PLAYER_GUIDE.md)
- **Order Verification Guide**: [/docs/guides/ORDER_VERIFICATION_AGENT_README.md](/docs/guides/ORDER_VERIFICATION_AGENT_README.md)
- **Demo System Documentation**: [/AI-Agent-Templates/DEMO_SYSTEM.md](/AI-Agent-Templates/DEMO_SYSTEM.md)

## Creating Your Own Demos

See the [Agent Development Guide](/docs/AGENT_DEVELOPMENT.md) for information on creating custom agents and demos.
