from veriflow_api.main import app


def test_phase_1b_routes_are_registered() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/workspaces" in paths
    assert "/api/v1/workspaces/{workspace_id}" in paths
    assert "/api/v1/workspaces/{workspace_id}/audit-logs" in paths
