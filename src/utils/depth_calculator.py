from typing import List, Tuple

"""
This function assumes that the orders are already sorted by price.
For bids, the orders are sorted in descending order by price (first index)
For asks, the orders are sorted in ascending order by price.
The second entry in each order is the volume of the underlying.
"""
def calculate_depth_price(depth: float, orders: List[List[str]]) -> Tuple[float, float]:
    total_price = 0.0
    depth_used = 0
    for order in orders:
        price, volume = float(order[0]), float(order[1])
        depth_needed = min(depth - depth_used, volume)
        total_price += price * depth_needed
        depth_used += depth_needed
    total_price = total_price / depth_used if depth_used > 0 else 0
    return total_price, depth_used
