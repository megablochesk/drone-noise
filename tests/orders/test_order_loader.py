import pandas as pd

from orders.order_loader import load_orders
from tests.legacy_reference import load_legacy_order_generator

LEGACY_ORDER_GENERATOR = load_legacy_order_generator()


def test_orders_match_the_published_loader(tmp_path):
    """Characterisation: same CSV, same Order objects as the loader at the published baseline commit."""
    orders_path = str(tmp_path / "orders.csv")
    pd.DataFrame({
        "Order ID": [1, 2, 3, 4],
        "Start Northing": [185648.81, 182049.78, 164142.21, 185648.81],
        "Start Easting": [520386.09, 538402.03, 530990.34, 520386.09],
        "End Northing": [184874.09, 182108.19, 163000.5, 190000.0],
        "End Easting": [515645.04, 537376.7, 531000.25, 521000.0],
    }).to_csv(orders_path, index=False)

    assert load_orders(4, orders_path) == LEGACY_ORDER_GENERATOR.load_orders(4, orders_path)
    assert load_orders(2, orders_path) == LEGACY_ORDER_GENERATOR.load_orders(2, orders_path)
