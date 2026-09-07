"""
warehouse.py

Core inventory engine for the Automated Restocking Optimization Engine.

Classes:
 - RestockStrategy (abstract)
 - EOQStrategy, HeuristicStrategy, LPStrategy
 - SupplierAgent
 - InventoryItem
 - Warehouse

LPStrategy uses PuLP; if PuLP is not installed and LPStrategy is used,
an informative ImportError is raised.
"""

from abc import ABC, abstractmethod
import math
import random
import collections
from typing import Dict, Tuple

# plotting import kept here for optional helpers (main.py will call plotting)
import matplotlib.pyplot as plt

try:
    import pulp
except Exception:
    pulp = None


# ---------------------------
# Strategy Interface
# ---------------------------
class RestockStrategy(ABC):
    @abstractmethod
    def plan(self, warehouse: "Warehouse", day: int) -> Dict[str, int]:
        """
        Return a plan mapping sku -> requested_quantity (int).
        """
        pass


# ---------------------------
# EOQ Strategy
# ---------------------------
class EOQStrategy(RestockStrategy):
    def plan(self, warehouse, day):
        plan = {}
        for sku, item in warehouse.items.items():
            D = item.annual_demand
            S = item.order_cost
            H = item.holding_cost
            if D <= 0 or S <= 0 or H <= 0:
                continue
            q = int(round(math.sqrt((2 * D * S) / H)))
            reorder_point = int(math.ceil(item.daily_demand * item.supplier.expected_lead_time_mean()))
            if item.stock <= reorder_point:
                plan[sku] = q
        return plan


# ---------------------------
# Heuristic Strategy
# ---------------------------
class HeuristicStrategy(RestockStrategy):
    def __init__(self, safety_factor: float = 0.3, weeks=2):
        self.safety_factor = safety_factor
        self.weeks = weeks  # order for `weeks` worth of demand

    def plan(self, warehouse, day):
        plan = {}
        for sku, item in warehouse.items.items():
            safety = int(math.ceil(item.daily_demand * self.safety_factor))
            if item.stock < int(item.daily_demand) + safety:
                plan[sku] = int(round(item.daily_demand * 7 * self.weeks))
        return plan


# ---------------------------
# LP Strategy with shortage penalty (avoids trivial zero ordering)
# ---------------------------
class LPStrategy(RestockStrategy):
    def __init__(self, shortage_penalty: float = 100.0, planning_days: int = 30, budget: float = None):
        """
        shortage_penalty: high cost per unit short to discourage stockouts
        planning_days: horizon (days) LP considers demand over when planning
        budget: optional budget cap on purchase cost this decision epoch
        """
        if pulp is None:
            raise ImportError("PuLP is required for LPStrategy. Install with `pip install pulp`.")
        self.shortage_penalty = float(shortage_penalty)
        self.planning_days = int(planning_days)
        self.budget = budget

    def plan(self, warehouse, day):
        # Candidates: all items (we let LP decide), but it's fine to restrict to low-stock ones
        SKUs = list(warehouse.items.keys())
        if not SKUs:
            return {}

        # Build LP
        prob = pulp.LpProblem("Restock_with_Shortage", pulp.LpMinimize)

        Q = {sku: pulp.LpVariable(f"Q_{sku}", lowBound=0, cat="Continuous") for sku in SKUs}
        S = {sku: pulp.LpVariable(f"S_{sku}", lowBound=0, cat="Continuous") for sku in SKUs}  # shortage variables

        # Objective: purchase cost + holding proxy + shortage penalty
        prob += pulp.lpSum(
            [
                warehouse.items[sku].unit_cost * Q[sku]
                + (warehouse.items[sku].holding_cost / 2.0) * Q[sku]
                + self.shortage_penalty * S[sku]
                for sku in SKUs
            ]
        )

        # Constraints: for each sku, ensure stock + Q - shortage >= demand_over_planning_horizon - incoming_arrivals_within_horizon
        for sku in SKUs:
            item = warehouse.items[sku]
            demand_horizon = item.daily_demand * self.planning_days
            # compute already scheduled incoming that will arrive within planning horizon
            incoming_within = sum(qty for (arr_day, qty) in warehouse.incoming.get(sku, []) if arr_day <= day + self.planning_days)
            # Current stock + orders - shortage + incoming >= demand_horizon
            prob += (item.stock + Q[sku] + incoming_within - S[sku]) >= demand_horizon

            # Supplier capacity constraint: can't order more than supplier max per order and warehouse capacity
            ub = min(item.supplier.max_supply_per_order, max(0, item.max_capacity - item.stock))
            prob += Q[sku] <= ub

        # Budget constraint optional
        if self.budget is not None:
            prob += pulp.lpSum([warehouse.items[sku].unit_cost * Q[sku] for sku in SKUs]) <= self.budget

        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        plan = {}
        for sku in SKUs:
            qval = Q[sku].value()
            q_final = int(round(qval)) if qval is not None else 0
            # Avoid tiny fractional orders below supplier min by rounding up to min_order when appropriate
            if q_final > 0 and q_final < item.supplier.min_order_qty(item.supplier):
                q_final = item.supplier.min_order_qty(item.supplier)
            plan[sku] = q_final
        return plan


# ---------------------------
# Supplier Agent
# ---------------------------
class SupplierAgent:
    def __init__(self, name: str, min_order: int = 10, max_supply_per_order: int = 1000,
                 lead_time_range: Tuple[int, int] = (1, 5), fill_rate: float = 1.0):
        self.name = name
        self.min_order = int(min_order)
        self.max_supply_per_order = int(max_supply_per_order)
        self.lead_time_range = (int(lead_time_range[0]), int(lead_time_range[1]))
        self.fill_rate = float(fill_rate)

    def place_order(self, sku: str, requested_qty: int, day: int) -> Tuple[int, int]:
        """
        Returns (accepted_qty, arrival_day) or (0, None) if rejected due to MOQ.
        accepted_qty is min(requested_qty, max_supply_per_order) scaled by fill_rate.
        arrival_day = day + random lead time within lead_time_range.
        """
        if requested_qty <= 0:
            return 0, None
        if requested_qty < self.min_order:
            return 0, None
        accepted = min(requested_qty, self.max_supply_per_order)
        accepted = int(round(accepted * self.fill_rate))
        lt = random.randint(self.lead_time_range[0], self.lead_time_range[1])
        arrival = day + lt
        return accepted, arrival

    # helper to let strategies check supplier min order
    def min_order_qty(self, supplier_self=None):
        return self.min_order

    def expected_lead_time_mean(self) -> float:
        return (self.lead_time_range[0] + self.lead_time_range[1]) / 2.0


# ---------------------------
# Inventory Item
# ---------------------------
class InventoryItem:
    def __init__(self, sku: str, name: str, initial_stock: int, annual_demand: float,
                 unit_cost: float, holding_cost: float, order_cost: float, max_capacity: int,
                 supplier: SupplierAgent):
        self.sku = sku
        self.name = name
        self.stock = int(initial_stock)
        self.annual_demand = float(annual_demand)
        self.unit_cost = float(unit_cost)
        self.holding_cost = float(holding_cost)
        self.order_cost = float(order_cost)
        self.max_capacity = int(max_capacity)
        self.supplier = supplier

        self.daily_demand = self.annual_demand / 365.0

        # tracking
        self.stock_history = []
        self.demand_history = []
        self.reorder_history = []
        self.cost_history = []
        self.total_ordered = 0
        self.total_cost = 0.0
        self.lost_sales = 0

    def sell(self, qty: int) -> Tuple[int, int]:
        qty = int(qty)
        sold = min(self.stock, qty)
        self.stock -= sold
        lost = qty - sold
        self.lost_sales += lost
        return sold, lost

    def receive(self, qty: int) -> int:
        qty = int(qty)
        accepted = min(qty, max(0, self.max_capacity - self.stock))
        self.stock += accepted
        return accepted

    def add_cost_for_order(self, qty: int):
        qty = int(qty)
        if qty <= 0:
            return
        self.total_cost += (self.order_cost + qty * self.unit_cost)
        self.total_ordered += qty

    def record_day(self, demand: int, requested: int):
        self.stock_history.append(self.stock)
        self.demand_history.append(int(demand))
        self.reorder_history.append(int(requested))
        self.cost_history.append(float(self.total_cost))


# ---------------------------
# Warehouse
# ---------------------------
class Warehouse:
    def __init__(self, strategy: RestockStrategy):
        self.strategy = strategy
        self.items: Dict[str, InventoryItem] = {}
        self.incoming: Dict[str, list] = collections.defaultdict(list)  # sku -> list of (arrival_day, qty)

    def register_item(self, item: InventoryItem):
        self.items[item.sku] = item

    def _receive_arrivals(self, day: int):
        for sku, queue in list(self.incoming.items()):
            while queue and queue[0][0] <= day:
                arrival_day, qty = queue.pop(0)
                item = self.items.get(sku)
                if item:
                    item.receive(qty)

    def _place_orders(self, plan: Dict[str, int], day: int):
        for sku, req in plan.items():
            if req <= 0:
                continue
            item = self.items.get(sku)
            if item is None:
                continue
            accepted, arrival = item.supplier.place_order(sku, req, day)
            if accepted > 0 and arrival is not None:
                self.incoming[sku].append((arrival, accepted))
                item.add_cost_for_order(accepted)
            # if accepted == 0, supplier rejected (MOQ); no cost added

    def simulate(self, days: int = 90, start_day: int = 1, seed: int = None):
        if seed is not None:
            random.seed(seed)
        for day in range(start_day, start_day + days):
            # 1) receive arrivals scheduled for today
            self._receive_arrivals(day)

            # 2) demand and sales
            day_demands = {}
            for item in self.items.values():
                demand = random.randint(5, 15)  # stochastic demand
                sold, lost = item.sell(demand)
                day_demands[item.sku] = demand

            # 3) decide orders (strategy)
            plan = self.strategy.plan(self, day)

            # 4) place orders with suppliers
            self._place_orders(plan, day)

            # 5) record day stats
            for sku, item in self.items.items():
                requested = plan.get(sku, 0)
                item.record_day(demand=day_demands.get(sku, 0), requested=requested)

    def summary(self):
        rows = []
        for item in self.items.values():
            rows.append({
                "sku": item.sku,
                "name": item.name,
                "stock": item.stock,
                "total_ordered": item.total_ordered,
                "total_cost": item.total_cost,
                "lost_sales": item.lost_sales
            })
        return rows

    # optional plotting helpers
    def plot_stock(self, title=None):
        plt.figure(figsize=(10, 5))
        for item in self.items.values():
            plt.plot(item.stock_history, label=f"{item.name} ({item.sku})")
        plt.title(title or "Stock Levels")
        plt.xlabel("Day")
        plt.ylabel("Stock")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def compute_service_level(self) -> float:
        # service level = 1 - (total lost sales / total demand)
        total_lost = sum(item.lost_sales for item in self.items.values())
        total_demand = sum(sum(item.demand_history) for item in self.items.values())
        if total_demand <= 0:
            return 1.0
        return 1.0 - (total_lost / total_demand)
