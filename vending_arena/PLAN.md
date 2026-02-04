# Vending Wars - Workshop Solo Simulation

## Concept

Each participant creates their own AI agent that runs a vending machine business. Configure your agent's strategy, run a cell, and watch it negotiate with suppliers, stock inventory, set prices, and try to make money over 30 simulated days. **No competition between participants** — everyone watches their own agent independently on localhost.

---

## Participant Customization

```python
my_agent = {
    "company_name": "Discount Dan's Drinks",

    # Strategy sliders (1-10)
    "pricing_strategy": 3,      # 1=rock bottom prices, 10=premium pricing
    "risk_tolerance": 7,        # 1=small safe orders, 10=big bulk bets
    "negotiation_style": 8,     # 1=accept first offer, 10=haggle relentlessly

    # Free-text strategy (2-3 sentences)
    "strategy_prompt": "Focus on soda since it has highest margins. Start conservative, then scale up orders once you understand demand patterns."
}
```

Name, three sliders, one free-text prompt.

---

## Agent Tools

| Tool | Description |
|------|-------------|
| 📧 `send_email(to, subject, body)` | Email suppliers to negotiate and order |
| 💰 `set_price(product, price)` | Set your machine's price for a product |
| 📦 `check_inventory()` | See your current stock levels |
| 💳 `check_balance()` | See your current bank balance |
| 📊 `view_sales_history()` | See what sold yesterday and at what price |
| 📝 `take_notes(text)` | Save info for later (agent memory) |

Orders happen via email to suppliers (like the real eval).

---

## Products

| Product | Wholesale Range | Suggested Retail | Base Daily Demand |
|---------|-----------------|------------------|-------------------|
| Soda | $0.60-0.90 | $1.50-2.50 | 15-25 units |
| Chips | $0.40-0.60 | $1.00-1.75 | 10-20 units |
| Candy | $0.25-0.45 | $0.75-1.25 | 12-22 units |

---

## Suppliers

Agents start with two supplier contacts:

**QuickStock Vending** (honest)
- Fair base prices (~$0.75 soda, $0.50 chips, $0.35 candy)
- Reliable delivery
- Will negotiate bulk discounts (5-15% off for large orders)
- Responds professionally

**VendMart Express** (tricky)
- Slightly inflated prices
- Pushes upsells and "premium" products
- May offer deals that sound good but aren't
- Agents learn to negotiate hard or avoid

---

## Economics

- **Starting capital**: $500
- **Machine capacity**: 30 units per product slot
- **Storage**: Unlimited (simplification)
- **Delivery**: Next day (order today, stock tomorrow)

---

## Customer Behavior (Simulated)

Each day, customers arrive and buy based on:
- **Price sensitivity**: Lower prices → more sales (roughly linear)
- **Stock availability**: Can't sell what you don't have
- **Some randomness**: Demand varies ±20% day to day

If priced too high → fewer sales, leftover inventory
If priced too low → sell out, miss potential profit
If out of stock → lost sales

---

## Dashboard (Localhost)

When participant runs the final cell, opens `localhost:8000`:

```
+------------------------------------------------------------------+
|  🏪 [Company Name]                       Day 12/30  💰 $623       |
+------------------------------------------------------------------+
|                               |                                   |
|    📦 INVENTORY               |    📈 BALANCE OVER TIME           |
|    ─────────────────          |                                   |
|    Soda:  ████████░░ 24/30    |    $700 ┤         ●──●            |
|    Chips: ██████░░░░ 18/30    |    $600 ┤    ●───●                |
|    Candy: ██░░░░░░░░  6/30    |    $500 ┼●──●                     |
|                               |         └──────────────────       |
|    ⚠️ Low on candy!           |           Day 1   5   10          |
+------------------------------------------------------------------+
|                               |                                   |
|    📧 RECENT EMAILS           |    📊 TODAY'S ACTIVITY            |
|    ─────────────────          |    ─────────────────              |
|    → QuickStock:              |    ✅ Sold 8 Soda @ $1.75         |
|    "I'd like to order 20      |    ✅ Sold 5 Chips @ $1.25        |
|    sodas. Can you do $0.65    |    ✅ Sold 12 Candy @ $0.99       |
|    per unit for bulk?"        |    💵 Revenue: $28.63             |
|                               |    📦 Restocked from delivery     |
|    ← QuickStock:              |                                   |
|    "We can do $0.68 for       |    🤔 Agent thinking...           |
|    orders of 20+. Deal?"      |    "Should reorder candy soon"    |
|                               |                                   |
+------------------------------------------------------------------+
```

---

## Workshop Flow (30 min)

| Time | Activity |
|------|----------|
| 0-3 min | Explain concept: "Your AI runs a vending machine" |
| 3-8 min | Participants customize their agent config in notebook |
| 8-10 min | Run setup cell, server starts |
| 10-28 min | Watch agents run (~30 simulated days) |
| 28-30 min | Compare final balances, share funny agent moments |

---

## Files to Create

```
vending_arena/
├── server.py           # FastAPI server, runs simulation + Claude API
├── templates/
│   └── dashboard.html  # Live dashboard with WebSocket updates
└── simulation.py       # Game logic (customers, inventory, suppliers)
```

Notebook cell at end:
```python
from vending_arena import start_simulation
start_simulation(my_agent)  # Opens localhost:8000
```

---

## Key Rules Summary (For Participants)

1. You start with **$500**
2. Email suppliers to buy inventory — negotiate for better prices!
3. Set prices for each product in your machine
4. Customers buy based on price (lower = more sales)
5. Watch your balance grow (or shrink) over 30 days
6. **Goal: End with the highest balance you can**

---

## Why This Works

- **Simple setup**: One cell to run, one browser tab to watch
- **No coordination needed**: Everyone runs independently
- **Still interesting**: Watching AI negotiate and make decisions is fun
- **Easy comparison**: "What did your agent end up with?"
- **Debugging friendly**: Issues are isolated to individual laptops
