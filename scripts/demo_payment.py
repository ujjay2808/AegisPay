#!/usr/bin/env python3

import argparse
import json
import sys
import uuid
from decimal import Decimal, InvalidOperation
from urllib import error, request


def parse_args():
    parser = argparse.ArgumentParser(description="Run a demo intent -> cart -> payment flow against the local gateway.")
    parser.add_argument("--amount", required=True, help="Payment amount as a decimal string.")
    parser.add_argument("--merchant-id", default="merchant-demo", help="Merchant ID to use for the cart.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL for the gateway.")
    parser.add_argument("--currency", default="INR", help="Currency code for the intent, cart, and payment flow.")
    return parser.parse_args()


def print_error_response(status_code, body):
    print("status_code={0}".format(status_code))
    print(body)


def http_json(method, url, payload=None):
    headers = {}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            status_code = response.status
            try:
                parsed = json.loads(body) if body else {}
            except ValueError:
                parsed = {"raw_body": body}
            return status_code, parsed
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else {}
        except ValueError:
            parsed = {"raw_body": body}
        print_error_response(exc.code, json.dumps(parsed, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    except error.URLError as exc:
        print_error_response("URL_ERROR", str(exc))
        raise SystemExit(1)


def choose_product_name(amount):
    return "Demo item {0}".format(amount)


def demo_flow(amount_str, merchant_id, base_url, currency):
    try:
        amount = Decimal(amount_str)
    except InvalidOperation:
        print("Invalid amount: {0}".format(amount_str))
        raise SystemExit(1)

    if amount <= 0:
        print("Amount must be greater than zero.")
        raise SystemExit(1)

    amount_text = format(amount, "f")
    item_name = choose_product_name(amount_text)

    intent_url = base_url.rstrip("/") + "/api/v1/mandates/intent"
    cart_url = base_url.rstrip("/") + "/api/v1/mandates/cart"
    payment_url = base_url.rstrip("/") + "/api/v1/mandates/payment"

    intent_payload = {
        "agent_id": "agent-demo",
        "user_id": "user-demo",
        "purpose": "Demo purchase",
        "spending_constraints": {
            "max_amount": "100000.00",
            "currency": currency,
        },
    }
    intent_status, intent_json = http_json("POST", intent_url, intent_payload)
    print("intent {0}".format(intent_status))
    intent_id = intent_json.get("intent_id")
    if intent_id is None:
        print("intent")
        print(json.dumps(intent_json, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    cart_payload = {
        "intent_id": intent_id,
        "merchant_id": merchant_id,
        "merchant_name": "Demo Merchant",
        "items": [
            {
                "product_id": "product-demo",
                "name": item_name,
                "quantity": 1,
                "unit_price": amount_text,
            }
        ],
        "currency": currency,
    }
    cart_status, cart_json = http_json("POST", cart_url, cart_payload)
    print("cart {0}".format(cart_status))
    cart_id = cart_json.get("cart_id")
    if cart_id is None:
        print("cart")
        print(json.dumps(cart_json, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    payment_payload = {
        "cart_id": cart_id,
        "payment_method": "SIMULATED_CARD",
        "idempotency_key": "demo-{0}".format(uuid.uuid4().hex[:8]),
    }
    payment_status, payment_json = http_json("POST", payment_url, payment_payload)
    print("payment {0}".format(payment_status))

    output = {
        "transaction_id": payment_json.get("payment_id"),
        "decision": payment_json.get("decision"),
        "status": payment_json.get("status"),
        "reason_code": payment_json.get("reason_code"),
    }
    if "audit_tx_hash" in payment_json:
        output["audit_tx_hash"] = payment_json.get("audit_tx_hash")

    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))


def main():
    args = parse_args()
    demo_flow(args.amount, args.merchant_id, args.base_url, args.currency)
    return 0


if __name__ == "__main__":
    sys.exit(main())
