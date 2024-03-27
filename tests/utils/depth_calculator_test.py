from typing import List

import pytest

from utils.depth_calculator import calculate_depth_price


@pytest.mark.parametrize("depth, expected_price, expected_volume, orders", [
    # single order adds up to requested depth
    (10.0, 10.5, 10.0, [["10.5", "100"]]),
    # two different orders added up to requested depth
    (10.0, 15.0, 10.0, [["10", "5"], ["20", "200"]]),
    # total volume does not add up to requested depth
    (10.0, 16.66, 6.0, [["10", "2"], ["20", "4"]]),
    # bid orders are taken in descending order
    (10.0, 36.0, 10.0, [["40", "8"], ["20", "200"]])
])
def test_calculate_depth_price(depth: float, expected_price: float, expected_volume: float, orders: List[List[str]]):
    actual = calculate_depth_price(depth, orders)
    print("ACTUAL PRICE: ", actual)
    approx_price = pytest.approx(expected_price, .01)
    approx_volume = pytest.approx(expected_volume, .01)
    assert (approx_price, approx_volume) == actual
