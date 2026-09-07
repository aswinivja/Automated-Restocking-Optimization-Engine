%%writefile test.py
"""
test_warehouse.py
Pytest tests for core behaviors.
"""

import pytest
from warehouse import (
    Warehouse, InventoryItem, SupplierAgent,
    EOQStrategy, HeuristicStrategy, LPStrategy
)

def build_small_warehouse(strategy):
    wh = Warehouse(strategy)
    supplier = SupplierAgent("TestSup", min_order=5, max_supply_per_order=200, lead_time_range=(1,2), fill_rate=1.0)
    wh.register_item(InventoryItem("X1", "ItemX", 50, 365, unit_cost=10, holding_cost=1.0, order_cost=10, max_capacity=500, supplier=supplier))
    wh.register_item(InventoryItem("X2", "ItemY", 30, 365, unit_cost=5, holding_cost=0.5, order_cost=8, max_capacity=300, supplier=supplier))
    return wh

def test_no_negative_stock_eoq():
    wh = build_small_warehouse(EOQStrategy())
    wh.simulate(days=10, seed=1)
    for item in wh.items.values():
        assert all(s >= 0 for s in item.stock_history)

def test_lp_avoids_massive_stockouts():
    wh = build_small_warehouse(LPStrategy(shortage_penalty=200.0, planning_days=14))
    wh.simulate(days=14, seed=1)
    # service level should be reasonable (no more than 90% lost)
    service = wh.compute_service_level()
    assert service > 0.1  # >10% service (very weak but ensures not all demand lost)

def test_heuristic_orders_and_costs():
    wh = build_small_warehouse(HeuristicStrategy(safety_factor=0.2, weeks=1))
    wh.simulate(days=14, seed=1)
    # ensure costs recorded and orders placed at least once
    assert any(item.total_ordered > 0 or sum(item.reorder_history) > 0 for item in wh.items.values())
