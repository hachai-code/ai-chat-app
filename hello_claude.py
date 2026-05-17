#!/usr/bin/env python3
import os
import sys

import env  # noqa: F401 — loads .env

import anthropic

def main():
    if len(sys.argv) < 2:
        print("Usage: python hello_claude.py <message>", file=sys.stderr)
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Missing ANTHROPIC_API_KEY. Add it to .env or export it.", file=sys.stderr)
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    client = anthropic.Anthropic()

    try:
        with client.messages.stream(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": message}],
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
        print()

    except (anthropic.RateLimitError) as e:
        retry_after = getattr(e, "response", None) and e.response.headers.get("retry-after")
        suffix = f" Retry after {retry_after}s." if retry_after else " Wait a moment and retry."
        print(f"\nAPI busy.{suffix}", file=sys.stderr)
        sys.exit(1)
    except anthropic.APITimeoutError:
        print("\nRequest timed out. Try again.", file=sys.stderr)
        sys.exit(1)
    except anthropic.APIConnectionError:
        print("\nNetwork error. Check your internet connection.", file=sys.stderr)
        sys.exit(1)
    except anthropic.AuthenticationError:
        print("\nInvalid API key. Set ANTHROPIC_API_KEY.", file=sys.stderr)
        sys.exit(1)
    except anthropic.APIStatusError as e:
        print(f"\nAPI error ({e.status_code}): {e.message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
