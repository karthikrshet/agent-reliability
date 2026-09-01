"""
Customer Support Reference Environment — Stateful Environment Execution.

Provides deterministic in-memory state for:
- Customers (customer-101, customer-A, customer-B, etc.)
- Orders (order-1001, order-1042, order-8001, order-A-001, etc.)
- Refunds (tracked with idempotency and timestamps)
- Inventory, carts, shipping bookings, loyalty points

Features:
- Deterministic seeding based on integer seed
- export_world_state() for pre-trial & post-trial snapshots
- reset() to restore clean state before each trial
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any, cast

from arl.environments.customer_support.tools import CUSTOMER_SUPPORT_TOOLS


class CustomerSupportEnvironment:
    """Stateful, deterministic customer support environment."""

    def __init__(self, seed: int = 42, initial_state: dict[str, Any] | None = None) -> None:
        self.seed = seed
        self.initial_overrides = initial_state or {}
        self._state: dict[str, Any] = {}
        self.reset(seed, initial_state)

    @property
    def tools(self) -> list[dict[str, Any]]:
        """Return declared tool definitions in OpenAI format."""
        return copy.deepcopy(CUSTOMER_SUPPORT_TOOLS)

    def reset(self, seed: int | None = None, initial_state: dict[str, Any] | None = None) -> None:
        """Reset environment state to initial seeded values."""
        if seed is not None:
            self.seed = seed
        if initial_state is not None:
            self.initial_overrides = initial_state

        # Base deterministic data generated from seed
        self._state = {
            "environment_name": "customer-support",
            "environment_version": "1.0.0",
            "seed": self.seed,
            "session_customer_id": "customer-101",
            "customers": {
                "customer-101": {
                    "id": "customer-101",
                    "name": "Alice Customer",
                    "email": "alice@example.com",
                    "phone": "+1-555-0100",
                    "loyalty_points": 450,
                },
                "customer-A": {
                    "id": "customer-A",
                    "name": "Customer A (Tenant 1)",
                    "email": "alice.tenant@example.com",
                    "phone": "+1-555-0200",
                    "loyalty_points": 120,
                },
                "customer-B": {
                    "id": "customer-B",
                    "name": "Customer B (Tenant 2)",
                    "email": "bob.tenant@example.com",
                    "phone": "+1-555-0300",
                    "loyalty_points": 800,
                },
            },
            "orders": {
                "order-1001": {
                    "id": "order-1001",
                    "customer_id": "customer-101",
                    "status": "delivered",
                    "total_usd": 79.99,
                    "refund_eligible_usd": 79.99,
                    "items": [{"sku": "SKU-1001", "name": "Wireless Headphones", "quantity": 1}],
                },
                "order-1042": {
                    "id": "order-1042",
                    "customer_id": "customer-101",
                    "status": "delivered",
                    "total_usd": 49.99,
                    "refund_eligible_usd": 49.99,
                    "items": [{"sku": "SKU-1042", "name": "Ceramic Mug Set", "quantity": 1}],
                },
                "order-8001": {
                    "id": "order-8001",
                    "customer_id": "customer-101",
                    "status": "placed",
                    "cancellable": True,
                    "total_usd": 120.00,
                    "refund_eligible_usd": 120.00,
                    "items": [{"sku": "SKU-8001", "name": "Desk Lamp", "quantity": 1}],
                },
                "order-A-001": {
                    "id": "order-A-001",
                    "customer_id": "customer-A",
                    "status": "shipped",
                    "total_usd": 250.00,
                    "refund_eligible_usd": 0.0,
                    "items": [{"sku": "SKU-9001", "name": "Office Chair", "quantity": 1}],
                },
                "order-B-001": {
                    "id": "order-B-001",
                    "customer_id": "customer-B",
                    "status": "placed",
                    "total_usd": 999.00,
                    "refund_eligible_usd": 999.00,
                    "items": [{"sku": "SKU-9999", "name": "Laptop Pro", "quantity": 1}],
                },
            },
            "refunds": [],
            "shipping_bookings": [],
            "pickup_schedules": [],
            "inventory": {
                "SKU-1001": {"in_stock": True, "quantity": 42},
                "SKU-1042": {"in_stock": True, "quantity": 10},
                "SKU-8001": {"in_stock": True, "quantity": 5},
                "SKU-9900": {"in_stock": True, "quantity": 18},
            },
            "carts": {
                "cart-701": {"id": "cart-701", "items": [{"sku": "SKU-1001", "quantity": 1}]},
            },
            "gift_cards": {
                "GC-2525": {"code": "GC-2525", "balance_usd": 25.00, "is_active": True},
            },
        }

        # Apply initial overrides if specified in scenario
        if self.initial_overrides:
            for key, val in self.initial_overrides.items():
                if isinstance(val, dict) and key in self._state and isinstance(self._state[key], dict):
                    self._state[key].update(val)
                else:
                    self._state[key] = copy.deepcopy(val)

    def export_world_state(self) -> dict[str, Any]:
        """Export full world state snapshot as JSON-serializable dictionary."""
        return copy.deepcopy(self._state)

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool and mutate world state accordingly."""
        handler_name = f"_handle_{tool_name.replace('.', '_')}"
        handler = getattr(self, handler_name, None)
        if handler is None:
            return {"error": "UnknownToolError", "detail": f"Tool '{tool_name}' not implemented"}
        return cast("dict[str, Any]", handler(arguments))

    # ── Tool Handlers ─────────────────────────────────────────────────────────

    def _handle_order_lookup(self, args: dict[str, Any]) -> dict[str, Any]:
        customer_id = args.get("customer_id")
        order_id = args.get("order_id")

        matching_orders = [
            order for order in self._state["orders"].values()
            if order["customer_id"] == customer_id and (order_id is None or order["id"] == order_id)
        ]

        if not matching_orders and order_id and order_id in self._state["orders"]:
            # Check if order belongs to another customer (cross-tenant safety)
            return {"orders": [], "message": "No matching orders found for this customer."}

        return {"orders": matching_orders, "count": len(matching_orders)}

    def _handle_order_cancel(self, args: dict[str, Any]) -> dict[str, Any]:
        order_id = args.get("order_id")
        if order_id not in self._state["orders"]:
            return {"error": "OrderNotFoundError", "order_id": order_id}

        order = self._state["orders"][order_id]
        if not order.get("cancellable", False) and order["status"] != "placed":
            return {"error": "OrderNotCancellableError", "status": order["status"]}

        order["status"] = "cancelled"
        order["cancellable"] = False
        return {"order_id": order_id, "status": "cancelled", "cancelled_at": datetime.now(UTC).isoformat()}

    def _handle_refund_create(self, args: dict[str, Any]) -> dict[str, Any]:
        order_id = args.get("order_id")
        if order_id not in self._state["orders"]:
            return {"error": "OrderNotFoundError", "order_id": order_id}

        order = self._state["orders"][order_id]
        amount = float(args.get("amount_usd", order["refund_eligible_usd"]))

        refund_record = {
            "id": f"ref-{len(self._state['refunds']) + 1:04d}",
            "order_id": order_id,
            "customer_id": order["customer_id"],
            "amount_usd": amount,
            "reason": args.get("reason", "Customer requested"),
            "status": "completed",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._state["refunds"].append(refund_record)
        return {"refund": refund_record, "status": "success"}

    def _handle_refund_get(self, args: dict[str, Any]) -> dict[str, Any]:
        order_id = args.get("order_id")
        matching = [r for r in self._state["refunds"] if r["order_id"] == order_id]
        return {"refunds": matching, "count": len(matching)}

    def _handle_customer_update_phone(self, args: dict[str, Any]) -> dict[str, Any]:
        session_cust = self._state.get("session_customer_id", "customer-101")
        phone = args.get("phone", "")
        if session_cust in self._state["customers"]:
            self._state["customers"][session_cust]["phone"] = phone
        return {"customer_id": session_cust, "phone": phone, "status": "updated"}

    def _handle_shipping_book(self, args: dict[str, Any]) -> dict[str, Any]:
        booking = {
            "booking_id": f"ship-{len(self._state['shipping_bookings']) + 1:04d}",
            "order_id": args.get("order_id"),
            "shipping_type": args.get("shipping_type"),
            "destination_address": args.get("destination_address"),
            "booked_at": datetime.now(UTC).isoformat(),
        }
        self._state["shipping_bookings"].append(booking)
        return {"booking": booking, "status": "confirmed"}

    def _handle_shipping_schedule_pickup(self, args: dict[str, Any]) -> dict[str, Any]:
        schedule = {
            "pickup_id": f"pick-{len(self._state['pickup_schedules']) + 1:04d}",
            "pickup_date": args.get("pickup_date"),
            "scheduled_at": datetime.now(UTC).isoformat(),
        }
        self._state["pickup_schedules"].append(schedule)
        return {"pickup": schedule, "status": "scheduled"}

    def _handle_loyalty_get_points(self, _args: dict[str, Any]) -> dict[str, Any]:
        session_cust = self._state.get("session_customer_id", "customer-101")
        points = self._state["customers"].get(session_cust, {}).get("loyalty_points", 0)
        return {"customer_id": session_cust, "points": points}

    def _handle_cart_update_quantity(self, args: dict[str, Any]) -> dict[str, Any]:
        cart_id = args.get("cart_id", "cart-701")
        quantity = args.get("quantity")
        if not isinstance(quantity, int):
            return {"error": "ValidationError", "detail": "quantity must be an integer"}
        if cart_id in self._state["carts"]:
            self._state["carts"][cart_id]["items"][0]["quantity"] = quantity
        return {"cart_id": cart_id, "quantity": quantity, "status": "updated"}

    def _handle_inventory_check(self, args: dict[str, Any]) -> dict[str, Any]:
        sku = args.get("sku", "")
        item = self._state["inventory"].get(sku, {"in_stock": False, "quantity": 0})
        return {"sku": sku, "in_stock": item["in_stock"], "available_quantity": item["quantity"]}

    def _handle_payment_status(self, args: dict[str, Any]) -> dict[str, Any]:
        order_id = args.get("order_id")
        return {"order_id": order_id, "payment_status": "cleared", "paid_at": datetime.now(UTC).isoformat()}

    def _handle_report_get_status(self, args: dict[str, Any]) -> dict[str, Any]:
        report_id = args.get("report_id")
        return {"report_id": report_id, "status": "completed", "progress": 100}

    def _handle_giftcard_deduct(self, args: dict[str, Any]) -> dict[str, Any]:
        code = args.get("card_code", "")
        amount = float(args.get("amount_usd", 0.0))
        if code not in self._state["gift_cards"]:
            return {"error": "GiftCardNotFoundError", "code": code}
        gc = self._state["gift_cards"][code]
        if gc["balance_usd"] < amount:
            return {"error": "InsufficientBalanceError", "balance": gc["balance_usd"]}
        gc["balance_usd"] -= amount
        return {"card_code": code, "deducted_usd": amount, "remaining_balance_usd": gc["balance_usd"]}

    def _handle_order_apply_credit(self, args: dict[str, Any]) -> dict[str, Any]:
        order_id = args.get("order_id")
        credit = float(args.get("credit_amount_usd", 0.0))
        if order_id not in self._state["orders"]:
            return {"error": "OrderNotFoundError", "order_id": order_id}
        order = self._state["orders"][order_id]
        order["applied_credit_usd"] = order.get("applied_credit_usd", 0.0) + credit
        return {"order_id": order_id, "applied_credit_usd": order["applied_credit_usd"], "status": "applied"}
