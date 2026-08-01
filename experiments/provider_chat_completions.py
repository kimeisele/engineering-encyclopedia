#!/usr/bin/env python3
"""Generic chat-completions provider adapter for the experiment harness.

Contract (matches the harness's ENCYCLOPEDIA_RUNNER contract):
  reads the prompt on stdin, writes the model's completion to stdout,
  diagnostics to stderr. Exit 0 on success, 1 on failure.

The API shape is OpenAI-compatible chat/completions; no vendor is named here.
The endpoint, model and key source are configured at run time so this file
never hardcodes a provider.

Usage:
  provider_chat_completions.py [--model NAME] [--base-url URL]
                               [--key-env VAR] [--max-tokens N]
                               [--timeout SECONDS]

Defaults: --model $MODEL or "deepseek-chat"; --base-url $BASE_URL or
"https://api.deepseek.com"; the key is read from the environment variable
named by --key-env, defaulting to $DEEPSEEK_API_KEY then $OPENAI_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Optional


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("MODEL") or "deepseek-chat")
    parser.add_argument("--base-url", default=os.environ.get("BASE_URL") or "https://api.deepseek.com")
    parser.add_argument("--key-env", default=None, help="name of the env var holding the API key")
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--disable-thinking", action="store_true",
                        help="send thinking: {type: disabled} (reasoning models "
                             "otherwise burn the token budget on reasoning)")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)

    key_env = args.key_env or ("DEEPSEEK_API_KEY" if os.environ.get("DEEPSEEK_API_KEY") else "OPENAI_API_KEY")
    api_key = os.environ.get(key_env)
    if not api_key:
        print(f"error: no API key in ${key_env}", file=sys.stderr)
        return 1

    prompt = sys.stdin.read()
    if not prompt.strip():
        print("error: empty prompt on stdin", file=sys.stderr)
        return 1

    endpoint = args.base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": args.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": args.max_tokens,
        "stream": False,
    }
    if args.disable_thinking:
        body["thinking"] = {"type": "disabled"}
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    # The API occasionally returns an empty completion (transient); retry the
    # whole request a few times before failing so the harness records a real
    # completion rather than a dropped run.
    last_error: Optional[str] = None
    for attempt in range(1, 4):
        last_error = None
        try:
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            last_error = f"HTTP {exc.code} from {endpoint}: {detail}"
            if exc.code in (400, 401, 403, 404, 422):  # not transient
                print(f"error: {last_error}", file=sys.stderr)
                return 1
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = f"request failed: {exc}"
        except json.JSONDecodeError as exc:
            last_error = f"invalid JSON response: {exc}"

        if last_error is None:
            try:
                content = payload["choices"][0]["message"]["content"]
                finish_reason = payload["choices"][0].get("finish_reason")
            except (KeyError, IndexError, TypeError):
                last_error = (
                    "unexpected response shape: " + json.dumps(payload)[:500]
                )
                content = None
                finish_reason = None
            if isinstance(content, str) and content.strip():
                sys.stdout.write(content)
                return 0
            last_error = (
                f"empty completion from the model "
                f"(finish_reason={finish_reason!r}), attempt {attempt}"
            )
        print(f"warning: {last_error}; retrying in 5s", file=sys.stderr)
        time.sleep(5)

    print(f"error: {last_error or 'giving up after retries'}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
