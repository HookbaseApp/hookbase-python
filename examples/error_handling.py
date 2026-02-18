"""Error handling patterns."""

from hookbase import (
    Hookbase,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    APIError,
    TimeoutError,
    NetworkError,
)

client = Hookbase(api_key="whr_your_api_key")

# --- Handling specific errors ---
try:
    source = client.sources.get("src_nonexistent")
except NotFoundError:
    print("Source not found")
except AuthenticationError:
    print("Invalid API key - check your credentials")
except ForbiddenError as e:
    print(f"Access denied: {e}")
except RateLimitError as e:
    print(f"Rate limited - retry after {e.retry_after}s")
except ValidationError as e:
    print(f"Validation failed: {e}")
    if e.validation_errors:
        for field, errors in e.validation_errors.items():
            print(f"  {field}: {', '.join(errors)}")

# --- Catching all API errors ---
try:
    client.sources.create({"name": ""})
except APIError as e:
    print(f"API error {e.status_code}: {e}")
    print(f"  Code: {e.code}")
    print(f"  Request ID: {e.request_id}")

# --- Network / timeout errors ---
try:
    client.sources.list()
except TimeoutError:
    print("Request timed out")
except NetworkError as e:
    print(f"Network error: {e}")
    if e.cause:
        print(f"  Caused by: {e.cause}")

client.close()
