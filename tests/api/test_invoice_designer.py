import copy

from app.models.app_setting import AppSetting


def test_invoice_layout_save_and_versioning(client, db_session):
    # Ensure initial state returns defaults
    initial_resp = client.get("/api/v1/invoice-designer/layout")
    assert initial_resp.status_code == 200
    initial_data = initial_resp.json()
    assert initial_data["layout"] == []

    payload = {
        "layout": [
            {
                "field": "companyName",
                "type": "text",
                "x": 60,
                "y": 40,
                "width": 240,
                "height": 80,
                "content": "Acme Corp",
                "fontFamily": "Inter, sans-serif",
                "fontSize": 18,
                "color": "#111827",
                "align": "left",
            }
        ],
        "form_data": {
            "customer_name": "Example Customer",
            "invoice_number": "INV-001",
            "items": [
                {"description": "Widget", "quantity": 2, "price": 10.5, "total": 21.0}
            ],
        },
        "metadata": {"gridVisible": True, "snapEnabled": False},
    }

    first_save = client.post("/api/v1/invoice-designer/layout", json=payload)
    assert first_save.status_code == 200
    first_data = first_save.json()

    assert first_data["layout"][0]["field"] == "companyName"
    assert first_data["version"] == 1
    assert first_data["updated_at"] is not None

    settings = db_session.query(AppSetting).first()
    assert settings is not None
    stored = settings.invoice_designer_config
    assert stored["layout"][0]["x"] == 60
    assert stored["form_data"]["invoice_number"] == "INV-001"

    # Saving identical payload should not bump version or timestamp
    repeat_save = client.post("/api/v1/invoice-designer/layout", json=payload)
    assert repeat_save.status_code == 200
    repeat_data = repeat_save.json()
    assert repeat_data["version"] == 1
    assert repeat_data["updated_at"] == first_data["updated_at"]

    # Modify layout to trigger a new version
    modified_payload = copy.deepcopy(payload)
    modified_payload["layout"][0]["x"] = 200

    second_save = client.post("/api/v1/invoice-designer/layout", json=modified_payload)
    assert second_save.status_code == 200
    second_data = second_save.json()
    assert second_data["version"] == 2
    assert second_data["updated_at"] != first_data["updated_at"]

    settings = db_session.query(AppSetting).first()
    stored = settings.invoice_designer_config
    assert stored["layout"][0]["x"] == 200
