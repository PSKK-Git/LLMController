from prometheus_client import Counter, Histogram

requests_total = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["model", "provider", "status"],
)

tokens_total = Counter(
    "llm_tokens_total",
    "Total tokens processed",
    ["model", "direction"],  # direction: input | output
)

cost_total = Counter(
    "llm_cost_total_usd",
    "Total cost in USD",
    ["model"],
)

request_duration = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency (gateway-observed)",
    ["model", "provider"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
)

quota_rejections_total = Counter(
    "llm_quota_rejections_total",
    "Requests rejected for exceeding a quota",
    ["quota_type"],
)
