# API and configuration

This is a documented OpenAI chat-completions subset, not full API compatibility. The server is stateless. Allowed roles are system (first message only), user, assistant; the last message must be user. Tool messages/calls, images, audio, multipart, temperature and undeclared parameters return 422. Tool relationships are therefore rejected rather than silently flattened.

| Endpoint | Contract |
|---|---|
| GET /health/live | Unauthenticated liveness, no internal detail |
| GET /health/ready | 200 after pinned model warmup; 503 while unavailable |
| GET /v1/models | Protected public API model `omo`; no provider secrets/endpoints |
| POST /v1/route | Protected bounded route inspection; no execution; excludes helper arguments |
| POST /v1/chat/completions | Protected non-streaming or buffered SSE delivery |
| GET /metrics | Protected fixed action/error counters; no content or user labels |

Authentication is a bearer API key with minimum 24 characters when configured. Without it, only actual loopback peers are accepted; forwarded headers do not establish caller identity. Binding beyond loopback without a key fails at startup. This single-key identity is not a multi-tenant authorization system. No CORS middleware or public docs endpoint is enabled.

Request fields: `model` is `omo`, `messages` required, `stream` boolean, `max_tokens` 8–256 (default 96), optional `omo` object:

```json
{"schema_version":"1","local_only":false,"action":"auto","required_capability":"text","max_cost_usd":0.0}
```

Actions supported as explicit overrides: auto, local_answer, helper, external_model. A helper override requires `helper` and only it may carry helper arguments. External use requires administrator enablement, an eligible registry entry, a provider key, and an explicit positive request budget. `local_only` can tighten administrator policy, never loosen it.

Helpers:

```json
{"action":"helper","helper":{"id":"decimal","operation":"add","a":"0.10","b":"0.20","unit":"AED"}}
```

```json
{"action":"helper","helper":{"id":"even_squares","values":[1,2,3,4]}}
```

Decimal operands are bounded decimal strings. No float coercion, exponent notation or arbitrary expression evaluation. Supported units: empty, AED, USD, kg, m, s. Add/subtract preserve a common supplied unit; compound multiplication/division units and non-terminating division are explicitly unsupported. `calc 0.1 + 0.2` is a full-command grammar available only in a single user turn. The sandbox helper accepts at most 128 integers in [-10000,10000], validates the result independently, and never receives credentials or raw conversation history.

Bounds: 32 KiB HTTP body, 16 KiB conversation content, 24 messages, 768 analysis tokens, 2048 local context including output reserve, four pending inference calls, eight API requests in flight, 120 requests/minute, 20 s end-to-end deadline. Oversized analysis is rejected explicitly. External forwarding preserves the entire validated conversation; no hidden truncation occurs. Provider input estimate is a conservative UTF-8 byte bound plus framing; configuring tokenizers that violate that bound is unsupported.

Streaming is **buffered delivery**, not token-by-token provider inference. OMO finishes/validates the complete result before emitting SSE chunks of at most 256 characters, a final usage/metadata event and `[DONE]`. Generation errors arrive before the first chunk. No provider fallback/splicing happens after output begins. Client cancellation closes pending work; delivery has a 5 s bound. Native upstream streaming/resume is deferred.

Responses include the actual execution action/executor, reason, model/policy/registry versions, usage when observed, provider attempts, timings and safe status. `confidence` is null and calibration is uncalibrated. Estimated cost is not observed billing. A deterministic policy rejection is a chat response with `omo.status=policy-denied`; transport/configuration/generation faults use structured HTTP errors. Provider codes distinguish bad request, authentication, authorization, quota, model unavailable, rate-limit, timeout, transport and malformed response. Only explicit 429 rejections get one jittered retry; ambiguous paid requests are not replayed.

Precedence: defaults < YAML (`--config`) < `OMO_` environment < explicit CLI `--host`/`--port`. Unknown names and invalid scalar types fail. No automatic dotenv loading. `OMO_PROVIDER_KEY_*` is reserved for administrator registry references. See config/default.yaml and the generated JSON schemas under config/. Registry reload is a tested Python API with validate-before-swap; an HTTP administration endpoint is intentionally absent. Registry entries are immutable per request.
