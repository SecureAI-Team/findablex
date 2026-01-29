"""Rate limiting configuration."""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Use default rate limit (can be made configurable later)
DEFAULT_RATE_LIMIT = 100  # requests per minute

# Create rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{DEFAULT_RATE_LIMIT}/minute"],
)
