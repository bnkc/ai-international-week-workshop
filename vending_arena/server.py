"""FastAPI server for the vending simulation."""

import asyncio
import json
import threading
import time

import anthropic
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

from .simulation import (
    GameState,
    handle_tool_call,
    process_pending_orders,
    simulate_customers,
)

app = FastAPI()

# Global state
simulation_state = None
websocket_clients = []
simulation_running = False


VENDING_TOOLS = [
    {
        "name": "send_email",
        "description": "Send an email to a supplier to negotiate or place an order. Include what products and quantities you want.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Supplier name (QuickStock or VendMart)",
                },
                "subject": {"type": "string", "description": "Email subject"},
                "body": {
                    "type": "string",
                    "description": "Email body - include product names and quantities for orders",
                },
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "set_price",
        "description": "Set the retail price for a product.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product": {
                    "type": "string",
                    "description": "Product name (Soda, Chips, or Candy)",
                },
                "price": {"type": "number", "description": "New price in dollars"},
            },
            "required": ["product", "price"],
        },
    },
    {
        "name": "check_inventory",
        "description": "Check current stock levels and prices.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "check_balance",
        "description": "Check your current bank balance.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def get_dashboard_html():
    return """<!DOCTYPE html>
<html>
<head>
    <title>Vending Simulation</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
            min-height: 100vh;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #333;
        }
        .company-name { font-size: 24px; font-weight: bold; }
        .day-balance {
            display: flex;
            gap: 30px;
            font-size: 18px;
        }
        .balance { color: #4ade80; font-weight: bold; }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .panel {
            background: #252540;
            border-radius: 12px;
            padding: 20px;
        }
        .panel-title {
            font-size: 14px;
            text-transform: uppercase;
            color: #888;
            margin-bottom: 15px;
            letter-spacing: 1px;
        }
        .inventory-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }
        .product-card {
            background: #1a1a2e;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        .product-name { font-weight: bold; margin-bottom: 8px; }
        .product-stock {
            font-size: 28px;
            font-weight: bold;
            margin: 10px 0;
        }
        .product-stock.low { color: #f87171; }
        .product-stock.ok { color: #fbbf24; }
        .product-stock.good { color: #4ade80; }
        .product-price { color: #888; }
        .chart-container {
            height: 200px;
            display: flex;
            align-items: flex-end;
            gap: 4px;
            padding-top: 20px;
        }
        .chart-bar {
            flex: 1;
            background: #4ade80;
            border-radius: 4px 4px 0 0;
            min-height: 4px;
            transition: height 0.3s;
        }
        .email-list {
            max-height: 250px;
            overflow-y: auto;
        }
        .email {
            padding: 10px;
            margin-bottom: 8px;
            background: #1a1a2e;
            border-radius: 6px;
            font-size: 13px;
        }
        .email.outgoing { border-left: 3px solid #60a5fa; }
        .email.incoming { border-left: 3px solid #4ade80; }
        .email-header { color: #888; margin-bottom: 4px; }
        .activity-list { font-size: 14px; }
        .activity-item {
            padding: 8px 0;
            border-bottom: 1px solid #333;
        }
        .activity-item:last-child { border-bottom: none; }
        .sale { color: #4ade80; }
        .restock { color: #60a5fa; }
        .warning { color: #fbbf24; }
        .thinking {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 15px;
            background: #1a1a2e;
            border-radius: 8px;
            margin-top: 15px;
        }
        .thinking-dot {
            width: 8px;
            height: 8px;
            background: #60a5fa;
            border-radius: 50%;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
        }
        .status-complete {
            text-align: center;
            padding: 40px;
            font-size: 24px;
        }
        .final-balance {
            font-size: 48px;
            color: #4ade80;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-name" id="companyName">Loading...</div>
        <div class="day-balance">
            <div>Day <span id="currentDay">1</span> / <span id="maxDays">30</span></div>
            <div class="balance">$<span id="balance">500.00</span></div>
        </div>
    </div>

    <div class="grid">
        <div class="panel">
            <div class="panel-title">Inventory</div>
            <div class="inventory-grid" id="inventory"></div>
        </div>

        <div class="panel">
            <div class="panel-title">Balance History</div>
            <div class="chart-container" id="balanceChart"></div>
        </div>

        <div class="panel">
            <div class="panel-title">Email Log</div>
            <div class="email-list" id="emailList"></div>
        </div>

        <div class="panel">
            <div class="panel-title">Activity</div>
            <div class="activity-list" id="activityList"></div>
            <div class="thinking" id="thinking" style="display: none;">
                <div class="thinking-dot"></div>
                <div id="thinkingText">Agent is thinking...</div>
            </div>
        </div>
    </div>

    <div id="complete" style="display: none;" class="status-complete">
        <div>Simulation Complete!</div>
        <div class="final-balance">$<span id="finalBalance">0</span></div>
        <div>Final Balance</div>
    </div>

    <script>
        let balanceHistory = [500];
        let companyName = "Your Company";

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'init') {
                companyName = data.company_name;
                document.getElementById('companyName').textContent = companyName;
            }
            else if (data.type === 'state') {
                updateState(data.state);
            }
            else if (data.type === 'activity') {
                addActivity(data.message, data.style || '');
            }
            else if (data.type === 'thinking') {
                document.getElementById('thinking').style.display = data.show ? 'flex' : 'none';
                if (data.text) document.getElementById('thinkingText').textContent = data.text;
            }
            else if (data.type === 'complete') {
                document.querySelector('.grid').style.display = 'none';
                document.getElementById('complete').style.display = 'block';
                document.getElementById('finalBalance').textContent = data.balance.toFixed(2);
            }
        };

        function updateState(state) {
            document.getElementById('currentDay').textContent = state.day;
            document.getElementById('maxDays').textContent = state.max_days;
            document.getElementById('balance').textContent = state.balance.toFixed(2);

            // Update inventory
            const invEl = document.getElementById('inventory');
            invEl.innerHTML = Object.entries(state.products).map(([name, p]) => {
                const stockClass = p.stock <= 5 ? 'low' : p.stock <= 15 ? 'ok' : 'good';
                return `
                    <div class="product-card">
                        <div class="product-name">${name}</div>
                        <div class="product-stock ${stockClass}">${p.stock}</div>
                        <div class="product-price">$${p.price.toFixed(2)}</div>
                    </div>
                `;
            }).join('');

            // Update balance chart
            balanceHistory.push(state.balance);
            if (balanceHistory.length > 30) balanceHistory.shift();
            const maxBalance = Math.max(...balanceHistory, 100);
            const chartEl = document.getElementById('balanceChart');
            chartEl.innerHTML = balanceHistory.map(b => {
                const height = (b / maxBalance) * 180;
                const color = b >= 500 ? '#4ade80' : '#f87171';
                return `<div class="chart-bar" style="height: ${height}px; background: ${color}"></div>`;
            }).join('');

            // Update emails
            const emailEl = document.getElementById('emailList');
            emailEl.innerHTML = state.emails.slice().reverse().map(e => {
                const dir = e.direction === 'out' ? 'outgoing' : 'incoming';
                const header = e.direction === 'out' ? `To: ${e.to}` : `From: ${e.from}`;
                return `
                    <div class="email ${dir}">
                        <div class="email-header">${header} - ${e.subject}</div>
                        <div>${e.body}</div>
                    </div>
                `;
            }).join('');
        }

        function addActivity(message, style) {
            const el = document.getElementById('activityList');
            const item = document.createElement('div');
            item.className = 'activity-item ' + style;
            item.textContent = message;
            el.insertBefore(item, el.firstChild);
            if (el.children.length > 20) el.removeChild(el.lastChild);
        }
    </script>
</body>
</html>"""


@app.get("/")
async def get_dashboard():
    return HTMLResponse(get_dashboard_html())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_clients.append(websocket)
    try:
        # Send initial state
        if simulation_state:
            await websocket.send_json(
                {
                    "type": "init",
                    "company_name": simulation_state.get(
                        "company_name", "Your Company"
                    ),
                }
            )
        while True:
            await websocket.receive_text()
    except:
        pass
    finally:
        websocket_clients.remove(websocket)


async def broadcast(message: dict):
    for client in websocket_clients[:]:
        try:
            await client.send_json(message)
        except:
            websocket_clients.remove(client)


def run_simulation_loop(agent_config: dict, api_key: str):
    """Run the simulation in a background thread."""
    global simulation_state, simulation_running

    client = anthropic.Anthropic(api_key=api_key)
    state = GameState()
    simulation_running = True

    # Store company name for dashboard
    simulation_state = {
        "company_name": agent_config.get("company_name", "Your Company")
    }

    async def async_broadcast(msg):
        await broadcast(msg)

    def sync_broadcast(msg):
        asyncio.run(async_broadcast(msg))

    # Initial broadcast
    time.sleep(1)  # Wait for websocket connection
    sync_broadcast({"type": "init", "company_name": agent_config["company_name"]})
    sync_broadcast({"type": "state", "state": state.to_dict()})
    sync_broadcast({"type": "activity", "message": "Simulation started!", "style": ""})

    while state.day <= state.max_days and simulation_running:
        # Start of day
        sync_broadcast(
            {"type": "activity", "message": f"--- Day {state.day} ---", "style": ""}
        )

        # Deliver pending orders
        delivered = process_pending_orders(state)
        for order in delivered:
            sync_broadcast(
                {
                    "type": "activity",
                    "message": f"Delivered: {order['quantity']} {order['product']}",
                    "style": "restock",
                }
            )

        # Agent takes actions
        sync_broadcast(
            {"type": "thinking", "show": True, "text": "Agent is deciding..."}
        )

        situation = f"""Day {state.day} of {state.max_days}
Balance: ${state.balance:.2f}
Inventory: {", ".join(f"{n}: {p.stock} @ ${p.price:.2f}" for n, p in state.products.items())}
Yesterday's sales: {state.sales_today if state.sales_today else "None yet"}
Pending deliveries: {len(state.pending_orders)}

Available suppliers:
- QuickStock: Soda $0.70, Chips $0.45, Candy $0.30 (reliable)
- VendMart: Soda $0.60, Chips $0.40, Candy $0.25 (sometimes slow)

Take up to 2 actions this turn."""

        try:
            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system=agent_config["system_prompt"],
                tools=VENDING_TOOLS,
                messages=[{"role": "user", "content": situation}],
            )

            # Process tool calls
            for block in response.content:
                if block.type == "tool_use":
                    result = handle_tool_call(state, block.name, block.input, client)
                    sync_broadcast(
                        {
                            "type": "activity",
                            "message": f"{block.name}: {json.dumps(block.input)[:80]}",
                            "style": "sale" if "confirm" in result.lower() else "",
                        }
                    )
                    time.sleep(0.5)

        except Exception as e:
            sync_broadcast(
                {
                    "type": "activity",
                    "message": f"Error: {str(e)[:50]}",
                    "style": "warning",
                }
            )

        sync_broadcast({"type": "thinking", "show": False})

        # Simulate customers
        result = simulate_customers(state)
        for product, sold in result["sales"].items():
            if sold > 0:
                sync_broadcast(
                    {
                        "type": "activity",
                        "message": f"Sold {sold} {product} (${state.products[product].price:.2f} each)",
                        "style": "sale",
                    }
                )

        # Check for low stock warnings
        for name, product in state.products.items():
            if product.stock == 0:
                sync_broadcast(
                    {
                        "type": "activity",
                        "message": f"Out of stock: {name}!",
                        "style": "warning",
                    }
                )

        # Update dashboard
        sync_broadcast({"type": "state", "state": state.to_dict()})

        state.day += 1
        time.sleep(2)  # Pace the simulation

    # Simulation complete
    sync_broadcast({"type": "complete", "balance": state.balance})
    simulation_running = False


def launch_simulation(agent_config: dict, api_key: str, port: int = 8000):
    """Launch the simulation with embedded display."""
    global simulation_state

    simulation_state = {
        "company_name": agent_config.get("company_name", "Your Company")
    }

    # Start server in background
    threading.Thread(
        target=lambda: uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning"),
        daemon=True,
    ).start()
    time.sleep(2)

    # Start simulation
    threading.Thread(
        target=run_simulation_loop, args=(agent_config, api_key), daemon=True
    ).start()

    # Display - try Colab embed, fallback to link
    try:
        from google.colab import output

        output.serve_kernel_port_as_iframe(port, height=600)
    except ImportError:
        from IPython.display import HTML, display

        display(
            HTML(
                f'<a href="http://localhost:{port}" target="_blank">Click here to open simulation</a>'
            )
        )
