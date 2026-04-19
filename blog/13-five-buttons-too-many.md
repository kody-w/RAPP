# Five header buttons is too many

At one point the brainstem header had: **Sign in · Browse · Binder · Agents · Install · Settings**. Six entries (sign-in is conditional, but it usually shows), each with an icon and a label. On desktop it looked busy. On mobile it overflowed. On a phone in portrait you couldn't read what any of them did.

We pulled Binder and Install inside the Settings panel. The header went down to **Sign in · Browse · Agents · ⚙**.

Why those two? Because they're the least frequently used and the most "second click" in the user's mental model.

**Binder** is the full card collection. You open it when you want to look at what you have, browse the holos, or organize. That's not a frequent action during a chat session. It's something you do occasionally between sessions, or when you're showing someone the project. Hiding it inside Settings doesn't slow down anyone who's actively using the brainstem.

**Install** is even less frequent. It opens a modal showing the one-line install command for the local brainstem (or the tether). You use it once, copy the command, never come back. Putting it next to Settings makes sense — it's a configuration-level action, not a conversation-level one.

What stayed in the header:

- **Sign in** — primary call-to-action when not signed in. Disappears once you are.
- **Browse** — the agent registry / marketplace. People will come back to this often once they realize they can install agents from it.
- **Agents** — your installed agents list. Used during chat to confirm what's loaded.
- **Settings (⚙)** — the gear, where everything else lives.

Three buttons plus a gear is the pattern almost every well-designed app uses. (Slack, Linear, Discord, Notion all hover around this number for their primary nav.) Beyond three, you start sacrificing the user's ability to *scan*. Each new button takes a half-second of cognitive load to read; four buttons is two seconds; six is three; at six you've spent enough time on the header that you've forgotten what you came here to ask the chat.

The gear is the escape valve. Anything we want to expose without putting in the header gets a row in Settings. Settings has rows for:

- Provider (LLM)
- Sign-in (status)
- Execution (Live | Stub)
- Hand (Pills | Cards)
- Agent sources (registries)
- Tether (URL + status)
- More: [Binder] [Install]

The "More" row at the bottom holds the demoted buttons. They're still one click away. They just don't compete for header real estate.

Mobile collapsed everything in the header to icon-only buttons via `font-size: 0` (text labels collapse, SVG icons keep their pixel size). The rest of the layout adapts via the existing 720px breakpoint. The result: same buttons, same actions, much less visual noise.

The number of things in your header is also the number of things a new user has to learn before they can use your app. Treat it as a budget you spend reluctantly.
