# Live AI Agent Evaluation Guide

Agent Reliability Lab allows evaluating real tool-using AI agents over HTTP or OpenAI-compatible ChatCompletions APIs.

---

## 1. Quickstart: Evaluating an HTTP Agent

### Step 1: Start your HTTP Agent
Start an agent server listening for JSON requests:
```bash
# Start your agent or reference server
python examples/deterministic-http-reference-agent/agent_server.py --port 8088
```

### Step 2: Run Evaluation via CLI
```bash
# Evaluate across all 25 canonical scenarios with 3 trials each
agentlab run -s scenarios/ --agent-url http://127.0.0.1:8088 -n 3 --seed 42
```

---

## 2. Quickstart: Evaluating an OpenAI-Compatible Model

You can evaluate any endpoint supporting the standard OpenAI `/v1/chat/completions` API (e.g. OpenAI GPT-4o, Ollama, vLLM, LiteLLM, Together AI):

```bash
export OPENAI_API_KEY="sk-..."

# Run evaluation against gpt-4o-mini
agentlab run -s scenarios/ --openai-model gpt-4o-mini -n 3 --seed 42
```

Or against a local vLLM or Ollama endpoint:
```bash
agentlab run -s scenarios/ --openai-model llama3.1 --openai-base-url http://127.0.0.1:11434/v1 -n 3 --seed 42
```

---

## 3. Running Reference Demonstration

To test local infrastructure without an external agent endpoint, use `--reference-agent`:
```bash
agentlab run -s scenarios/ --reference-agent -n 3 --seed 42
```
*Note: Reference runs are explicitly marked `reference_only=true`, emit `NON_PRODUCTION_REFERENCE` reports, and do not assign production readiness verdicts.*

---

## 4. Running via MCP Server in Claude Desktop / Cursor

Add ARL to your MCP configuration:
```json
{
  "mcpServers": {
    "agent-reliability-lab": {
      "command": "agentlab-mcp",
      "args": ["--scenarios-dir", "./scenarios"]
    }
  }
}
```

Available tools in MCP:
- `list_scenarios`
- `get_scenario_spec`
- `validate_scenario_yaml`
- `run_evaluation_trial` (with `agent_url`, `openai_model`, or `reference_only`)
- `calculate_wilson_interval`
- `verify_evidence_chain`
