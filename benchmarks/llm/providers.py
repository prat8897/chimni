"""Model providers. Each one turns a request into (text, usage, stop_reason).

To add a provider (an OpenAI-compatible endpoint, say), subclass Provider, implement `complete` (and
`count_tokens` if the provider has a counting endpoint), and register it in PROVIDERS. models.yaml then
refers to it with `provider: <name>`. `usage` must use the keys in USAGE_KEYS so cost accounting works.
"""
import hashlib
import os
from dataclasses import dataclass

USAGE_KEYS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


@dataclass
class Reply:
    text: str
    usage: dict
    stop_reason: str


class Provider:
    name = "base"

    def __init__(self, model_cfg):
        self.cfg = model_cfg

    def complete(self, system, messages, max_tokens, context):
        """`context` is {"task", "condition", "sample", "attempt"}: for logging and the mock model only."""
        raise NotImplementedError

    def count_tokens(self, system, messages):
        return None


class AnthropicProvider(Provider):
    """Claude via the official `anthropic` SDK. Reads ANTHROPIC_API_KEY from the environment.

    The system prompt is cached (cache_control), so the documentation is billed at the cache-read rate after the
    first call per model and condition. Temperature is sent only when models.yaml sets one: current Claude models
    reject non-default sampling parameters. Refusal fallbacks are deliberately NOT enabled: a fallback would mix two
    models' answers into one model's score.
    """
    name = "anthropic"

    def __init__(self, model_cfg):
        super().__init__(model_cfg)
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("ANTHROPIC_API_KEY is not set. Export it, or use --dry-run.")
        import anthropic
        self.client = anthropic.Anthropic(max_retries=6)

    def _system(self, system):
        return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    def complete(self, system, messages, max_tokens, context):
        kw = {}
        if self.cfg.get("temperature") is not None:
            kw["temperature"] = self.cfg["temperature"]
        if self.cfg.get("effort"):
            kw["output_config"] = {"effort": self.cfg["effort"]}
        r = self.client.messages.create(model=self.cfg["id"], max_tokens=max_tokens, system=self._system(system),
                                        messages=messages, **kw)
        text = "".join(b.text for b in r.content if b.type == "text")
        usage = {k: getattr(r.usage, k, 0) or 0 for k in USAGE_KEYS}
        return Reply(text=text, usage=usage, stop_reason=r.stop_reason)

    def count_tokens(self, system, messages):
        kw = {"system": self._system(system)} if system else {}
        return self.client.messages.count_tokens(model=self.cfg["id"], messages=messages, **kw).input_tokens


class MockProvider(Provider):
    """A free, deterministic stand-in for --dry-run. It answers with the task's reference solution or with a
    deliberately broken one, so every failure category and the repair loop get exercised."""
    name = "mock"

    def complete(self, system, messages, max_tokens, context):
        from .common import load_tasks
        (task,) = load_tasks([context["task"]])
        cond, attempt = context["condition"], context["attempt"]
        h = int(hashlib.sha256(f"{task.id}|{cond}|{context['sample']}|{attempt}".encode()).hexdigest(), 16) % 100
        if attempt > 1:
            kind = "correct" if h < 70 else "wrong"
        else:
            kind = ("correct" if h < 55 else "static" if h < 65 else "runtime" if h < 75 else "wrong" if h < 85
                    else "timeout" if h < 90 else "extraction" if h < 95 else "decline")
        text = self._answer(task, cond, kind)
        n_in = (len(system) + sum(len(m["content"]) for m in messages)) // 4
        return Reply(text=text, usage={"input_tokens": n_in, "output_tokens": len(text) // 4 + 40,
                                       "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
                     stop_reason="end_turn")

    def _answer(self, task, cond, kind):
        lang = "chimni" if cond == "chimni" else "sql" if cond == "sql" else "python"
        p0, params = task.inputs[0], ",".join(task.inputs)
        if cond == "chimni" and (kind == "decline" or not task.expressible and kind == "correct"):
            return "CANNOT_EXPRESS: this needs an operation Chimni does not have."
        if kind == "decline":
            kind = "correct"                      # only the chimni prompt offers CANNOT_EXPRESS
        if kind == "extraction":
            return "I would approach this by grouping first, then sorting."
        if kind == "timeout" and cond == "chimni":
            kind = "static"                       # Chimni has no loops, so it cannot time out
        code = {
            "correct": task.reference_code(cond) or "",
            "static": {"chimni": "$[x]{y}\n@nope  ^\n", "sql": "SELEC 1\n"}.get(cond, "def solve(:\n"),
            "runtime": {"chimni": f"$[{params}]{{x}}\n@{p0}  *(no_such_field)  ^\n",
                        "sql": "SELECT abs(-9223372036854775808)\n"}.get(
                cond, "def solve(**kw):\n    raise ValueError('mock failure')\n"),
            "wrong": {"chimni": f"$[{params}]{{x|none}}\n@{p0}  ^\n", "sql": "SELECT 42\n"}.get(
                cond, "def solve(**kw):\n    return 42\n"),
            "timeout": {"sql": "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) "
                               "SELECT COUNT(*) FROM c\n"}.get(cond, "def solve(**kw):\n    while True:\n        pass\n"),
        }[kind]
        return f"Here is my solution.\n\n```{lang}\n{code.rstrip()}\n```\n"

    def count_tokens(self, system, messages):
        return None


PROVIDERS = {"anthropic": AnthropicProvider, "mock": MockProvider}
