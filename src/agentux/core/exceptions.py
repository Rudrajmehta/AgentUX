"""AgentUX exception hierarchy."""


class AgentUXError(Exception):
    """Base exception for all AgentUX errors."""


class ConfigError(AgentUXError):
    """Invalid or missing configuration."""


class SurfaceError(AgentUXError):
    """Error during surface interaction."""


class BrowserSurfaceError(SurfaceError):
    """Browser-specific surface error."""


class CLISurfaceError(SurfaceError):
    """CLI-specific surface error."""


class MCPSurfaceError(SurfaceError):
    """MCP-specific surface error."""


class BackendError(AgentUXError):
    """Error communicating with an LLM backend."""


class BackendAuthError(BackendError):
    """Missing or invalid LLM credentials."""


class StorageError(AgentUXError):
    """Database or persistence error."""


class SchedulerError(AgentUXError):
    """Scheduler configuration or runtime error."""


class SandboxError(AgentUXError):
    """Sandbox creation or safety violation."""
