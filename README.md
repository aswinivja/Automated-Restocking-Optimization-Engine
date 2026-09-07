# Automated Restocking Optimization Engine (AROE)

## Overview
The **Automated Restocking Optimization Engine (AROE)** is a Python-based inventory optimization system that automates the process of determining optimal reorder quantities for products in an FMCG environment. The project integrates **Object-Oriented Programming (OOP)** principles with **mathematical optimization** to achieve efficient, scalable, and maintainable inventory management.

This project was developed as part of the course **MA5741: Object-Oriented Programming** under the guidance of **Dr. Neelesh Shankar Upadhye** at the **Department of Mathematics, Indian Institute of Technology Madras**.

---

## Abstract
This system calculates optimal reorder quantities using three optimization strategies:

1. **Economic Order Quantity (EOQ)** – Closed-form analytical model minimizing total cost.  
2. **Linear Programming (LP)** – Constrained optimization using the PuLP solver for cost minimization under supplier and capacity limits.  
3. **Heuristic Algorithm** – A rule-based approach employing safety stock logic for quick, practical decision-making.

The project demonstrates advanced use of OOP concepts such as **abstraction**, **encapsulation**, **inheritance**, **polymorphism**, and **composition**, adhering to all five **SOLID design principles**.

---

## Features
- Automatic restocking simulation for multiple products and suppliers.  
- Configurable optimization strategy (EOQ, LP, or Heuristic).  
- Supplier agent with lead-time and capacity constraints.  
- Visualization of inventory levels, reorders, and cumulative costs.  
- Extensible architecture for adding new optimization strategies.  
- Compliance with SOLID and Strategy Design Pattern.

---

## Mathematical Framework

### Economic Order Quantity (EOQ)
\[
Q^* = \sqrt{\frac{2DS}{H}}
\]
where  
- \(D\) = annual demand,  
- \(S\) = ordering cost per order,  
- \(H\) = holding cost per unit per year.

Minimizes total variable cost:  
\[
TVC(Q) = \frac{DS}{Q} + \frac{HQ}{2}
\]

### Linear Programming (LP)
Minimizes total inventory cost under real-world constraints:
\[
\text{Minimize: } Z = \sum_i (c_i Q_i + \frac{h_i}{2}Q_i + pS_i)
\]
Subject to:
- Demand satisfaction  
- Supplier capacity  
- Warehouse capacity  
- Budget limits

### Heuristic Strategy
Uses a safety stock factor:
\[
SS_i = \alpha \cdot d_i
\]
and triggers reorders if stock < \(d_i(1+\alpha)\), ordering stock for the next few days of coverage.

---

## Object-Oriented Design

**Key Classes:**
- `RestockStrategy` – Abstract base class defining the common interface.  
- `EOQStrategy`, `LPStrategy`, `HeuristicStrategy` – Implement different optimization methods.  
- `InventoryItem` – Represents an FMCG product with encapsulated stock logic.  
- `SupplierAgent` – Simulates supplier lead time, fill rate, and constraints.  
- `Warehouse` – Central simulation engine coordinating all components.

**Design Patterns Used:**
- **Strategy Pattern** – Enables interchangeable optimization algorithms at runtime.  
- **Composition Over Inheritance** – Promotes modularity and flexibility.  
- **SOLID Principles** – Ensures maintainable, extensible, and testable architecture.

---

## Implementation Details
The project consists of the following core files:

| File | Description |
|------|--------------|
| `warehouse.py` | Core logic implementing strategies, supplier agent, and warehouse system. |
| `main.py` | Entry point to execute and visualize simulations. |
| `test_warehouse.py` | Unit tests for CI/CD and strategy validation. |
| `requirements.txt` | Dependencies required for project execution. |

---

## Visualization
The system provides plots for:
- Inventory level variation over time.  
- Cumulative cost growth.  
- Demand vs reorder activity per product.

These visualizations help evaluate and compare the efficiency of different strategies.

---

## Results Summary
| Strategy | Characteristics | Performance |
|-----------|----------------|-------------|
| EOQ | Analytical, scalable | Low computational cost, moderate optimality |
| LP | Exact optimization | Best cost efficiency, higher complexity |
| Heuristic | Rule-based | Fast and flexible, approximate results |

---

## Limitations
- Assumes deterministic demand (no seasonality or trend).  
- Single-warehouse model without network-level optimization.  
- LP scalability decreases for large numbers of products.  
- Limited test coverage for extreme edge cases.

---

## Future Enhancements
- Integration of **Reinforcement Learning** (RL) for adaptive restocking.  
- Demand forecasting using **time-series or ML models (ARIMA, LSTM)**.  
- Multi-echelon warehouse network optimization.  
- Web-based GUI for parameter tuning and real-time simulation.  
- API integration with ERP systems (SAP, Oracle).

---
