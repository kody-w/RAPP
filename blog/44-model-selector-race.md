# The model selector that forgot what you picked

The brainstem has a model dropdown in its header. You pick `claude-opus-4-7-1m` from the Copilot catalog. The chat works. You refresh the page. The dropdown is back to `gpt-4o`. You sigh, pick Opus again, send another message. Refresh. `gpt-4o` again.

This bug lived for about a week before someone (me) noticed it was a bug and not just "Claude is the wrong default."

The cause was a race between two functions, both running at boot:

```js
function loadSettings() {
  const saved = LS.get('settings', null);
  if (saved) Object.assign(state.settings, saved);  // restores model = 'claude-opus-4-7-1m'
  // ... more setup ...
  refreshModelOptions();   // ← this is the bug
}

function refreshModelOptions() {
  const sel = $('#model-sel');
  sel.innerHTML = '';
  for (const m of PROVIDERS[state.settings.provider].models) {
    const o = document.createElement('option');
    o.value = m.id; o.textContent = m.name;
    sel.appendChild(o);
  }
  // The "fix it back to default" line:
  if (!PROVIDERS[state.settings.provider].models.find(m => m.id === state.settings.model)) {
    state.settings.model = PROVIDERS[state.settings.provider].defaultModel;  // bug
  }
  sel.value = state.settings.model;
}
```

The flow:

1. `loadSettings()` restores `state.settings.model = 'claude-opus-4-7-1m'` from localStorage. ✓
2. `refreshModelOptions()` runs *synchronously* with the static `PROVIDERS.copilot.models` list — which only has a few hardcoded defaults like `gpt-4o`. The full Copilot catalog (138 models) is fetched asynchronously and hasn't arrived yet.
3. The check `if (!PROVIDERS[provider].models.find(m => m.id === state.settings.model))` is true — Opus isn't in the static list yet.
4. Bug: the function *overwrites* `state.settings.model` to the static default `gpt-4o`.
5. Asynchronously, `fetchCopilotModels()` returns with the full catalog. It calls `refreshModelOptions()` again.
6. Now Opus is in the list, but `state.settings.model` is already `gpt-4o` (from step 4). The dropdown selects `gpt-4o`.

The user picked Opus. The dropdown shows GPT. The model used for the next chat is GPT.

**The fix:**

Don't overwrite `state.settings.model` in `refreshModelOptions`. If the saved model isn't in the current option list, append it as a placeholder so the dropdown still reflects the user's pick:

```js
function refreshModelOptions() {
  const sel = $('#model-sel');
  const provider = PROVIDERS[state.settings.provider];
  sel.innerHTML = '';
  for (const m of provider.models) {
    const o = document.createElement('option');
    o.value = m.id; o.textContent = m.name;
    sel.appendChild(o);
  }
  // Preserve the user's saved choice even when the static defaults don't
  // include it yet. The async catalog fetch will repopulate shortly.
  const saved = state.settings.model;
  if (saved && !provider.models.find(m => m.id === saved)) {
    const o = document.createElement('option');
    o.value = saved; o.textContent = `${saved} (loading…)`;
    sel.appendChild(o);
  }
  sel.value = saved || provider.defaultModel;
}
```

The dropdown briefly shows `claude-opus-4-7-1m (loading…)` while the Copilot catalog fetches. When the catalog arrives, the next `refreshModelOptions()` call replaces the option list with proper labels — the user's choice stays selected the whole time.

**Why this took a week to find:**

The bug only reproduced when:
- Provider is Copilot (which is the default).
- The user had picked a model not in the small static defaults list (i.e., anything except `gpt-4o`).
- The user had refreshed the page since picking.

If you only ever used `gpt-4o` you never saw it. If you didn't refresh between picking and using, you never saw it. That's a small slice of users hitting a 100% reproducible bug, which felt like "something flaky" until I sat down with it.

**Two lessons:**

**One: be suspicious of code that overwrites user state.** Any time you see `state.settings.x = default` in code that's not explicitly the "reset to defaults" path, ask why. The model setter is "use the user's choice"; defaults are for when there's no user choice. Don't blur them.

**Two: race conditions between sync and async are real even in a single-threaded JS runtime.** Sync code runs to completion before any async callback fires. That's exactly the problem here — `refreshModelOptions` ran synchronously, reset the model, then the async `fetchCopilotModels` arrived too late. You can't outrun the sync code from an async context. Design for the order of events, don't hope for it.

The fix shipped as commit `62beb20` — about ten lines added and removed. The dropdown now remembers what you picked, every time.
