# Why `state.settings.soul = SOUL` runs on every load

The brainstem's system prompt is canonical. It's the verbatim port of `kody-w/rapp-installer/rapp_brainstem/soul.md`, structured as XML blocks (`<identity>`, `<agent_usage>`, etc.). Every chat call uses it. There is no UI to edit it.

But there used to be. For a while, the brainstem shipped a `<textarea>` in Settings labeled "soul.md (system prompt)" that let users customize. We pulled the editor (see "Why we don't ship a soul.md editor anymore") but a problem remained: users who had customized their soul still had the *old* soul cached in `localStorage.settings.soul`. Any improvements we made to the canonical soul never reached them. They were stuck on whatever they'd typed months ago.

This was bad for two reasons:
1. **Bug fixes didn't propagate.** When we fixed the "summarize the result in plain English" bug (which was stripping markdown links), users with customized souls kept stripping links. We'd shipped the fix but they couldn't see it.
2. **The system prompt is too important to be drift-prone.** The `<agent_usage>` honesty rules — NEVER fabricate, NEVER pretend — are the difference between a model that lies about tool calls and one that doesn't. Users who'd accidentally edited those rules out had a model that would confabulate.

The fix is two lines:

```js
function loadSettings() {
  const saved = LS.get('settings', null);
  if (saved) Object.assign(state.settings, saved);
  // ... other migration code ...
  // settings.soul is ignored at chat time — buildSystemPrompt() composes the
  // prompt from canonical SOUL_* blocks + live memory read. We blank the field
  // so legacy export/import surfaces don't carry around a misleading value.
  state.settings.soul = '';
}
```

Two lines. After every load, the saved soul is overwritten with the empty string. The actual chat-time function (`buildSystemPrompt()`) ignores `state.settings.soul` entirely and composes the prompt from canonical `SOUL_*` constants compiled into the brainstem. The next time settings are persisted, the empty string gets saved — replacing the stale custom soul forever.

**Why blank instead of writing the canonical SOUL into `state.settings.soul`?**

We tried that first:
```js
state.settings.soul = SOUL;  // version 1
```

Worked, but had a downside: `state.settings.soul` then held a copy of the canonical soul. If we updated the canonical soul (added a new `<personality>` bullet, etc.), users still had the old version cached until their next page load. And `LS.set('settings', state.settings)` was now persisting a multi-KB string for no reason.

The cleaner fix: make `settings.soul` a vestigial field. It exists so legacy import/export code doesn't crash on missing keys, but nothing reads it at runtime. Empty string is fine.

**The pattern: silent migrations on load.**

The brainstem has a few of these:

```js
// Migration v2: github → copilot for users who never explicitly picked openai/custom
if (!migrated && state.settings.provider === 'github') {
  state.settings.provider = 'copilot';
  state.settings.model = PROVIDERS.copilot.defaultModel;
  LS.set('settings', state.settings);
}
LS.set('migratedToCopilot', 1);

// Migration v3: stub → live as the default execution mode
const liveMig = LS.get('migratedToLive', 0);
if (!liveMig && state.settings.execMode === 'stub') {
  state.settings.execMode = 'live';
  LS.set('settings', state.settings);
}
LS.set('migratedToLive', 1);

// Migration v4 (the soul reset above)
state.settings.soul = '';
```

Each migration:
- Runs once per browser, gated by a `migrated*` flag in localStorage.
- Touches *only* the field it's responsible for.
- Is silent. The user doesn't see "your settings have been updated."
- Persists the change so it survives refreshes.

The soul reset is special: it runs on EVERY load (not gated by a flag) because the soul is the kind of thing where "stale" is always wrong. If a user manages to put something into `state.settings.soul` somehow (an export-then-import dance), the next load wipes it.

**The lesson:**

When you change defaults that users have customized, you have three choices:

1. **Honor the customization forever.** Standard. But you lose the ability to fix bugs in the default for those users.
2. **Force the new default once, via an explicit migration.** Honest. The user sees their settings reset; you write a one-time toast saying "we updated this for everyone." Heavy-handed.
3. **Make the field vestigial; ignore it at runtime.** What we did. The customization persists in storage but never executes. Users who want customization can fork the brainstem (one HTML file). Users who don't get the canonical default forever.

For settings that are critical (system prompts, security boundaries, default models), option 3 is often right. For settings that are genuinely a matter of taste (theme, font size, hand display mode), option 1 is right. The distinction is "would a user be surprised that this didn't update?" If yes, option 3.
