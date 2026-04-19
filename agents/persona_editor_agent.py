"""
persona_editor_agent.py — Editor persona, composite of three specialist agents.

Each specialist (factcheck / voicecheck / cutweak) is its own portable
agent.py. Editor's perform() direct-imports them and runs each in turn,
then composes the final output.

Sacred all the way down: this file is a single agent.py, but its perform()
delegates to other agent.py files. Cat any one of them to read the whole
unit. Move them together to share the Editor capability.
"""
from agents.basic_agent import BasicAgent
from agents.editor_cutweak_agent    import EditorCutweakAgent
from agents.editor_factcheck_agent  import EditorFactcheckAgent
from agents.editor_voicecheck_agent import EditorVoicecheckAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/persona-editor",
    "tier": "core",
    "trust": "community",
    "version": "0.2.0",
    "tags": ["persona", "creative-pipeline", "composite"],
    "delegates_to": [
        "@rapp/editor-cutweak",
        "@rapp/editor-factcheck",
        "@rapp/editor-voicecheck",
    ],
    "example_call": {"args": {"input": "draft text"}},
}


class PersonaEditorAgent(BasicAgent):
    def __init__(self):
        self.name = "Editor"
        self.metadata = {
            "name": self.name,
            "description": "The Editor persona. Delegates to cutweak + factcheck + "
                           "voicecheck specialist agents and composes the result.",
            "parameters": {
                "type": "object",
                "properties": {"input": {"type": "string", "description": "Writer's draft"}},
                "required": ["input"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, input="", **kwargs):
        cut    = EditorCutweakAgent().perform(input=input)
        facts  = EditorFactcheckAgent().perform(input=input)
        voice  = EditorVoicecheckAgent().perform(input=input)
        return (
            f"{cut}\n"
            f"---\n"
            f"**Editor's note**\n\n"
            f"_Sourcing flags:_\n{facts}\n\n"
            f"_Voice drift:_\n{voice}\n"
        )
