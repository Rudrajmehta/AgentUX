# Security

AgentUX executes LLM-generated actions against real surfaces. This document describes the safety measures in place.

## CLI Sandboxing

When evaluating CLI tools, commands run inside a temporary sandbox directory (`utils/sandbox.py`):

- A fresh temporary directory is created for each run.
- `HOME` and `TMPDIR` are redirected into the sandbox.
- The sandbox is deleted after the run completes.

### Blocked Commands

The following patterns are blocked and will not execute:

- `rm -rf /`, `rm -rf /*`
- `mkfs`, `dd if=`
- Fork bombs
- Writes to `/dev/sda`
- `sudo rm`
- `chmod -R 777 /`
- Piped install patterns (`curl | sh`, `wget | bash`)

Additional patterns can be configured via the `extra_blocked` parameter.

### Network Restrictions

By default, sandboxed CLI runs set `AGENTUX_SANDBOX=1` and `NO_PROXY=*` as signals to child processes. This is a convention, not enforcement. For stronger isolation, run AgentUX inside a container or VM.

## Secrets Handling

- API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) are read from environment variables, never stored in config files or logs.
- The `agentux doctor` command checks that keys are present but never prints them.
- Trace records truncate observation and result strings to avoid accidentally persisting sensitive page content.

## Log Redaction

- Step observations are truncated to 500 characters in stored traces.
- Action results are truncated to 200 characters in agent history context.
- Raw LLM prompts and completions are not persisted unless verbose logging is explicitly enabled.

## Safe Defaults

- `--demo` mode uses a mock backend with no network calls and no API key required.
- Browser evaluations run Playwright in headless mode by default.
- The maximum step count defaults to 25 to prevent runaway agent loops.
- Monitor thresholds default to conservative values (10% AES drop, 80% success rate).

## Recommendations

- Run AgentUX with the minimum required permissions.
- Use `--demo` mode for testing and development.
- When evaluating untrusted targets, run inside a container.
- Review monitor configs before deploying to CI -- each monitor run consumes API tokens.
- Do not commit API keys to version control. Use environment variables or a secrets manager.
