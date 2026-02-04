"""Vending machine simulation logic."""

import random
from dataclasses import dataclass, field


@dataclass
class Product:
    name: str
    stock: int = 0
    price: float = 0.0
    wholesale_cost: float = 0.0


@dataclass
class GameState:
    day: int = 1
    balance: float = 500.0
    products: dict = field(
        default_factory=lambda: {
            "Soda": Product("Soda", stock=10, price=1.75, wholesale_cost=0.70),
            "Chips": Product("Chips", stock=10, price=1.25, wholesale_cost=0.45),
            "Candy": Product("Candy", stock=10, price=0.99, wholesale_cost=0.30),
        }
    )
    pending_orders: list = field(default_factory=list)
    sales_today: dict = field(default_factory=dict)
    emails: list = field(default_factory=list)
    agent_notes: str = ""
    max_days: int = 30

    def to_dict(self):
        return {
            "day": self.day,
            "balance": round(self.balance, 2),
            "products": {
                name: {
                    "stock": p.stock,
                    "price": p.price,
                    "wholesale_cost": p.wholesale_cost,
                }
                for name, p in self.products.items()
            },
            "sales_today": self.sales_today,
            "emails": self.emails[-10:],  # Last 10 emails
            "max_days": self.max_days,
        }


SUPPLIERS = {
    "QuickStock": {
        "Soda": 0.70,
        "Chips": 0.45,
        "Candy": 0.30,
        "reliable": True,
        "delivery_days": 1,
        "personality": "professional",
    },
    "VendMart": {
        "Soda": 0.60,
        "Chips": 0.40,
        "Candy": 0.25,
        "reliable": False,
        "delivery_days": 1,  # but unreliable, may take 2
        "personality": "pushy",
    },
    "BulkBarn": {
        "Soda": 0.50,
        "Chips": 0.35,
        "Candy": 0.20,
        "reliable": True,
        "delivery_days": 3,  # slow but cheapest
        "personality": "friendly",
    },
}


def simulate_customers(state: GameState) -> dict:
    """Simulate a day of customer purchases."""
    sales = {"Soda": 0, "Chips": 0, "Candy": 0}
    revenue = 0.0

    # Base demand varies by product
    base_demand = {"Soda": 20, "Chips": 15, "Candy": 18}

    for product_name, product in state.products.items():
        if product.stock <= 0:
            continue

        # Demand affected by price (lower price = more demand)
        price_factor = 2.0 / (product.price + 0.5)  # Higher prices reduce demand
        demand = int(
            base_demand[product_name] * price_factor * random.uniform(0.7, 1.3)
        )

        # Can't sell more than we have
        sold = min(demand, product.stock)
        product.stock -= sold
        sales[product_name] = sold
        revenue += sold * product.price

    state.balance += revenue
    state.sales_today = sales
    return {"sales": sales, "revenue": round(revenue, 2)}


def process_pending_orders(state: GameState):
    """Deliver any pending orders."""
    delivered = []
    for order in state.pending_orders[:]:
        order["days_remaining"] -= 1
        if order["days_remaining"] <= 0:
            product = state.products.get(order["product"])
            if product:
                product.stock += order["quantity"]
            delivered.append(order)
            state.pending_orders.remove(order)
    return delivered


def handle_tool_call(
    state: GameState, tool_name: str, args: dict, llm_client=None
) -> str:
    """Execute a tool and return the result."""

    if tool_name == "send_email":
        return handle_email(state, args, llm_client)
    elif tool_name == "set_price":
        product = args.get("product", "")
        price = float(args.get("price", 0))
        if product in state.products:
            old_price = state.products[product].price
            state.products[product].price = price
            return f"Price for {product} changed from ${old_price:.2f} to ${price:.2f}"
        return f"Unknown product: {product}"
    elif tool_name == "check_inventory":
        lines = ["Current inventory:"]
        for name, p in state.products.items():
            lines.append(f"  {name}: {p.stock} units @ ${p.price:.2f}")
        return "\n".join(lines)
    elif tool_name == "check_balance":
        return f"Current balance: ${state.balance:.2f}"
    elif tool_name == "take_notes":
        state.agent_notes = args.get("text", "")
        return "Notes saved."
    elif tool_name == "view_sales_history":
        return f"Yesterday's sales: {state.sales_today}"
    else:
        return f"Unknown tool: {tool_name}"


def handle_email(state: GameState, args: dict, llm_client=None) -> str:
    """Handle email to suppliers with simulated responses."""
    to = args.get("to", "")
    subject = args.get("subject", "")
    body = args.get("body", "")

    # Log outgoing email
    state.emails.append(
        {
            "direction": "out",
            "to": to,
            "subject": subject,
            "body": body[:200],
        }
    )

    # Find supplier
    supplier = None
    for name in SUPPLIERS:
        if name.lower() in to.lower():
            supplier = name
            break

    if not supplier:
        return f"Unknown recipient: {to}"

    # Generate supplier response based on email content
    response = generate_supplier_response(state, supplier, subject, body, llm_client)

    # Log incoming email
    state.emails.append(
        {
            "direction": "in",
            "from": supplier,
            "subject": f"Re: {subject}",
            "body": response[:200],
        }
    )

    return f"Email sent to {supplier}. They replied: {response}"


def generate_supplier_response(
    state: GameState, supplier: str, subject: str, body: str, llm_client=None
) -> str:
    """Generate a supplier response, optionally using LLM."""
    supplier_info = SUPPLIERS[supplier]
    body_lower = body.lower()

    # Check if this looks like an order
    is_order = any(
        word in body_lower
        for word in ["order", "buy", "purchase", "want", "need", "send"]
    )

    # Parse quantities from the email
    quantities = {}
    for product in ["soda", "chips", "candy"]:
        # Look for patterns like "20 sodas" or "soda: 20"
        import re

        patterns = [
            rf"(\d+)\s*{product}",
            rf"{product}[:\s]+(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, body_lower)
            if match:
                quantities[product.title()] = int(match.group(1))
                break

    if is_order and quantities:
        # Calculate total cost
        total = sum(quantities.get(p, 0) * supplier_info.get(p, 0) for p in quantities)

        # Check if they can afford it
        if total > state.balance:
            return f"Your order totals ${total:.2f} but your balance is only ${state.balance:.2f}. Please adjust your order."

        # Process the order
        base_days = supplier_info.get("delivery_days", 1)
        # Unreliable suppliers may add 1 extra day
        delivery_days = (
            base_days
            if supplier_info["reliable"]
            else base_days + random.choice([0, 1])
        )

        for product, qty in quantities.items():
            cost = qty * supplier_info.get(product, 0)
            state.balance -= cost
            state.pending_orders.append(
                {
                    "product": product,
                    "quantity": qty,
                    "cost": cost,
                    "days_remaining": delivery_days,
                }
            )

        order_summary = ", ".join(f"{q} {p}" for p, q in quantities.items())
        delivery_msg = "tomorrow" if delivery_days == 1 else f"in {delivery_days} days"
        return f"Order confirmed: {order_summary}. Total: ${total:.2f}. Delivery {delivery_msg}."

    # Generic response for non-orders
    if supplier_info["personality"] == "pushy":
        return "Thanks for reaching out! We have the BEST prices in town. What can I get you? We're running a special today - order now!"
    elif supplier_info["personality"] == "friendly":
        return f"Hey there! Great to hear from you. We've got wholesale prices: Soda ${supplier_info['Soda']:.2f}, Chips ${supplier_info['Chips']:.2f}, Candy ${supplier_info['Candy']:.2f}. Delivery takes 3 days but you'll save big!"
    else:
        return f"Hello! Happy to help. Our current prices: Soda ${supplier_info['Soda']:.2f}, Chips ${supplier_info['Chips']:.2f}, Candy ${supplier_info['Candy']:.2f}. Let me know what you need."
