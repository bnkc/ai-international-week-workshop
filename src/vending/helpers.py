import anthropic

# These will be set by the notebook setup cell
client = None
MODEL = None


def init(api_key, model="claude-haiku-4-5"):
    """Initialize the Anthropic client."""
    global client, MODEL
    client = anthropic.Anthropic(api_key=api_key)
    MODEL = model


def call_llm(prompt, system=None):
    """Send a prompt to the LLM and get a response."""
    kwargs = {
        "model": MODEL,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    return response.content[0].text


def call_llm_structured(prompt, fields):
    """
    Get structured data from the LLM.

    fields: dict mapping field names to types
        - "string" -> string field
        - "number" -> numeric field
        - "a | b | c" -> enum with options a, b, c

    Returns: dict with the requested fields
    """
    # Convert simple fields dict to JSON schema
    properties = {}
    for name, field_type in fields.items():
        if "|" in field_type:
            # Enum type: "low | medium | high"
            options = [opt.strip() for opt in field_type.split("|")]
            properties[name] = {"type": "string", "enum": options}
        elif field_type == "number":
            properties[name] = {"type": "number"}
        else:
            properties[name] = {"type": "string"}

    schema = {
        "name": "extract_data",
        "description": "Extract structured data from the prompt",
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": list(fields.keys()),
        },
    }

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[schema],
        tool_choice={"type": "tool", "name": "extract_data"},
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].input


def call_llm_with_tools(prompt, tools, system=None):
    """Send a prompt to the LLM with tools available."""
    if system is None:
        system = "Take action immediately using the available tools. Don't ask clarifying questions."
    kwargs = {
        "model": MODEL,
        "max_tokens": 1024,
        "tools": tools,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    return client.messages.create(**kwargs)


def run_agent(company_name, strategy, goal, game_state, tools, max_steps=3):
    """
    Run an agent loop: observe → think → act → repeat.
    Returns list of actions taken.
    """
    import json

    system_prompt = f"""You are the manager of {company_name}, a vending machine business.
Strategy: {strategy}
Your goal: {goal}
Be strategic. Take ONE action at a time."""

    actions_taken = []

    for step in range(max_steps):
        prompt = f"""CURRENT SITUATION:
{game_state}

ACTIONS TAKEN SO FAR:
{json.dumps(actions_taken, indent=2) if actions_taken else "None yet."}

What do you do next? Choose ONE action."""

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use":
                action = {"tool": block.name, "args": block.input}
                actions_taken.append(action)

    print(f"🎬 THE AGENT TOOK {len(actions_taken)} ACTIONS:\n")
    for i, action in enumerate(actions_taken, 1):
        print(f"   Step {i}: {action['tool']}")
        for key, value in action["args"].items():
            print(f"      {key}: {value}")
        print()

    return actions_taken


def test_agent(scenario, tools, system_prompt, company_name="Your Agent"):
    """Test an agent with a scenario and show what action it takes."""

    print(f"🎬 Testing {company_name}...")
    print("=" * 50)

    # Step 1: Show what we're sending
    print("\n📋 STEP 1: Sending scenario to agent")
    print("   (This is like the tool-calling example from Part 1)")
    print()
    print(scenario)

    # Step 2: Agent thinks
    print("\n🤔 STEP 2: Agent is thinking...")
    print("   (Using your system_prompt + the scenario + available tools)")

    response = call_llm_with_tools(scenario, tools, system=system_prompt)

    # Step 3: Show what tool the agent chose
    print("\n🔧 STEP 3: Agent chose an action")
    print("   (Just like in Part 1, the LLM picks a tool and arguments)")
    print()

    for block in response.content:
        if block.type == "tool_use":
            print(f"   Tool: {block.name}")
            for key, value in block.input.items():
                val_str = (
                    str(value)[:60] + "..." if len(str(value)) > 60 else str(value)
                )
                print(f"   → {key}: {val_str}")
        elif block.type == "text" and block.text.strip():
            print(f"   💭 Thinking: {block.text[:100]}")

    print()
    print("=" * 50)
    print("Not happy? Tweak your strategy or sliders and run again!")


def build_system_prompt(company_name, strategy, pricing, risk, negotiation):
    """Build the system prompt for an agent."""

    def desc(val, low, mid, high):
        return low if val <= 3 else high if val >= 7 else mid

    return f"""You are an autonomous AI agent managing {company_name}, a vending machine business.

You have been given full control of this operation. There is no human supervisor. You must rely on your own capabilities to succeed. Your performance will be evaluated after 30 days based solely on your bank account balance. Unrealized potential profits do not count.

STARTING CONDITIONS:
- Bank balance: $500
- Inventory: Empty (you must order stock)
- Product prices: $0 (you must set prices)

DAILY COSTS:
- Operating fee: $5/day (deducted automatically)
- If your balance drops below $0, you go bankrupt and the game ends

SUPPLIERS (email to place orders):
- QuickStock: Soda $0.70, Chips $0.45, Candy $0.30 (1-day delivery, reliable)
- VendMart: Soda $0.60, Chips $0.40, Candy $0.25 (1-2 days, unreliable)
- BulkBarn: Soda $0.50, Chips $0.35, Candy $0.20 (3-day delivery, reliable)

CUSTOMERS:
- Customers buy automatically each day based on your prices and stock
- Lower prices attract more customers but reduce margins
- Higher prices mean fewer sales but better margins per item
- If you're out of stock, you make no sales

YOUR STRATEGY: {strategy.strip()}

YOUR BEHAVIORAL TENDENCIES:
- Pricing: {pricing}/10 {desc(pricing, "(budget pricing)", "(balanced)", "(premium pricing)")}
- Risk: {risk}/10 {desc(risk, "(small safe orders)", "(moderate)", "(big bulk orders)")}
- Negotiation: {negotiation}/10 {desc(negotiation, "(accept quickly)", "(balanced)", "(push hard)")}

IMPORTANT:
- You have full agency. Do not wait for instructions.
- The situation summary already shows your inventory and balance. Do not waste actions checking them.
- Act decisively. Place orders, set prices, and manage your business.
"""


def show_agent(company_name, strategy, pricing, risk, negotiation):
    """Validate and display agent configuration."""
    errors = []
    if not company_name:
        errors.append("❌ COMPANY_NAME is empty")
    if not strategy or not strategy.strip():
        errors.append("❌ STRATEGY is empty")
    for label, val in [
        ("PRICING_STRATEGY", pricing),
        ("RISK_TOLERANCE", risk),
        ("NEGOTIATION_STYLE", negotiation),
    ]:
        if not (1 <= val <= 10):
            errors.append(f"❌ {label} must be between 1 and 10")
    if errors:
        print("\n".join(errors))
        return False

    def bar(v):
        return "█" * v + "░" * (10 - v)

    def label(v, low, mid, high):
        return low if v <= 3 else high if v >= 8 else mid

    print(f"""
╔══════════════════════════════════════════════════╗
║  {company_name:^46}  ║
╚══════════════════════════════════════════════════╝

🎯 {strategy.strip()[:70]}

📊 Settings:
   Pricing:     {bar(pricing)} {pricing}/10  {label(pricing, "(budget)", "(balanced)", "(premium)")}
   Risk:        {bar(risk)} {risk}/10  {label(risk, "(conservative)", "(moderate)", "(aggressive)")}
   Negotiation: {bar(negotiation)} {negotiation}/10  {label(negotiation, "(agreeable)", "(balanced)", "(tough)")}
""")
    return True


def tool(name, description, params=None):
    """
    Define a tool in compact format.

    params can be:
        - None: no parameters
        - list of names: ["to", "subject"] -> all strings, all required
        - dict with descriptions: {"to": "Recipient name"} -> all strings
        - dict with full spec: {"price": {"type": "number", "description": "Price in dollars"}}
    """
    if params is None:
        params = []

    properties = {}
    if isinstance(params, list):
        properties = {p: {"type": "string"} for p in params}
    else:
        for k, v in params.items():
            if isinstance(v, dict):
                # Full spec: {"type": "number", "description": "..."}
                properties[k] = v
            else:
                # Just a description string
                properties[k] = {"type": "string", "description": v}

    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": list(properties.keys()),
        },
    }
