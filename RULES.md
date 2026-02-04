# Vending Machine Simulation Rules

## Goal

Run a profitable vending machine business for 30 days. End with more money than you started with ($500).

## Daily Flow

Each day follows this sequence:

```
1. DAILY FEE      → Pay $5 operating cost
2. DELIVERIES     → Ordered inventory arrives
3. AGENT ACTIONS  → Your AI takes up to 2 actions
4. CUSTOMERS      → Simulated customers buy products
5. REPEAT         → Next day begins
```

## How Customers Work

Customers are simulated automatically at the end of each day. You don't control this.

**Base demand per day:**
- Soda: ~20 customers
- Chips: ~15 customers
- Candy: ~18 customers

**Price affects demand:**
```
demand = base_demand × (2.0 / (price + 0.5)) × random(0.7 to 1.3)
```

| Price | Demand Multiplier | Example (Soda) |
|-------|-------------------|----------------|
| $0.50 | 2.0x | ~40 sales |
| $1.00 | 1.3x | ~26 sales |
| $1.50 | 1.0x | ~20 sales |
| $2.00 | 0.8x | ~16 sales |
| $3.00 | 0.6x | ~12 sales |

**Key insight:** Lower prices = more sales, but thinner margins. Higher prices = fewer sales, but better margins.

## Products

| Product | Default Price | Wholesale Cost (cheapest) |
|---------|---------------|---------------------------|
| Soda    | $1.75         | $0.50 (BulkBarn)         |
| Chips   | $1.25         | $0.35 (BulkBarn)         |
| Candy   | $0.99         | $0.20 (BulkBarn)         |

## Suppliers

| Supplier | Soda | Chips | Candy | Delivery | Notes |
|----------|------|-------|-------|----------|-------|
| QuickStock | $0.70 | $0.45 | $0.30 | 1 day | Reliable, fast |
| VendMart | $0.60 | $0.40 | $0.25 | 1-2 days | Cheaper but unreliable |
| BulkBarn | $0.50 | $0.35 | $0.20 | 3 days | Cheapest but slow |

**How to order:** Send an email with quantities. Example:
> "I'd like to order 50 sodas, 30 chips, and 20 candy"

The supplier auto-confirms and deducts money from your balance immediately.

## Available Tools

| Tool | What it does |
|------|--------------|
| `send_email` | Email a supplier to place an order |
| `set_price` | Change the retail price of a product |
| `check_inventory` | See current stock levels |
| `check_balance` | See current bank balance |

## Money Flow

```
START: $500

EXPENSES:
- Daily fee: $5/day × 30 days = $150 total
- Inventory: Varies based on orders

INCOME:
- Customer sales: price × quantity sold

PROFIT = Sales Revenue - Inventory Cost - Daily Fees
```

## Win/Lose Conditions

**Win:** End day 30 with balance > $500 (you made profit)

**Lose (Bankruptcy):** Balance drops below $0 at any point

## Example Day

```
Day 5 starts
├── Pay $5 daily fee (Balance: $423 → $418)
├── Delivery arrives: 30 Chips from QuickStock
├── Agent action 1: set_price("Chips", 1.50)
├── Agent action 2: send_email to BulkBarn for 50 sodas
│   └── Order confirmed, -$25 (Balance: $418 → $393)
├── Customers arrive:
│   ├── Sold 18 Soda @ $1.75 = $31.50
│   ├── Sold 22 Chips @ $1.50 = $33.00
│   └── Sold 12 Candy @ $0.99 = $11.88
│   └── Total revenue: $76.38 (Balance: $393 → $469.38)
└── Day 5 ends
```

## Strategy Tips

1. **Don't run out of stock** - Zero inventory = zero sales
2. **Plan ahead with BulkBarn** - 3-day delivery means order early
3. **Watch your margins** - Selling below wholesale = losing money
4. **Cover the daily fee** - Need ~$5/day profit minimum to survive
5. **Balance price vs volume** - Find the sweet spot

## Quick Math

To break even on daily fees alone ($5/day):
- At $1.25 margin per soda: need to sell 4 sodas/day
- At $0.80 margin per chips: need to sell 7 chips/day
- At $0.70 margin per candy: need to sell 8 candy/day
