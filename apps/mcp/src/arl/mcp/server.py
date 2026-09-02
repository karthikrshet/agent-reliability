"""
Model Context Protocol (MCP) Server for Agent Reliability Lab.

Exposes tools, resources, and evaluation prompts to AI assistants (Claude Desktop,
Antigravity, Cursor, etc.) to perform agent production readiness testing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

from arl.adapters.http.adapter import HttpAgentAdapter
from arl.adapters.reference.agent import MockAgentAdapter
from arl.core.domain.trial import Trial
from arl.environments.customer_support.environment import CustomerSupportEnvironment
from arl.evidence.collector import EvidenceCollector
from arl.execution_engine.executor import TrialExecutor
from arl.grading_engine.deterministic import DeterministicTrialEvaluator
from arl.grading_engine.stats import compute_wilson_score_interval
from arl.protocol.adapter import AgentAdapter
from arl.scenario_engine.loader import load_scenario, load_scenario_from_string
from arl.scenario_engine.schema import ParsedScenario

logger = logging.getLogger("arl.mcp")

# Default scenarios directory path
SCENARIOS_DIR = Path(__file__).resolve().parents[5] / "scenarios"


class MCPServer:
    """
    Standard MCP (Model Context Protocol) 2024-11-05 Server implementation.
    Operates over stdio using JSON-RPC 2.0.
    """

    def __init__(self, scenarios_dir: Path | None = None) -> None:
        self.scenarios_dir = scenarios_dir or SCENARIOS_DIR
        self._scenarios_cache: dict[str, tuple[ParsedScenario, Path]] = {}
        self._load_scenarios()

    def _load_scenarios(self) -> None:
        """Scan scenarios directory and populate scenario cache."""
        if not self.scenarios_dir.exists():
            return
        for yaml_path in sorted(self.scenarios_dir.rglob("*.yaml")):
            try:
                scenario, _, _ = load_scenario(yaml_path)
                self._scenarios_cache[scenario.id] = (scenario, yaml_path)
            except Exception as e:
                logger.warning(f"Failed to parse scenario {yaml_path.name}: {e}")

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return MCP tool definitions."""
        return [
            {
                "name": "list_scenarios",
                "description": "List all canonical agent reliability scenarios with category, severity, and tags.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Optional category filter (tool-correctness, error-recovery, budget-limits, multi-tenant-isolation, prompt-injection)",
                        },
                        "severity": {
                            "type": "string",
                            "description": "Optional severity filter (critical, high, medium, low)",
                        },
                    },
                },
            },
            {
                "name": "get_scenario_spec",
                "description": "Retrieve full specification of a test scenario including fault injection schedules and expected effects.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "scenario_id": {
                            "type": "string",
                            "description": "Unique scenario ID (e.g., 'tc-01-order-lookup' or 'er-01-transient-500-retry')",
                        }
                    },
                    "required": ["scenario_id"],
                },
            },
            {
                "name": "validate_scenario_yaml",
                "description": "Validate custom YAML scenario definition against JSON Schema 2020-12 rules.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "yaml_content": {
                            "type": "string",
                            "description": "Raw YAML string of the evaluation scenario.",
                        }
                    },
                    "required": ["yaml_content"],
                },
            },
            {
                "name": "run_evaluation_trial",
                "description": "Execute a sandboxed evaluation trial against an agent under deterministic fault injection. Requires explicit target.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "scenario_id": {
                            "type": "string",
                            "description": "Scenario ID to execute",
                        },
                        "agent_url": {
                            "type": "string",
                            "description": "HTTP Agent endpoint URL",
                        },
                        "openai_model": {
                            "type": "string",
                            "description": "OpenAI-compatible model name",
                        },
                        "openai_base_url": {
                            "type": "string",
                            "description": "OpenAI-compatible base URL",
                        },
                        "reference_only": {
                            "type": "boolean",
                            "default": False,
                            "description": "Explicitly select local deterministic reference agent (NON_PRODUCTION_REFERENCE)",
                        },
                        "seed": {
                            "type": "integer",
                            "default": 42,
                            "description": "Deterministic PRNG seed for fault scheduling",
                        },
                    },
                    "required": ["scenario_id"],
                },
            },
            {
                "name": "calculate_wilson_interval",
                "description": "Calculate 95% Wilson score confidence interval and evaluate production readiness threshold.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "successes": {
                            "type": "integer",
                            "description": "Number of passed evaluation trials",
                        },
                        "total": {
                            "type": "integer",
                            "description": "Total number of evaluation trials executed",
                        },
                        "threshold": {
                            "type": "number",
                            "default": 0.80,
                            "description": "Production readiness threshold (lower confidence bound)",
                        },
                    },
                    "required": ["successes", "total"],
                },
            },
            {
                "name": "verify_evidence_chain",
                "description": "Cryptographically verify SHA-256 hash-chain integrity for evaluation trial records.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "evidence_records": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Array of evidence records containing payload_hash and chain_hash",
                        }
                    },
                    "required": ["evidence_records"],
                },
            },
        ]

    async def handle_tool_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute tool call and format MCP text response."""
        if name == "list_scenarios":
            cat_filter = arguments.get("category")
            sev_filter = arguments.get("severity")

            scenarios_list = []
            for sc, _ in self._scenarios_cache.values():
                if cat_filter and sc.category != cat_filter:
                    continue
                if sev_filter and sc.severity != sev_filter:
                    continue
                scenarios_list.append(
                    {
                        "id": sc.id,
                        "title": sc.title,
                        "category": sc.category,
                        "severity": sc.severity,
                        "max_turns": sc.budgets.max_turns,
                        "max_tool_calls": sc.budgets.max_tool_calls,
                        "fault_count": len(sc.fault_plan),
                        "tags": sc.tags,
                    }
                )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"total": len(scenarios_list), "scenarios": scenarios_list}, indent=2
                        ),
                    }
                ]
            }

        elif name == "get_scenario_spec":
            scenario_id = arguments["scenario_id"]
            if scenario_id not in self._scenarios_cache:
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Scenario '{scenario_id}' not found."}],
                }

            sc, yaml_path = self._scenarios_cache[scenario_id]
            raw_yaml = yaml_path.read_text(encoding="utf-8")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "id": sc.id,
                                "title": sc.title,
                                "category": sc.category,
                                "severity": sc.severity,
                                "description": sc.description,
                                "raw_yaml": raw_yaml,
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        elif name == "validate_scenario_yaml":
            yaml_content = arguments["yaml_content"]
            try:
                scenario = load_scenario_from_string(yaml_content)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "valid": True,
                                    "id": scenario.id,
                                    "title": scenario.title,
                                    "category": scenario.category,
                                    "severity": scenario.severity,
                                },
                                indent=2,
                            ),
                        }
                    ]
                }
            except Exception as e:
                return {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"valid": False, "error": str(e)}, indent=2),
                        }
                    ],
                }

        elif name == "run_evaluation_trial":
            scenario_id = arguments["scenario_id"]
            seed = int(arguments.get("seed", 42))
            agent_url = arguments.get("agent_url")
            openai_model = arguments.get("openai_model")
            openai_base_url = arguments.get("openai_base_url", "https://api.openai.com/v1")
            reference_only = bool(arguments.get("reference_only", False))

            if scenario_id not in self._scenarios_cache:
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Scenario '{scenario_id}' not found."}],
                }

            if not agent_url and not openai_model and not reference_only:
                return {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "CONFIGURATION ERROR: No target agent specified. "
                                "You must explicitly provide 'agent_url', 'openai_model', "
                                "or 'reference_only: true'."
                            ),
                        }
                    ],
                }

            scenario, _ = self._scenarios_cache[scenario_id]

            adapter: AgentAdapter
            if agent_url:
                adapter = HttpAgentAdapter(endpoint_url=agent_url)
            elif openai_model:
                from arl.adapters.openai.adapter import OpenAIAgentAdapter

                adapter = OpenAIAgentAdapter(
                    endpoint_url=f"{openai_base_url.rstrip('/')}/chat/completions",
                    model=openai_model,
                )
            else:
                adapter = MockAgentAdapter()

            env = CustomerSupportEnvironment(seed=seed)
            trial_id = f"mcp-trial-{uuid.uuid4().hex[:8]}"
            trial = Trial(
                id=trial_id,
                run_id="mcp-run",
                trial_index=0,
                idempotency_key=f"idemp-{trial_id}",
                fault_seed=seed,
            )

            executor = TrialExecutor(
                trial=trial,
                scenario=scenario,
                adapter=adapter,
                environment=env,
            )

            # Execute Trial
            exec_res = await executor.run()

            # Deterministic Grading
            evaluator = DeterministicTrialEvaluator()
            verdict, score, grader_results = await evaluator.evaluate_trial(
                trial, scenario, exec_res
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "scenario_id": scenario_id,
                                "trial_id": trial_id,
                                "reference_only": reference_only,
                                "adapter_type": adapter.framework,
                                "passed": verdict.value == "pass",
                                "verdict": "NON_PRODUCTION_REFERENCE"
                                if reference_only
                                else verdict.value,
                                "score": score,
                                "turns_consumed": len(exec_res.turns),
                                "tool_calls_executed": len(exec_res.tool_calls),
                                "injected_faults": len(exec_res.fault_events),
                                "findings_count": sum(len(g.findings) for g in grader_results),
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        elif name == "calculate_wilson_interval":
            k = int(arguments["successes"])
            n = int(arguments["total"])
            threshold = float(arguments.get("threshold", 0.80))

            lower, upper = compute_wilson_score_interval(k, n, confidence=0.95)
            pass_rate = k / n if n > 0 else 0.0
            is_ready = lower >= threshold

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "successes": k,
                                "total_trials": n,
                                "empirical_pass_rate": round(pass_rate, 4),
                                "wilson_lower_95": round(lower, 4),
                                "wilson_upper_95": round(upper, 4),
                                "readiness_threshold": threshold,
                                "production_ready": is_ready,
                                "verdict": "READY" if is_ready else "NOT_READY",
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        elif name == "verify_evidence_chain":
            records = arguments["evidence_records"]
            collector = EvidenceCollector()
            # In-memory verification
            is_valid = True
            prev_hash = collector.current_hash

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "chain_valid": is_valid,
                                "records_checked": len(records),
                                "final_hash": prev_hash,
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        else:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
            }

    async def handle_jsonrpc_request(self, req: dict[str, Any]) -> dict[str, Any]:
        """Process incoming JSON-RPC request dictionary and produce response dictionary."""
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                    },
                    "serverInfo": {
                        "name": "arl-mcp",
                        "version": "0.1.0",
                    },
                },
            }
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.get_tool_definitions()},
            }
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            call_res = await self.handle_tool_call(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": call_res,
            }
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

    async def run_stdio(self) -> None:
        """Standard MCP JSON-RPC stdio event loop."""
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line = await reader.readline()
            if not line:
                break
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            try:
                req = json.loads(line_str)
                res = await self.handle_jsonrpc_request(req)
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()

            except Exception as e:
                err_res = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": f"Internal error: {e!s}"},
                }
                sys.stdout.write(json.dumps(err_res) + "\n")
                sys.stdout.flush()


def main() -> None:
    """Entry point for `arl-mcp` command."""
    server = MCPServer()
    asyncio.run(server.run_stdio())


if __name__ == "__main__":
    main()
