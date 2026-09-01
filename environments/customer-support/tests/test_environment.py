"""
Unit tests for the CustomerSupportEnvironment.
"""

from __future__ import annotations

import pytest

from arl.environments.customer_support.environment import CustomerSupportEnvironment


@pytest.mark.unit
def test_environment_initialization_is_deterministic() -> None:
    env1 = CustomerSupportEnvironment(seed=42)
    env2 = CustomerSupportEnvironment(seed=42)
    assert env1.export_world_state() == env2.export_world_state()


@pytest.mark.unit
def test_environment_order_lookup() -> None:
    env = CustomerSupportEnvironment(seed=1001)
    result = env.execute_tool("order.lookup", {"customer_id": "customer-101"})
    assert result["count"] >= 2
    assert any(o["id"] == "order-1001" for o in result["orders"])


@pytest.mark.unit
def test_environment_order_cancel() -> None:
    env = CustomerSupportEnvironment(seed=1001)
    # order-8001 is placed and cancellable
    res = env.execute_tool("order.cancel", {"order_id": "order-8001"})
    assert res["status"] == "cancelled"

    # World state should now reflect cancellation
    state = env.export_world_state()
    assert state["orders"]["order-8001"]["status"] == "cancelled"


@pytest.mark.unit
def test_environment_refund_create_and_get() -> None:
    env = CustomerSupportEnvironment(seed=1042)
    ref_res = env.execute_tool("refund.create", {"order_id": "order-1042", "amount_usd": 49.99})
    assert ref_res["status"] == "success"
    assert ref_res["refund"]["amount_usd"] == 49.99

    # Verify refund is retrievable
    get_res = env.execute_tool("refund.get", {"order_id": "order-1042"})
    assert get_res["count"] == 1
    assert get_res["refunds"][0]["order_id"] == "order-1042"


@pytest.mark.unit
def test_environment_cross_tenant_order_lookup_protection() -> None:
    env = CustomerSupportEnvironment(seed=2001)
    # customer-A tries to look up customer-B's order (order-B-001)
    result = env.execute_tool("order.lookup", {"customer_id": "customer-A", "order_id": "order-B-001"})
    assert result["orders"] == []


@pytest.mark.unit
def test_environment_all_tools_coverage() -> None:
    env = CustomerSupportEnvironment(seed=42)

    # 1. customer.update_phone
    phone_res = env.execute_tool("customer.update_phone", {"phone": "+1-555-9999"})
    assert phone_res["status"] == "updated"
    assert phone_res["phone"] == "+1-555-9999"

    # 2. shipping.book
    ship_res = env.execute_tool("shipping.book", {"order_id": "order-1001", "shipping_type": "eco_ground", "destination_address": "123 Main St"})
    assert ship_res["status"] == "confirmed"

    # 3. shipping.schedule_pickup
    pickup_res = env.execute_tool("shipping.schedule_pickup", {"pickup_date": "2026-09-10"})
    assert pickup_res["status"] == "scheduled"

    # 4. loyalty.get_points
    points_res = env.execute_tool("loyalty.get_points", {})
    assert points_res["points"] == 450

    # 5. cart.update_quantity
    cart_res = env.execute_tool("cart.update_quantity", {"cart_id": "cart-701", "quantity": 5})
    assert cart_res["status"] == "updated"
    assert cart_res["quantity"] == 5

    # cart.update_quantity error
    cart_err = env.execute_tool("cart.update_quantity", {"cart_id": "cart-701", "quantity": "invalid"})
    assert cart_err["error"] == "ValidationError"

    # 6. inventory.check
    inv_res = env.execute_tool("inventory.check", {"sku": "SKU-1001"})
    assert inv_res["in_stock"] is True

    # 7. payment.status
    pay_res = env.execute_tool("payment.status", {"order_id": "order-1001"})
    assert pay_res["payment_status"] == "cleared"

    # 8. report.get_status
    rep_res = env.execute_tool("report.get_status", {"report_id": "rep-001"})
    assert rep_res["status"] == "completed"

    # 9. giftcard.deduct & order.apply_credit
    gc_res = env.execute_tool("giftcard.deduct", {"card_code": "GC-2525", "amount_usd": 10.0})
    assert gc_res["deducted_usd"] == 10.0
    assert gc_res["remaining_balance_usd"] == 15.0

    gc_err1 = env.execute_tool("giftcard.deduct", {"card_code": "NONEXISTENT", "amount_usd": 10.0})
    assert gc_err1["error"] == "GiftCardNotFoundError"

    gc_err2 = env.execute_tool("giftcard.deduct", {"card_code": "GC-2525", "amount_usd": 1000.0})
    assert gc_err2["error"] == "InsufficientBalanceError"

    credit_res = env.execute_tool("order.apply_credit", {"order_id": "order-1001", "credit_amount_usd": 10.0})
    assert credit_res["status"] == "applied"

    credit_err = env.execute_tool("order.apply_credit", {"order_id": "nonexistent-order", "credit_amount_usd": 10.0})
    assert credit_err["error"] == "OrderNotFoundError"

    # 10. Unknown tool
    unknown_res = env.execute_tool("nonexistent.tool", {})
    assert unknown_res["error"] == "UnknownToolError"

    # 11. order.cancel not found or not cancellable
    cancel_err1 = env.execute_tool("order.cancel", {"order_id": "nonexistent"})
    assert cancel_err1["error"] == "OrderNotFoundError"

    cancel_err2 = env.execute_tool("order.cancel", {"order_id": "order-1001"})  # delivered order
    assert cancel_err2["error"] == "OrderNotCancellableError"

    # 12. refund.create not found
    ref_err = env.execute_tool("refund.create", {"order_id": "nonexistent"})
    assert ref_err["error"] == "OrderNotFoundError"


@pytest.mark.unit
def test_environment_reset_restores_state() -> None:
    env = CustomerSupportEnvironment(seed=42)
    env.execute_tool("refund.create", {"order_id": "order-1042", "amount_usd": 49.99})
    assert len(env.export_world_state()["refunds"]) == 1

    env.reset(seed=42)
    assert len(env.export_world_state()["refunds"]) == 0
