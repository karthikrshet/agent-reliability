"""
Customer Support Environment — Declared Tool Definitions.

Defines all available tools in OpenAI function-calling format,
including strict JSON schemas for parameter validation.
"""

from __future__ import annotations

from typing import Any

CUSTOMER_SUPPORT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "order.lookup",
            "description": "Look up order status, items, and details for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "ID of the customer whose order to look up.",
                    },
                    "order_id": {
                        "type": "string",
                        "description": "Optional specific order ID to look up.",
                    },
                },
                "required": ["customer_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "order.cancel",
            "description": "Cancel a placed order if eligible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "ID of the order to cancel.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for order cancellation.",
                    },
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "refund.create",
            "description": "Issue a financial refund for an order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "ID of the order to refund.",
                    },
                    "amount_usd": {
                        "type": "number",
                        "minimum": 0.01,
                        "description": "Amount in USD to refund.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the refund.",
                    },
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "refund.get",
            "description": "Check the status of an existing refund for an order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to check for existing refunds.",
                    },
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "customer.update_phone",
            "description": "Update customer's primary phone number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {
                        "type": "string",
                        "description": "New phone number.",
                    },
                },
                "required": ["phone"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shipping.book",
            "description": "Book a shipping carrier for an order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to book shipping for.",
                    },
                    "shipping_type": {
                        "type": "string",
                        "enum": ["eco_ground", "standard", "express_air"],
                        "description": "Type of shipping service.",
                    },
                    "destination_address": {
                        "type": "string",
                        "description": "Delivery address.",
                    },
                },
                "required": ["shipping_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shipping.schedule_pickup",
            "description": "Schedule a package return pickup with courier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pickup_date": {
                        "type": "string",
                        "description": "Desired pickup date.",
                    },
                },
                "required": ["pickup_date"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "loyalty.get_points",
            "description": "Get loyalty rewards point balance.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cart.update_quantity",
            "description": "Update quantity of items in a shopping cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cart_id": {"type": "string"},
                    "quantity": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Quantity as integer.",
                    },
                },
                "required": ["quantity"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inventory.check",
            "description": "Check if a product SKU is in stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {"type": "string", "description": "Product SKU code."},
                },
                "required": ["sku"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "payment.status",
            "description": "Check status of a payment transaction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report.get_status",
            "description": "Get status of an async batch reporting task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_id": {"type": "string"},
                },
                "required": ["report_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "giftcard.deduct",
            "description": "Deduct credit balance from a gift card.",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_code": {"type": "string"},
                    "amount_usd": {"type": "number", "minimum": 0.01},
                },
                "required": ["card_code", "amount_usd"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "order.apply_credit",
            "description": "Apply credit to an active order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "credit_amount_usd": {"type": "number", "minimum": 0.01},
                },
                "required": ["order_id", "credit_amount_usd"],
                "additionalProperties": False,
            },
        },
    },
]
