# Dual Recall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second UserPromptSubmit hook (`local-recall.mjs`) that calls Sonnet API to extract relevant context from TOOLS.md, AGENTS.md, and LEARNINGS.md on every user message, parallel with existing OV auto-recall.

**Architecture:** New Node.js script reads 3 local files, sends them to Anthropic Sonnet API with user's prompt, receives relevant lines back, returns as `<local-context>` in additionalContext. Runs parallel with existing `auto-recall.mjs`. Falls back gracefully on error.

**Tech Stack:** Node.js (ESM), Anthropic SDK (`@anthropic-ai/sdk`), existing config infrastructure from {{MEMORY_SERVICE}} plugin.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `~/{{MEMORY_PLUGIN_DIR}}/scripts/local-recall.mjs` | Create | Main hook script -- read files, call Sonnet, return context |
| `~/{{MEMORY_PLUGIN_DIR}}/scripts/local-recall-config.mjs` | Create | Config loader for local-recall (workspace path, model, timeout) |
| `~/{{AGENT_LAB_DIR}}/{{AGENT_ID}}/.claude/settings.json` | Modify | Add second hook to UserPromptSubmit |
| `~/{{AGENT_LAB_DIR}}/{{AGENT_2_ID}}/.claude/settings.json` | Modify | Same hook for {{AGENT_2_NAME}} (scaling) |

---

### Task 1: Install Anthropic SDK

**Files:**
- Modify: `~/{{MEMORY_PLUGIN_DIR}}/package.json`

- [ ] **Step 1: Check if SDK already installed**

```bash
cd ~/{{MEMORY_PLUGIN_DIR}} && cat package.json | grep anthropic
```

Expected: no match (SDK not yet installed)

- [ ] **Step 2: Install Anthropic SDK**

```bash
cd ~/{{MEMORY_PLUGIN_DIR}} && npm install @anthropic-ai/sdk
```

Expected: added @anthropic-ai/sdk to dependencies

- [ ] **Step 3: Verify installation**

```bash
cd ~/{{MEMORY_PLUGIN_DIR}} && node -e "import('@anthropic-ai/sdk').then(m => console.log('OK:', Object.keys(m).slice(0,3)))"
```

Expected: OK: [Anthropic, ...]

- [ ] **Step 4: Commit**

```bash
cd ~/{{MEMORY_PLUGIN_DIR}} && git add package.json package-lock.json && git commit -m "feat: add @anthropic-ai/sdk for local-recall hook"
```

---

### Task 2: Create local-recall-config.mjs

**Files:**
- Create: `~/{{MEMORY_PLUGIN_DIR}}/scripts/local-recall-config.mjs`

- [ ] **Step 1: Create config loader**

```javascript
import { homedir } from "node:os";
import { join } from "node:path";

export function loadLocalRecallConfig() {
  const home = homedir();
  const agentWorkspace = process.env.CLAUDE_PROJECT_DIR
    || join(home, "{{AGENT_LAB_DIR}}", "{{AGENT_ID}}", ".claude");

  return {
    agentWorkspace,
    toolsPath: join(agentWorkspace, "tools", "TOOLS.md"),
    agentsPath: join(agentWorkspace, "core", "AGENTS.md"),
    learningsPath: join(agentWorkspace, "core", "LEARNINGS.md"),
    model: process.env.LOCAL_RECALL_MODEL || "claude-sonnet-4-6",
    maxTokens: 500,
    temperature: 0,
    timeoutMs: 9000,
    minQueryLength: 3,
  };
}
```

- [ ] **Step 2: Verify it loads without errors**

```bash
cd ~/{{MEMORY_PLUGIN_DIR}} && node -e "
  import { loadLocalRecallConfig } from './scripts/local-recall-config.mjs';
  const c = loadLocalRecallConfig();
  console.log('workspace:', c.agentWorkspace);
  console.log('model:', c.model);
  console.log('tools:', c.toolsPath);
"
```

Expected: prints workspace path, model name, tools path

- [ ] **Step 3: Commit**

```bash
cd ~/{{MEMORY_PLUGIN_DIR}} && git add scripts/local-recall-config.mjs && git commit -m "feat: add config loader for local-recall hook"
```

---

### Task 3: Create local-recall.mjs

**Files:**
- Create: `~/{{MEMORY_PLUGIN_DIR}}/scripts/local-recall.mjs`

- [ ] **Step 1: Create the hook script**

```javascript
#!/usr/bin/env node

import { readFileSync } from "node:fs";
import Anthropic from "@anthropic-ai/sdk";
import { loadLocalRecallConfig } from "./local-recall-config.mjs";
import { createLogger } from "./debug-log.mjs";

const cfg = loadLocalRecallConfig();
const { log, logError } = createLogger("local-recall");

function output(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}

function approve(msg) {
  const out = { decision: "approve" };
  if (msg) {
    out.hookSpecificOutput = {
      hookEventName: "UserPromptSubmit",
      additionalContext: msg,
    };
  }
  output(out);
}

function readFileSafe(path) {
  try {
    return readFileSync(path, "utf-8");
  } catch {
    return null;
  }
}

async function main() {
  let input;
  try {
    const chunks = [];
    for await (const chunk of process.stdin) chunks.push(chunk);
    input = JSON.parse(Buffer.concat(chunks).toString());
  } catch {
    log("skip", { reason: "invalid stdin" });
    approve();
    return;
  }

  const userPrompt = (input.prompt || "").trim();
  if (!userPrompt || userPrompt.length < cfg.minQueryLength) {
    log("skip", { reason: "query too short" });
    approve();
    return;
  }

  log("start", { query: userPrompt.slice(0, 200), model: cfg.model });

  const tools = readFileSafe(cfg.toolsPath);
  const agents = readFileSafe(cfg.agentsPath);
  const learnings = readFileSafe(cfg.learningsPath);

  if (!tools && !agents && !learnings) {
    log("skip", { reason: "no reference files found" });
    approve("<local-recall-failed reason=\"no files\"/>");
    return;
  }

  const fileSections = [
    tools ? `---TOOLS.MD---\n${tools}` : null,
    agents ? `---AGENTS.MD---\n${agents}` : null,
    learnings ? `---LEARNINGS.MD---\n${learnings}` : null,
  ].filter(Boolean).join("\n\n");

  const client = new Anthropic();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), cfg.timeoutMs);

  try {
    const response = await client.messages.create({
      model: cfg.model,
      max_tokens: cfg.maxTokens,
      temperature: cfg.temperature,
      system: "You are a context extractor for an AI agent. From the provided reference files, find ONLY lines relevant to the user's query. Return 5-15 lines max. Keep exact values (IPs, ports, paths, commands). If nothing is relevant, return exactly: NONE",
      messages: [
        {
          role: "user",
          content: `Query: ${userPrompt}\n\n${fileSections}`,
        },
      ],
    }, { signal: controller.signal });

    const text = response.content[0]?.text?.trim() || "";

    if (!text || text === "NONE") {
      log("result", { status: "no_relevant_context" });
      approve();
      return;
    }

    log("result", { status: "context_found", length: text.length });

    const context =
      "<local-context source=\"TOOLS.md, AGENTS.md, LEARNINGS.md\">\n" +
      text + "\n" +
      "</local-context>";

    approve(context);
  } catch (err) {
    logError("sonnet_call", err?.message || err);
    approve("<local-recall-failed reason=\"api_error\"/>");
  } finally {
    clearTimeout(timer);
  }
}

main().catch((err) => {
  logError("uncaught", err);
  approve("<local-recall-failed reason=\"uncaught_error\"/>");
});
```

- [ ] **Step 2: Make executable**

```bash
chmod +x ~/{{MEMORY_PLUGIN_DIR}}/scripts/local-recall.mjs
```

- [ ] **Step 3: Test with mock input**

```bash
cd ~/{{MEMORY_PLUGIN_DIR}} && echo '{"prompt":"what is the server IP"}' | ANTHROPIC_API_KEY=$(grep -o 'sk-ant-[^"]*' ~/{{AGENT_LAB_DIR}}/.secrets/{{API_KEY_FILE}} 2>/dev/null || echo "$ANTHROPIC_API_KEY") node scripts/local-recall.mjs
```

Expected: JSON with `decision: "approve"` and `additionalContext` containing `<local-context>` with server IP info

- [ ] **Step 4: Test with empty input (graceful skip)**

```bash
cd ~/{{MEMORY_PLUGIN_DIR}} && echo '{"prompt":""}' | node scripts/local-recall.mjs
```

Expected: `{"decision":"approve"}` (no additionalContext, no error)

- [ ] **Step 5: Test with no files (graceful fallback)**

```bash
cd ~/{{MEMORY_PLUGIN_DIR}} && echo '{"prompt":"test query"}' | CLAUDE_PROJECT_DIR=/tmp/nonexistent node scripts/local-recall.mjs
```

Expected: `{"decision":"approve"}` with `<local-recall-failed reason="no files"/>`

- [ ] **Step 6: Commit**

```bash
cd ~/{{MEMORY_PLUGIN_DIR}} && git add scripts/local-recall.mjs && git commit -m "feat: add local-recall hook -- Sonnet-powered context extraction from TOOLS/AGENTS/LEARNINGS"
```

---

### Task 4: Add hook to {{AGENT_NAME}} settings.json

**Files:**
- Modify: `~/{{AGENT_LAB_DIR}}/{{AGENT_ID}}/.claude/settings.json` (line 16-27)

- [ ] **Step 1: Add local-recall.mjs as second hook in UserPromptSubmit**

Replace the current UserPromptSubmit section:

```json
"UserPromptSubmit": [
  {
    "matcher": "",
    "hooks": [
      {
        "type": "command",
        "command": "node $HOME/{{MEMORY_PLUGIN_DIR}}/scripts/auto-recall.mjs",
        "timeout": 8
      }
    ]
  }
]
```

With:

```json
"UserPromptSubmit": [
  {
    "matcher": "",
    "hooks": [
      {
        "type": "command",
        "command": "node $HOME/{{MEMORY_PLUGIN_DIR}}/scripts/auto-recall.mjs",
        "timeout": 8
      },
      {
        "type": "command",
        "command": "node $HOME/{{MEMORY_PLUGIN_DIR}}/scripts/local-recall.mjs",
        "timeout": 10
      }
    ]
  }
]
```

- [ ] **Step 2: Validate JSON syntax**

```bash
python3 -c "import json; json.load(open('$HOME/{{AGENT_LAB_DIR}}/{{AGENT_ID}}/.claude/settings.json')); print('JSON valid')"
```

Expected: JSON valid

- [ ] **Step 3: Commit**

```bash
cd ~/{{AGENT_LAB_DIR}}/{{AGENT_ID}}/.claude && git add settings.json && git commit -m "feat: add local-recall hook to UserPromptSubmit (dual recall)"
```

---

### Task 5: Add hook to {{AGENT_2_NAME}} settings.json

**Files:**
- Modify: `~/{{AGENT_LAB_DIR}}/{{AGENT_2_ID}}/.claude/settings.json`

- [ ] **Step 1: Check if {{AGENT_2_NAME}} has settings.json with UserPromptSubmit**

```bash
cat ~/{{AGENT_LAB_DIR}}/{{AGENT_2_ID}}/.claude/settings.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('hooks' in d.get('hooks',{}).get('UserPromptSubmit',[{}])[0])" 2>/dev/null || echo "NO_SETTINGS"
```

- [ ] **Step 2: Add local-recall hook (same as {{AGENT_NAME}})**

Add the same second hook entry to {{AGENT_2_NAME}} UserPromptSubmit section. The `CLAUDE_PROJECT_DIR` env var will automatically point to {{AGENT_2_NAME}} workspace.

- [ ] **Step 3: Validate JSON**

```bash
python3 -c "import json; json.load(open('$HOME/{{AGENT_LAB_DIR}}/{{AGENT_2_ID}}/.claude/settings.json')); print('JSON valid')"
```

- [ ] **Step 4: Commit**

```bash
cd ~/{{AGENT_LAB_DIR}}/{{AGENT_2_ID}}/.claude && git add settings.json && git commit -m "feat: add local-recall hook to {{AGENT_2_NAME}} (dual recall)"
```

---

### Task 6: End-to-end test via Telegram

**Files:** None (manual verification)

- [ ] **Step 1: Send technical message to {{AGENT_NAME}} in Telegram**

Send: "what port does {{MEMORY_SERVICE}} run on?"

Expected: {{AGENT_NAME}} responds with correct port ({{MEMORY_SERVICE_PORT}}) without using Read tool -- context came from local-recall hook.

- [ ] **Step 2: Check debug logs**

```bash
tail -20 ~/{{MEMORY_PLUGIN_DIR}}/logs/cc-hooks.log | grep local-recall
```

Expected: log entries showing `local-recall start`, `result`, `context_found`

- [ ] **Step 3: Send non-technical message**

Send: "how are you?"

Expected: {{AGENT_NAME}} responds normally. local-recall returns NONE or empty context (no wasted tokens on irrelevant queries).

- [ ] **Step 4: Test fallback -- temporarily break API key**

```bash
ANTHROPIC_API_KEY=invalid echo '{"prompt":"test"}' | node ~/{{MEMORY_PLUGIN_DIR}}/scripts/local-recall.mjs
```

Expected: `{"decision":"approve"}` with `<local-recall-failed reason="api_error"/>` -- graceful degradation, no crash.

---

### Task 7: Update public architecture docs

**Files:**
- Modify: `/tmp/public-arch-review/HOOKS.md`
- Modify: `/tmp/public-arch-review/MEMORY.md`

- [ ] **Step 1: Add local-recall to HOOKS.md**

Add to the UserPromptSubmit section:

```markdown
### local-recall.mjs (Sonnet context extraction)

- **Trigger:** UserPromptSubmit (parallel with auto-recall)
- **What:** Reads TOOLS.md + AGENTS.md + LEARNINGS.md, sends to Sonnet API, returns relevant lines as `<local-context>`
- **Timeout:** 10 seconds
- **Fallback:** Returns `<local-recall-failed/>` on error -- agent uses Opus Read tool as one-time backup
- **Cost:** ~$0.015 per message (Sonnet input ~4K tokens + output ~300 tokens)
```

- [ ] **Step 2: Update MEMORY.md architecture diagram**

Add to the "Every message" section:

```
Every message (parallel hooks):
  +-- auto-recall.mjs --> OV semantic search --> <relevant-memories>
  +-- local-recall.mjs --> Sonnet API --> <local-context>
```

- [ ] **Step 3: Commit and push**

```bash
cd /tmp/public-arch-review && git add HOOKS.md MEMORY.md && git commit -m "docs: add local-recall hook to architecture docs" && git push origin main
```
