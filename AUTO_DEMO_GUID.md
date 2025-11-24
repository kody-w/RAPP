# Auto-Trigger Demos by GUID

The ScriptedDemoAgent now supports automatically triggering demos based on user GUID - **no separate configuration files needed!**

When a demo is triggered, the agent automatically generates a **shareable HTML script page** that shows the user exactly what to say at each step.

## How It Works

1. Add an `auto_trigger_guids` field to your demo JSON file with a list of GUIDs that should always trigger that demo
2. When that GUID is used, the demo auto-triggers and generates a beautiful HTML script guide
3. The response includes a download link to the script (valid for 7 days)

## Example Demo JSON

```json
{
  "demo_name": "My Sales Demo",
  "description": "Automatically triggered for sales demo GUIDs",

  "auto_trigger_guids": [
    "sales-demo-guid-1",
    "sales-demo-guid-2",
    "test-demo-123"
  ],

  "trigger_phrases": [
    "start demo",
    "show demo"
  ],

  "conversation_flow": [
    {
      "step_number": 1,
      "user_message": "hello",
      "agent_response": "Welcome to the demo! ..."
    }
  ]
}
```

## Setup

**1. Upload the HTML template (one-time setup):**
   ```bash
   python upload_demo_template.py
   ```
   This uploads `demo_script_template.html` to Azure File Storage.

**2. Add GUIDs to your demo file:**
   - Edit your demo JSON in Azure File Storage `demos/` directory
   - Add the `auto_trigger_guids` array with your GUIDs
   - Save the file

**3. Use the GUID in requests:**
   ```bash
   curl -X POST http://localhost:7071/api/businessinsightbot_function \
     -H "Content-Type: application/json" \
     -d '{
       "user_input": "anything at all",
       "conversation_history": [],
       "user_guid": "sales-demo-guid-1"
     }'
   ```

**4. That's it!**
   - Any message with that GUID will trigger the demo
   - The user's message is still matched against conversation_flow steps
   - The response includes a link to the HTML script guide
   - Share the script link with presenters so they know what to say!

## Multiple Demos

Each demo file can have its own list of GUIDs:

- `demo1.json` → `auto_trigger_guids: ["guid-a", "guid-b"]`
- `demo2.json` → `auto_trigger_guids: ["guid-c", "guid-d"]`
- `demo3.json` → `auto_trigger_guids: ["guid-e"]`

## Script HTML Features

The generated HTML script page includes:
- **Beautiful, professional design** with gradient header
- **Step-by-step guide** showing what to say and what response to expect
- **Auto-trigger info** displaying which GUIDs trigger this demo
- **Tips for success** to help presenters deliver great demos
- **Mobile responsive** - works on phones, tablets, and desktops
- **Print-friendly** - can be printed for offline reference

**Example Response:**
```
Welcome to the demo! This demo is automatically triggered for your GUID.

📄 Demo script available: [View Script](https://your-storage.file.core.windows.net/...)
```

Click the link to see a beautiful HTML page with all the conversation steps!

## Notes

- GUIDs can be any string (no specific format required)
- One GUID should only be in one demo's `auto_trigger_guids` list
- If a GUID matches, the demo triggers regardless of user input
- User input is still used for step matching within the demo
- The `auto_trigger_guids` field is optional - demos work normally without it
- Script HTML files are saved in `demo_scripts/` directory in Azure File Storage
- Download links expire after 7 days (regenerated each time demo is triggered)
- Template is cached for performance after first load
