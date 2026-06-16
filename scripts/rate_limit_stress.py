"""Behavioral rate-limit stress scenarios for the local Memories API.

Run this against a disposable local server, for example:

    $env:MEMORIES_DB_FILE="$env:TEMP\\memories-rate-limit-stress.db"
    uvicorn app.main:app --host 127.0.0.1 --port 8000

Then:

    python scripts/rate_limit_stress.py

The scenarios intentionally live outside pytest because they are timing-sensitive and
generate load. They focus on realistic agent usage, fast agent bursts, concurrent floods,
and client isolation across REST and MCP HTTP surfaces.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import dataclasses
import html
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx

REST_SURFACE = "rest"
MCP_SURFACE = "mcp"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"


@dataclass(frozen=True)
class LoadProfile:
	mixed_rest_reads: int = 40
	mixed_rest_writes: int = 8
	mixed_rest_batches: int = 2
	mixed_mcp_requests: int = 80
	mixed_pause_seconds: float = 0.15
	fast_rest_reads: int = 150
	fast_rest_writes: int = 40
	fast_mcp_requests: int = 300
	flood_rest_reads: int = 500
	flood_rest_writes: int = 100
	flood_mcp_requests: int = 500
	two_agent_normal_rest_reads: int = 40
	two_agent_normal_rest_writes: int = 6
	two_agent_normal_mcp_requests: int = 60
	two_agent_flood_rest_reads: int = 300
	two_agent_flood_mcp_requests: int = 300


@dataclass(frozen=True)
class StressConfig:
	base_url: str
	timeout_seconds: float
	profile: LoadProfile
	scenarios: tuple[str, ...]
	surfaces: tuple[str, ...]
	output_file: Path


@dataclass(frozen=True)
class RequestSpec:
	method: str
	path: str
	json: object | None = None


@dataclass
class ScenarioResult:
	scenario: str
	surface: str
	client_id: str
	duration_seconds: float
	status_counts: collections.Counter[int]

	@property
	def accepted_by_limiter(self) -> int:
		return sum(count for status, count in self.status_counts.items() if status != 429)

	@property
	def denied_by_limiter(self) -> int:
		return self.status_counts[429]

	@property
	def other_errors(self) -> int:
		return sum(
			count
			for status, count in self.status_counts.items()
			if status >= 500 or status in {408, 409}
		)

	@property
	def total_requests(self) -> int:
		return sum(self.status_counts.values())

	@property
	def denied_percent(self) -> float:
		if self.total_requests == 0:
			return 0
		return self.denied_by_limiter / self.total_requests * 100


async def send_request(
	client: httpx.AsyncClient,
	spec: RequestSpec,
	client_id: str,
) -> int:
	response = await client.request(
		spec.method,
		spec.path,
		headers={"X-Client-Id": client_id},
		json=spec.json,
	)
	return response.status_code


def rest_read_spec() -> RequestSpec:
	return RequestSpec("GET", "/memories", None)


def rest_write_spec(index: int) -> RequestSpec:
	return RequestSpec(
		"POST",
		"/memories",
		{
			"content": f"rate limit stress memory {time.time_ns()} {index}",
			"tags": ["stress", "rate-limit"],
		},
	)


def rest_batch_spec(index: int) -> RequestSpec:
	return RequestSpec(
		"POST",
		"/memories/batch",
		[
			{
				"content": f"rate limit stress batch memory {time.time_ns()} {index}",
				"tags": ["stress", "batch"],
			}
		],
	)


def mcp_request_spec() -> RequestSpec:
	return RequestSpec("POST", "/mcp/", {})


def mixed_rest_specs(profile: LoadProfile) -> list[RequestSpec]:
	specs: list[RequestSpec] = []
	for index in range(max(profile.mixed_rest_reads, profile.mixed_rest_writes)):
		if index < profile.mixed_rest_writes:
			specs.append(rest_write_spec(index))
		if index < profile.mixed_rest_batches:
			specs.append(rest_batch_spec(index))
		if index < profile.mixed_rest_reads:
			specs.append(rest_read_spec())
	return specs


def mixed_mcp_specs(profile: LoadProfile) -> list[RequestSpec]:
	return [mcp_request_spec() for _ in range(profile.mixed_mcp_requests)]


def fast_rest_specs(profile: LoadProfile) -> list[RequestSpec]:
	return [
		*[rest_read_spec() for _ in range(profile.fast_rest_reads)],
		*[rest_write_spec(index) for index in range(profile.fast_rest_writes)],
	]


def fast_mcp_specs(profile: LoadProfile) -> list[RequestSpec]:
	return [mcp_request_spec() for _ in range(profile.fast_mcp_requests)]


def flood_rest_specs(profile: LoadProfile) -> list[RequestSpec]:
	return [
		*[rest_read_spec() for _ in range(profile.flood_rest_reads)],
		*[rest_write_spec(index) for index in range(profile.flood_rest_writes)],
	]


def flood_mcp_specs(profile: LoadProfile) -> list[RequestSpec]:
	return [mcp_request_spec() for _ in range(profile.flood_mcp_requests)]


async def run_sequence(
	client: httpx.AsyncClient,
	specs: list[RequestSpec],
	client_id: str,
	pause_seconds: float,
) -> collections.Counter[int]:
	statuses: collections.Counter[int] = collections.Counter()
	for spec in specs:
		statuses[await send_request(client, spec, client_id)] += 1
		if pause_seconds > 0:
			await asyncio.sleep(pause_seconds)
	return statuses


async def run_concurrent(
	client: httpx.AsyncClient,
	specs: list[RequestSpec],
	client_id: str,
) -> collections.Counter[int]:
	statuses = await asyncio.gather(
		*(send_request(client, spec, client_id) for spec in specs),
	)
	return collections.Counter(statuses)


async def run_single_result(
	config: StressConfig,
	scenario: str,
	surface: str,
	client_id: str,
	specs: list[RequestSpec],
	runner: Callable[
		[httpx.AsyncClient, list[RequestSpec], str], Awaitable[collections.Counter[int]]
	],
) -> ScenarioResult:
	timeout = httpx.Timeout(config.timeout_seconds)
	limits = httpx.Limits(max_connections=max(100, len(specs)), max_keepalive_connections=50)
	async with httpx.AsyncClient(
		base_url=config.base_url,
		timeout=timeout,
		limits=limits,
	) as client:
		started = time.perf_counter()
		status_counts = await runner(client, specs, client_id)
		duration_seconds = time.perf_counter() - started

	return ScenarioResult(
		scenario=scenario,
		surface=surface,
		client_id=client_id,
		duration_seconds=duration_seconds,
		status_counts=status_counts,
	)


async def run_mixed_workload(config: StressConfig, surface: str) -> list[ScenarioResult]:
	profile = config.profile
	client_id = f"stress-mixed-{surface}-{random.randrange(1_000_000)}"
	if surface == REST_SURFACE:
		specs = mixed_rest_specs(profile)
	else:
		specs = mixed_mcp_specs(profile)

	async def paced_runner(
		client: httpx.AsyncClient,
		request_specs: list[RequestSpec],
		request_client_id: str,
	) -> collections.Counter[int]:
		return await run_sequence(
			client,
			request_specs,
			request_client_id,
			profile.mixed_pause_seconds,
		)

	return [
		await run_single_result(
			config,
			"mixed_workload",
			surface,
			client_id,
			specs,
			paced_runner,
		)
	]


async def run_fast_agent(config: StressConfig, surface: str) -> list[ScenarioResult]:
	profile = config.profile
	client_id = f"stress-fast-{surface}-{random.randrange(1_000_000)}"
	specs = fast_rest_specs(profile) if surface == REST_SURFACE else fast_mcp_specs(profile)
	return [
		await run_single_result(
			config,
			"fast_agent",
			surface,
			client_id,
			specs,
			run_sequence_no_pause,
		)
	]


async def run_concurrent_flood(config: StressConfig, surface: str) -> list[ScenarioResult]:
	profile = config.profile
	client_id = f"stress-flood-{surface}-{random.randrange(1_000_000)}"
	specs = flood_rest_specs(profile) if surface == REST_SURFACE else flood_mcp_specs(profile)
	return [
		await run_single_result(
			config,
			"concurrent_flood",
			surface,
			client_id,
			specs,
			run_concurrent,
		)
	]


async def run_two_agent_comparison(config: StressConfig, surface: str) -> list[ScenarioResult]:
	profile = config.profile
	normal_client_id = f"stress-normal-{surface}-{random.randrange(1_000_000)}"
	flood_client_id = f"stress-runaway-{surface}-{random.randrange(1_000_000)}"

	if surface == REST_SURFACE:
		normal_specs = [
			*[rest_read_spec() for _ in range(profile.two_agent_normal_rest_reads)],
			*[rest_write_spec(index) for index in range(profile.two_agent_normal_rest_writes)],
		]
		flood_specs = [
			*[rest_read_spec() for _ in range(profile.two_agent_flood_rest_reads)],
		]
	else:
		normal_specs = [mcp_request_spec() for _ in range(profile.two_agent_normal_mcp_requests)]
		flood_specs = [mcp_request_spec() for _ in range(profile.two_agent_flood_mcp_requests)]

	async with httpx.AsyncClient(
		base_url=config.base_url,
		timeout=httpx.Timeout(config.timeout_seconds),
		limits=httpx.Limits(max_connections=500, max_keepalive_connections=100),
	) as client:
		started = time.perf_counter()
		normal_task = asyncio.create_task(
			run_sequence(client, normal_specs, normal_client_id, profile.mixed_pause_seconds)
		)
		flood_task = asyncio.create_task(run_concurrent(client, flood_specs, flood_client_id))
		normal_counts, flood_counts = await asyncio.gather(normal_task, flood_task)
		duration_seconds = time.perf_counter() - started

	return [
		ScenarioResult(
			scenario="two_agent_comparison_normal",
			surface=surface,
			client_id=normal_client_id,
			duration_seconds=duration_seconds,
			status_counts=normal_counts,
		),
		ScenarioResult(
			scenario="two_agent_comparison_runaway",
			surface=surface,
			client_id=flood_client_id,
			duration_seconds=duration_seconds,
			status_counts=flood_counts,
		),
	]


async def run_sequence_no_pause(
	client: httpx.AsyncClient,
	specs: list[RequestSpec],
	client_id: str,
) -> collections.Counter[int]:
	return await run_sequence(client, specs, client_id, 0)


SCENARIO_RUNNERS = {
	"mixed": run_mixed_workload,
	"fast": run_fast_agent,
	"flood": run_concurrent_flood,
	"two-agent": run_two_agent_comparison,
}


async def run_stress_suite(config: StressConfig) -> list[ScenarioResult]:
	results: list[ScenarioResult] = []
	for scenario in config.scenarios:
		for surface in config.surfaces:
			results.extend(await SCENARIO_RUNNERS[scenario](config, surface))
	return results


def status_badge_class(status: int) -> str:
	if status == 429:
		return "status-denied"
	if status >= 500 or status in {408, 409}:
		return "status-error"
	return "status-accepted"


def html_escape(value: object) -> str:
	return html.escape(str(value), quote=True)


def render_status_badges(status_counts: collections.Counter[int]) -> str:
	return "".join(
		f'<span class="status-badge {status_badge_class(status)}">'
		f"{html_escape(status)}: {html_escape(count)}</span>"
		for status, count in sorted(status_counts.items())
	)


def render_bar(result: ScenarioResult) -> str:
	total = max(1, result.total_requests)
	accepted_width = result.accepted_by_limiter / total * 100
	denied_width = result.denied_by_limiter / total * 100
	other_width = max(0, 100 - accepted_width - denied_width)
	return (
		'<div class="bar" aria-label="request outcome distribution">'
		f'<div class="bar-accepted" style="width: {accepted_width:.2f}%"></div>'
		f'<div class="bar-denied" style="width: {denied_width:.2f}%"></div>'
		f'<div class="bar-other" style="width: {other_width:.2f}%"></div>'
		"</div>"
	)


def render_html_report(config: StressConfig, results: list[ScenarioResult]) -> str:
	total_requests = sum(result.total_requests for result in results)
	total_accepted = sum(result.accepted_by_limiter for result in results)
	total_denied = sum(result.denied_by_limiter for result in results)
	total_other = sum(result.other_errors for result in results)
	generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

	rows = []
	for result in results:
		rows.append(
			f"""
			<tr>
				<td>
					<strong>{html_escape(result.scenario)}</strong>
					<div class="muted">{html_escape(result.client_id)}</div>
				</td>
				<td><span class="surface">{html_escape(result.surface)}</span></td>
				<td class="numeric">{result.total_requests}</td>
				<td class="numeric accepted">{result.accepted_by_limiter}</td>
				<td class="numeric denied">{result.denied_by_limiter}</td>
				<td class="numeric">{result.denied_percent:.1f}%</td>
				<td class="numeric">{result.other_errors}</td>
				<td class="numeric">{result.duration_seconds:.2f}s</td>
				<td>{render_bar(result)}</td>
				<td class="statuses">{render_status_badges(result.status_counts)}</td>
			</tr>
			"""
		)

	return f"""<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>Memories API Rate Limit Stress Report</title>
	<style>
		:root {{
			color-scheme: light;
			--bg: #f6f7f9;
			--panel: #ffffff;
			--ink: #17202a;
			--muted: #667085;
			--line: #d9dee7;
			--accepted: #16835f;
			--accepted-bg: #dff5ec;
			--denied: #b42318;
			--denied-bg: #fee4df;
			--other: #875bf7;
			--other-bg: #eee8ff;
			--surface: #1f6feb;
			--surface-bg: #e7f0ff;
		}}

		body {{
			margin: 0;
			background: var(--bg);
			color: var(--ink);
			font-family:
				Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
				sans-serif;
		}}

		main {{
			max-width: 1180px;
			margin: 0 auto;
			padding: 32px 24px 48px;
		}}

		header {{
			margin-bottom: 24px;
		}}

		h1 {{
			margin: 0 0 8px;
			font-size: 28px;
			line-height: 1.2;
		}}

		.meta {{
			display: flex;
			flex-wrap: wrap;
			gap: 10px 18px;
			color: var(--muted);
			font-size: 14px;
		}}

		.cards {{
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
			gap: 12px;
			margin: 20px 0 24px;
		}}

		.card {{
			background: var(--panel);
			border: 1px solid var(--line);
			border-radius: 8px;
			padding: 16px;
		}}

		.card .label {{
			color: var(--muted);
			font-size: 13px;
			margin-bottom: 8px;
		}}

		.card .value {{
			font-size: 26px;
			font-weight: 700;
		}}

		.table-wrap {{
			overflow-x: auto;
			background: var(--panel);
			border: 1px solid var(--line);
			border-radius: 8px;
		}}

		table {{
			width: 100%;
			border-collapse: collapse;
			min-width: 1020px;
		}}

		th, td {{
			padding: 12px 14px;
			border-bottom: 1px solid var(--line);
			text-align: left;
			vertical-align: middle;
			font-size: 14px;
		}}

		th {{
			background: #eef1f6;
			color: #344054;
			font-size: 12px;
			text-transform: uppercase;
			letter-spacing: 0;
		}}

		tr:last-child td {{
			border-bottom: 0;
		}}

		.numeric {{
			text-align: right;
			font-variant-numeric: tabular-nums;
		}}

		.accepted {{
			color: var(--accepted);
			font-weight: 700;
		}}

		.denied {{
			color: var(--denied);
			font-weight: 700;
		}}

		.muted {{
			color: var(--muted);
			font-size: 12px;
			margin-top: 3px;
		}}

		.surface, .status-badge {{
			display: inline-flex;
			align-items: center;
			border-radius: 999px;
			padding: 3px 8px;
			font-size: 12px;
			font-weight: 700;
			white-space: nowrap;
		}}

		.surface {{
			color: var(--surface);
			background: var(--surface-bg);
		}}

		.statuses {{
			display: flex;
			flex-wrap: wrap;
			gap: 6px;
		}}

		.status-accepted {{
			color: var(--accepted);
			background: var(--accepted-bg);
		}}

		.status-denied {{
			color: var(--denied);
			background: var(--denied-bg);
		}}

		.status-error {{
			color: var(--other);
			background: var(--other-bg);
		}}

		.bar {{
			display: flex;
			width: 150px;
			height: 10px;
			overflow: hidden;
			background: #eceff3;
			border-radius: 999px;
		}}

		.bar-accepted {{
			background: var(--accepted);
		}}

		.bar-denied {{
			background: var(--denied);
		}}

		.bar-other {{
			background: var(--other);
		}}

		footer {{
			margin-top: 18px;
			color: var(--muted);
			font-size: 13px;
		}}
	</style>
</head>
<body>
	<main>
		<header>
			<h1>Memories API Rate Limit Stress Report</h1>
			<div class="meta">
				<span>Generated: {html_escape(generated_at)}</span>
				<span>Base URL: {html_escape(config.base_url)}</span>
				<span>Scenarios: {html_escape(", ".join(config.scenarios))}</span>
				<span>Surfaces: {html_escape(", ".join(config.surfaces))}</span>
			</div>
		</header>

		<section class="cards" aria-label="summary">
			<div class="card">
				<div class="label">Total Requests</div>
				<div class="value">{total_requests}</div>
			</div>
			<div class="card">
				<div class="label">Accepted By Limiter</div>
				<div class="value accepted">{total_accepted}</div>
			</div>
			<div class="card">
				<div class="label">Denied 429</div>
				<div class="value denied">{total_denied}</div>
			</div>
			<div class="card">
				<div class="label">Other Notable Errors</div>
				<div class="value">{total_other}</div>
			</div>
		</section>

		<section class="table-wrap" aria-label="scenario results">
			<table>
				<thead>
					<tr>
						<th>Scenario</th>
						<th>Surface</th>
						<th class="numeric">Total</th>
						<th class="numeric">Accepted</th>
						<th class="numeric">429</th>
						<th class="numeric">Denied %</th>
						<th class="numeric">Other</th>
						<th class="numeric">Duration</th>
						<th>Distribution</th>
						<th>Status Counts</th>
					</tr>
				</thead>
				<tbody>
					{"".join(rows)}
				</tbody>
			</table>
		</section>

		<footer>
			For MCP, non-429 statuses mean the request passed the rate limiter. Lightweight MCP
			probe requests may still be rejected later by MCP transport parsing.
		</footer>
	</main>
</body>
</html>
"""


def write_html_report(config: StressConfig, results: list[ScenarioResult]) -> None:
	config.output_file.parent.mkdir(parents=True, exist_ok=True)
	config.output_file.write_text(render_html_report(config, results), encoding="utf-8")


def parse_csv_choices(value: str, allowed: set[str]) -> tuple[str, ...]:
	choices = tuple(part.strip() for part in value.split(",") if part.strip())
	unknown = sorted(set(choices) - allowed)
	if unknown:
		raise argparse.ArgumentTypeError(f"unknown choices: {', '.join(unknown)}")
	return choices


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Run behavioral Memories API rate-limit stress scenarios."
	)
	parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
	parser.add_argument("--timeout", type=float, default=30.0)
	parser.add_argument(
		"--scenarios",
		default="mixed,fast,flood,two-agent",
		help="Comma-separated: mixed,fast,flood,two-agent",
	)
	parser.add_argument(
		"--surfaces",
		default="rest,mcp",
		help="Comma-separated: rest,mcp",
	)
	parser.add_argument(
		"--output",
		type=Path,
		default=Path("scripts/rate_limit_report.html"),
		help="HTML report output path.",
	)
	for field in dataclasses.fields(LoadProfile):
		default_value = getattr(LoadProfile(), field.name)
		parser.add_argument(
			f"--{field.name.replace('_', '-')}",
			type=type(default_value),
			default=default_value,
		)
	return parser


def build_config(args: argparse.Namespace) -> StressConfig:
	profile_values = {
		field.name: getattr(args, field.name) for field in dataclasses.fields(LoadProfile)
	}
	return StressConfig(
		base_url=args.base_url.rstrip("/"),
		timeout_seconds=args.timeout,
		profile=LoadProfile(**profile_values),
		scenarios=parse_csv_choices(args.scenarios, set(SCENARIO_RUNNERS)),
		surfaces=parse_csv_choices(args.surfaces, {REST_SURFACE, MCP_SURFACE}),
		output_file=args.output,
	)


def main() -> None:
	parser = build_parser()
	config = build_config(parser.parse_args())
	results = asyncio.run(run_stress_suite(config))
	write_html_report(config, results)
	print(f"HTML report written to {config.output_file.resolve()}")


if __name__ == "__main__":
	main()
