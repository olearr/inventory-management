"""
Tests for restocking API endpoints (demand-based restock orders).
"""
from datetime import datetime

import pytest

import mock_data  # server/ is on sys.path via conftest.py


@pytest.fixture(autouse=True)
def clean_restock_orders():
    """Restock orders live in a module-level list shared by all tests, so empty it
    around every test. Use clear() (not reassignment) because main.py holds a
    reference to the same list object."""
    mock_data.restock_orders.clear()
    yield
    mock_data.restock_orders.clear()


def _forecast(client, sku):
    """Look up one demand forecast record by SKU."""
    forecasts = client.get("/api/demand").json()
    return next(f for f in forecasts if f["item_sku"] == sku)


def _order_payload(budget, *items):
    """Build a POST body from (sku, quantity) pairs."""
    return {
        "budget": budget,
        "items": [{"item_sku": sku, "quantity": quantity} for sku, quantity in items],
    }


class TestDemandForecastRestockFields:
    """Demand forecasts carry the cost data that restocking needs."""

    def test_forecasts_have_unit_cost_and_lead_time(self, client):
        """Every forecast has a positive unit cost and a positive lead time in days."""
        data = client.get("/api/demand").json()
        assert len(data) > 0

        for forecast in data:
            assert isinstance(forecast["unit_cost"], (int, float))
            assert forecast["unit_cost"] > 0
            assert isinstance(forecast["lead_time_days"], int)
            assert forecast["lead_time_days"] > 0

    def test_forecast_unit_cost_matches_inventory_where_sku_exists(self, client):
        """PSU-501 exists in inventory, so its forecast cost must agree with it."""
        inventory = client.get("/api/inventory").json()
        item = next(i for i in inventory if i["sku"] == "PSU-501")

        assert abs(_forecast(client, "PSU-501")["unit_cost"] - item["unit_cost"]) < 0.01


class TestRestockingEndpoints:
    """Test suite for the restocking order endpoints."""

    def test_list_is_empty_initially(self, client):
        """No restock orders exist before anything is submitted."""
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_order_returns_201_with_server_computed_totals(self, client):
        """Totals, line totals and lead time are computed by the server."""
        wdg = _forecast(client, "WDG-001")
        gsk = _forecast(client, "GSK-203")
        payload = _order_payload(50000, ("WDG-001", 450), ("GSK-203", 600))

        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"] == "RO-0001"
        assert order["status"] == "Submitted"
        assert order["budget"] == 50000
        assert len(order["items"]) == 2

        expected_total = 450 * wdg["unit_cost"] + 600 * gsk["unit_cost"]
        assert abs(order["total_cost"] - expected_total) < 0.01

        line = next(i for i in order["items"] if i["item_sku"] == "WDG-001")
        assert line["item_name"] == wdg["item_name"]
        assert line["quantity"] == 450
        assert abs(line["unit_cost"] - wdg["unit_cost"]) < 0.01
        assert abs(line["line_total"] - 450 * wdg["unit_cost"]) < 0.01
        assert line["lead_time_days"] == wdg["lead_time_days"]

    def test_order_lead_time_is_the_longest_item_lead_time(self, client):
        """An order is complete only when its slowest item arrives."""
        lead_times = [
            _forecast(client, "WDG-001")["lead_time_days"],
            _forecast(client, "GSK-203")["lead_time_days"],
            _forecast(client, "FLT-405")["lead_time_days"],
        ]
        # The test is only meaningful if the items differ in lead time
        assert len(set(lead_times)) > 1

        payload = _order_payload(100000, ("WDG-001", 10), ("GSK-203", 10), ("FLT-405", 10))
        order = client.post("/api/restocking/orders", json=payload).json()

        assert order["lead_time_days"] == max(lead_times)

    def test_expected_delivery_is_submission_plus_lead_time(self, client):
        """expected_delivery is submitted_at shifted by lead_time_days."""
        order = client.post(
            "/api/restocking/orders", json=_order_payload(50000, ("WDG-001", 10))
        ).json()

        submitted = datetime.fromisoformat(order["submitted_at"])
        expected = datetime.fromisoformat(order["expected_delivery"])
        assert (expected - submitted).days == order["lead_time_days"]

    def test_order_numbers_increment(self, client):
        """Consecutive orders get consecutive numbers."""
        first = client.post("/api/restocking/orders", json=_order_payload(50000, ("WDG-001", 10)))
        second = client.post("/api/restocking/orders", json=_order_payload(50000, ("WDG-001", 10)))

        assert first.json()["order_number"] == "RO-0001"
        assert second.json()["order_number"] == "RO-0002"

    def test_submitted_orders_are_listed_newest_first(self, client):
        """GET returns the submitted orders with the most recent one first."""
        client.post("/api/restocking/orders", json=_order_payload(50000, ("WDG-001", 10)))
        client.post("/api/restocking/orders", json=_order_payload(50000, ("GSK-203", 10)))

        data = client.get("/api/restocking/orders").json()
        assert [o["order_number"] for o in data] == ["RO-0002", "RO-0001"]

    def test_prices_sent_by_the_client_are_ignored(self, client):
        """A client cannot lower the price: the server uses its own unit cost."""
        wdg = _forecast(client, "WDG-001")
        payload = {
            "budget": 50000,
            "items": [{"item_sku": "WDG-001", "quantity": 10, "unit_cost": 0.01}],
        }

        order = client.post("/api/restocking/orders", json=payload).json()

        assert abs(order["items"][0]["unit_cost"] - wdg["unit_cost"]) < 0.01
        assert abs(order["total_cost"] - 10 * wdg["unit_cost"]) < 0.01

    def test_total_equal_to_budget_is_accepted(self, client):
        """The budget is a ceiling: a total exactly at the budget is allowed."""
        wdg = _forecast(client, "WDG-001")
        budget = 10 * wdg["unit_cost"]

        response = client.post("/api/restocking/orders", json=_order_payload(budget, ("WDG-001", 10)))
        assert response.status_code == 201

    def test_total_over_budget_is_rejected(self, client):
        """A total above the budget is a 400 and stores nothing."""
        response = client.post("/api/restocking/orders", json=_order_payload(1, ("WDG-001", 10)))

        assert response.status_code == 400
        assert "budget" in response.json()["detail"].lower()
        assert client.get("/api/restocking/orders").json() == []

    def test_unknown_sku_is_rejected(self, client):
        """A SKU that is not in the demand forecast is a 400."""
        response = client.post("/api/restocking/orders", json=_order_payload(50000, ("NOPE-999", 10)))

        assert response.status_code == 400
        assert "NOPE-999" in response.json()["detail"]
        assert client.get("/api/restocking/orders").json() == []

    def test_duplicate_sku_is_rejected(self, client):
        """The same SKU twice in one order is a 400."""
        payload = _order_payload(50000, ("WDG-001", 10), ("WDG-001", 5))

        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 400
        assert "duplicate" in response.json()["detail"].lower()

    def test_empty_item_list_is_rejected(self, client):
        """An order without items is a 400."""
        response = client.post("/api/restocking/orders", json=_order_payload(50000))

        assert response.status_code == 400
        assert client.get("/api/restocking/orders").json() == []

    @pytest.mark.parametrize("quantity", [0, -5])
    def test_quantity_below_one_is_rejected(self, client, quantity):
        """Quantities below 1 fail validation."""
        response = client.post(
            "/api/restocking/orders", json=_order_payload(50000, ("WDG-001", quantity))
        )
        assert response.status_code == 422

    def test_wrong_types_are_rejected(self, client):
        """A non-numeric quantity or budget fails validation."""
        bad_quantity = {"budget": 50000, "items": [{"item_sku": "WDG-001", "quantity": "many"}]}
        bad_budget = {"budget": "lots", "items": [{"item_sku": "WDG-001", "quantity": 10}]}

        assert client.post("/api/restocking/orders", json=bad_quantity).status_code == 422
        assert client.post("/api/restocking/orders", json=bad_budget).status_code == 422

    def test_negative_budget_is_rejected(self, client):
        """A negative budget fails validation."""
        response = client.post("/api/restocking/orders", json=_order_payload(-1, ("WDG-001", 10)))
        assert response.status_code == 422

    def test_restock_orders_do_not_appear_in_customer_orders(self, client):
        """Restock orders are a separate list from the ORD- customer orders."""
        before = len(client.get("/api/orders").json())
        client.post("/api/restocking/orders", json=_order_payload(50000, ("WDG-001", 10)))

        assert len(client.get("/api/orders").json()) == before

    def test_total_one_cent_over_budget_is_rejected(self, client):
        """The budget boundary is exact: one cent over the budget is a 400."""
        wdg = _forecast(client, "WDG-001")
        total = round(10 * wdg["unit_cost"], 2)

        response = client.post(
            "/api/restocking/orders", json=_order_payload(round(total - 0.01, 2), ("WDG-001", 10))
        )
        assert response.status_code == 400
        assert client.get("/api/restocking/orders").json() == []

    @pytest.mark.parametrize("literal", ["Infinity", "-Infinity", "NaN"])
    def test_non_finite_budget_is_rejected(self, client, literal):
        """Python's JSON parser accepts the bare literals Infinity and NaN. They must not
        switch the budget check off, end up stored, or turn the 422 into a 500 (the error
        body echoes the rejected value, which is not valid JSON)."""
        response = client.post(
            "/api/restocking/orders",
            content='{"budget": %s, "items": [{"item_sku": "WDG-001", "quantity": 1}]}' % literal,
            headers={"content-type": "application/json"},
        )

        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "budget"]
        assert client.get("/api/restocking/orders").json() == []

    def test_budget_above_the_maximum_is_rejected(self, client):
        """An absurdly large budget fails validation instead of disabling the budget check."""
        response = client.post(
            "/api/restocking/orders", json=_order_payload(10**12, ("WDG-001", 10))
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("quantity", [1_000_001, 10**400])
    def test_quantity_above_the_maximum_is_rejected(self, client, quantity):
        """A huge quantity is a 422, not an arithmetic overflow (500)."""
        response = client.post(
            "/api/restocking/orders", json=_order_payload(50000, ("WDG-001", quantity))
        )
        assert response.status_code == 422
        assert client.get("/api/restocking/orders").json() == []
