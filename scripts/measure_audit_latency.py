#!/usr/bin/env python3
import argparse
import json
import os
import secrets
import statistics
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_AUDIT_URL = "http://localhost:8080/api/decisions"
DEFAULT_RPC_URL = "https://rpc-amoy.polygon.technology"
POLL_INTERVAL_SECONDS = 0.2
CONFIRMATION_TIMEOUT_SECONDS = 60.0
HTTP_TIMEOUT_SECONDS = 30.0
PRE_FLIGHT_TIMEOUT_SECONDS = 10.0


def _post_json(url: str, payload: Dict[str, Any], timeout_seconds: float) -> Dict[str, Any]:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as error:
        raise RuntimeError("status %d" % error.code)
    except urllib.error.URLError as error:
        reason = getattr(error, "reason", None)
        if isinstance(reason, TimeoutError):
            raise RuntimeError("timeout")
        raise RuntimeError("connection failed")
    except TimeoutError:
        raise RuntimeError("timeout")
    except json.JSONDecodeError:
        raise RuntimeError("invalid JSON")


def _fetch_receipt(rpc_url: str, tx_hash: str, timeout_seconds: float) -> Optional[Dict[str, Any]]:
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getTransactionReceipt",
        "params": [tx_hash],
        "id": 1,
    }
    response = _post_json(rpc_url, payload, timeout_seconds)
    if not isinstance(response, dict):
        raise RuntimeError("invalid JSON-RPC response")
    if response.get("error"):
        raise RuntimeError("JSON-RPC returned an error")
    result = response.get("result")
    if result is None:
        return None
    if not isinstance(result, dict):
        raise RuntimeError("invalid receipt payload")
    return result


def _parse_hex_int(value: Any) -> Optional[int]:
    if isinstance(value, str):
        try:
            if value.startswith("0x") or value.startswith("0X"):
                return int(value, 16)
            return int(value)
        except ValueError:
            return None
    if isinstance(value, int):
        return value
    return None


def _measure_one_run(audit_url: str, rpc_url: str) -> Tuple[float, float, Optional[int], Optional[int]]:
    decision_hash = "0x" + secrets.token_hex(32)
    decision_payload = {
        "decisionHash": decision_hash,
        "decision": "APPROVED",
    }

    started_at = time.perf_counter()
    post_response = _post_json(audit_url, decision_payload, timeout_seconds=HTTP_TIMEOUT_SECONDS)
    submit_seconds = time.perf_counter() - started_at

    if not isinstance(post_response, dict):
        raise RuntimeError("invalid audit response")

    tx_hash = post_response.get("txHash")
    if not isinstance(tx_hash, str) or not tx_hash:
        raise RuntimeError("missing txHash in audit response")

    deadline = started_at + CONFIRMATION_TIMEOUT_SECONDS
    receipt = None
    while True:
        now = time.perf_counter()
        if now >= deadline:
            raise TimeoutError("confirmation timeout after %.1fs" % CONFIRMATION_TIMEOUT_SECONDS)

        receipt = _fetch_receipt(rpc_url, tx_hash, timeout_seconds=HTTP_TIMEOUT_SECONDS)
        if receipt is not None:
            break
        time.sleep(POLL_INTERVAL_SECONDS)

    confirm_seconds = time.perf_counter() - started_at
    block_number = _parse_hex_int(receipt.get("blockNumber"))
    status_value = _parse_hex_int(receipt.get("status"))
    return submit_seconds, confirm_seconds, block_number, status_value


def _format_stats(label: str, values: List[float]) -> str:
    return (
        "%s min/avg/median/max: %.3fs / %.3fs / %.3fs / %.3fs"
        % (
            label,
            min(values),
            sum(values) / len(values),
            statistics.median(values),
            max(values),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure audit submit and confirmation latency.")
    parser.add_argument("--runs", type=int, default=10, help="Number of runs to execute (default: 10)")
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        default=True,
        help="Stop after the first failed run (default: enabled)",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_AUDIT_URL,
        help="Audit service decision endpoint URL",
    )
    args = parser.parse_args()

    if args.runs <= 0:
        print("--runs must be greater than 0", file=sys.stderr)
        return 2

    rpc_url = os.environ.get("AMOY_RPC_URL", DEFAULT_RPC_URL)

    try:
        latest_block_response = _post_json(
            rpc_url,
            {
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1,
            },
            timeout_seconds=PRE_FLIGHT_TIMEOUT_SECONDS,
        )
        if not isinstance(latest_block_response, dict):
            raise RuntimeError("invalid JSON-RPC response")
        latest_block = latest_block_response.get("result")
        if not isinstance(latest_block, str):
            raise RuntimeError("missing block number")
    except Exception:
        print("Pre-flight failed: ")
        return 1

    print("Pre-flight OK, latest block %s" % latest_block)

    submit_samples = []  # type: List[float]
    confirm_samples = []  # type: List[float]

    for run_index in range(1, args.runs + 1):
        try:
            submit_seconds, confirm_seconds, block_number, status_value = _measure_one_run(
                audit_url=args.url,
                rpc_url=rpc_url,
            )
            submit_samples.append(submit_seconds)
            confirm_samples.append(confirm_seconds)
            block_text = str(block_number) if block_number is not None else "-"
            status_text = str(status_value) if status_value is not None else "-"
            print(
                "run %d: submit=%.3fs confirm=%.3fs block=%s status=%s"
                % (run_index, submit_seconds, confirm_seconds, block_text, status_text)
            )
        except Exception as error:
            print("run %d: error=: %s: %s" % (run_index, type(error).__name__, error))
            if args.stop_on_error:
                return 1
            continue

    if submit_samples and confirm_samples:
        print(_format_stats("submit", submit_samples))
        print(_format_stats("confirm", confirm_samples))
    else:
        print("No successful runs to summarize.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
