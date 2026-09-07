%%writefile main.py
"""
main.py
Example runner that creates three warehouses (EOQ, LP, Heuristic),
simulates them over the same random seed, and plots & prints comparison.
"""

from warehouse import (
    Warehouse, InventoryItem, SupplierAgent,
    EOQStrategy, HeuristicStrategy, LPStrategy
)
import matplotlib.pyplot as plt

def build_warehouse(strategy):
    wh = Warehouse(strategy)
    supplier_fast = SupplierAgent("FastSup", min_order=10, max_supply_per_order=500, lead_time_range=(1,3), fill_rate=0.98)
    supplier_slow = SupplierAgent("SlowSup", min_order=20, max_supply_per_order=300, lead_time_range=(4,7), fill_rate=0.9)

    wh.register_item(InventoryItem("S1", "Soap", 150, 1200, unit_cost=10, holding_cost=1.5, order_cost=20, max_capacity=1000, supplier=supplier_fast))
    wh.register_item(InventoryItem("S2", "Shampoo", 120, 1500, unit_cost=25, holding_cost=3.0, order_cost=40, max_capacity=800, supplier=supplier_fast))
    wh.register_item(InventoryItem("B1", "Biscuits", 200, 2000, unit_cost=5, holding_cost=0.8, order_cost=15, max_capacity=1500, supplier=supplier_slow))
    wh.register_item(InventoryItem("T1", "Toothpaste", 100, 1000, unit_cost=12, holding_cost=1.8, order_cost=30, max_capacity=700, supplier=supplier_fast))

    return wh

def run_all(seed=42, days=90):
    strategies = [
        (EOQStrategy(), "EOQ"),
        (LPStrategy(shortage_penalty=150.0, planning_days=30, budget=None), "LP"),
        (HeuristicStrategy(safety_factor=0.3, weeks=2), "Heuristic")
    ]

    results = []
    warehouses = []
    for strat, name in strategies:
        wh = build_warehouse(strat)
        wh.simulate(days=days, seed=seed)
        warehouses.append((wh, name))
        rows = wh.summary()
        service_level = wh.compute_service_level()
        results.append((name, rows, service_level))

    # Print summary
    for name, rows, service in results:
        print(f"\n===== {name} Strategy Results =====")
        for r in rows:
            print(f"{r['name']}: Stock={r['stock']}, TotalOrdered={r['total_ordered']}, Cost={r['total_cost']:.2f}, Lost={r['lost_sales']}")
        print(f"Service level: {service*100:.2f}%")

    # Plot stock time-series for all items across strategies using subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    axes = axes.flatten() # Flatten the 2x2 array of axes for easy iteration

    for i, sku in enumerate(warehouses[0][0].items.keys()): # Iterate through SKUs (assuming all warehouses have the same SKUs)
        ax = axes[i]
        for wh, name in warehouses:
            item = wh.items[sku]
            ax.plot(item.stock_history, label=f"{name}")
        ax.set_title(f"Stock of {item.name} ({sku})")
        ax.set_xlabel("Day")
        ax.set_ylabel("Stock")
        ax.legend()
        ax.grid(True)

    plt.tight_layout()
    plt.suptitle("Stock Levels of All Items Across Strategies", y=1.02, fontsize=16)
    plt.savefig('all_items_stock_across_strategies.png') # Save the figure
    plt.show()

    # Plot total cost comparison
    names = []
    total_costs = []
    for wh, name in warehouses:
        names.append(name)
        total_costs.append(sum(item.total_cost for item in wh.items.values()))
    plt.figure(figsize=(8,4))
    plt.bar(names, total_costs)
    plt.ylabel("Total Cost"); plt.title("Total Cost by Strategy"); plt.show()
