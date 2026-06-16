# Rate Limit Stress Scripts

This directory contains standalone behavioral stress tests for the Memories API rate limiter.
These are not pytest tests. They intentionally generate request bursts and timing-sensitive load
against a running local server.

The script focuses on the four scenarios agreed for realistic agent use and overload behavior:

- `mixed`: a normal mixed agent workload. For REST, this combines reads, writes, and batch writes
  at a paced interval. For MCP, this sends paced MCP HTTP requests. This replaces a separate
  "normal session" test and gives a practical baseline for expected agent usage.
- `fast`: a single agent making requests as fast as possible. For REST, it sends read and write
  requests with no delay. For MCP, it sends MCP HTTP requests with no delay.
- `flood`: a concurrent burst from one client. This models a broken loop, runaway agent, or many
  parallel tool calls.
- `two-agent`: a normal client and a runaway client at the same time using different
  `X-Client-Id` values. This checks that a flooded client identity does not consume another
  client's quota.

Each scenario can run against both surfaces:

- `rest`: memory HTTP routes such as `GET /memories`, `POST /memories`, and
  `POST /memories/batch`.
- `mcp`: the MCP streamable HTTP endpoint under `/mcp/`.

For MCP, the stress script sends lightweight `POST /mcp/` requests. The rate limiter runs before
MCP transport parsing, so these requests are enough to test rate-limit accept/deny behavior without
implementing a full MCP client handshake. The report treats any non-`429` status as accepted by the
limiter.

## Run

Start the API against a disposable database:

```powershell
$env:MEMORIES_DB_FILE="$env:TEMP\memories-rate-limit-stress.db"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another shell:

```powershell
python scripts\rate_limit_stress.py
```

The script writes an HTML report to `scripts\rate_limit_report.html` by default. The report includes
summary totals, per-scenario accepted and denied counts, raw status counts, and simple distribution
bars.

## Useful Options

Run only REST:

```powershell
python scripts\rate_limit_stress.py --surfaces rest
```

Run only MCP:

```powershell
python scripts\rate_limit_stress.py --surfaces mcp
```

Run selected scenarios:

```powershell
python scripts\rate_limit_stress.py --scenarios mixed,fast
```

Point at a different server:

```powershell
python scripts\rate_limit_stress.py --base-url http://127.0.0.1:8010
```

Write the report somewhere else:

```powershell
python scripts\rate_limit_stress.py --output reports\rate-limit-smoke.html
```

Lower the API limits before starting the server to make denials happen quickly:

```powershell
$env:MEMORIES_RATE_LIMIT_READS_PER_MINUTE="5"
$env:MEMORIES_RATE_LIMIT_WRITES_PER_MINUTE="3"
$env:MEMORIES_RATE_LIMIT_BATCH_PER_MINUTE="2"
$env:MEMORIES_RATE_LIMIT_MCP_PER_MINUTE="10"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Tune request counts:

```powershell
python scripts\rate_limit_stress.py `
  --fast-rest-reads 200 `
  --fast-rest-writes 60 `
  --flood-rest-reads 750 `
  --flood-mcp-requests 750
```

## Interpreting Results

For the `mixed` scenario, the expected result is usually zero `429` responses with the default
limits. That means routine agent memory usage fits comfortably.

For `fast` and `flood`, `429` responses are expected once the configured bucket is exhausted. The
important signs are that the server remains responsive, the accepted count is near the configured
per-minute bucket limit, and denials are clean `429`s.

For `two-agent`, the normal client should continue to avoid `429`s while the runaway client is
limited. That indicates `X-Client-Id` isolation is behaving as intended under load.
