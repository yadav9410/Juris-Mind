from app.main import app

def test_professional_platform_routes_registered():
    paths = app.openapi()["paths"]
    expected = {
        "/platform/matters",
        "/platform/matters/{matter_id}",
        "/platform/matters/{matter_id}/tasks",
        "/platform/tasks/{task_id}",
        "/platform/matters/{matter_id}/audit",
        "/platform/matters/{matter_id}/agent-review",
        "/platform/matters/{matter_id}/quality-report",
        "/platform/matters/{matter_id}/reports",
    }
    assert expected.issubset(set(paths))

def test_professional_platform_methods_registered():
    paths = app.openapi()["paths"]
    assert {"post", "get"}.issubset(set(paths["/platform/matters"]))
    assert {"get", "patch"}.issubset(set(paths["/platform/matters/{matter_id}"]))
    assert "post" in paths["/platform/matters/{matter_id}/tasks"]
    assert "patch" in paths["/platform/tasks/{task_id}"]
    assert "get" in paths["/platform/matters/{matter_id}/audit"]
    assert "post" in paths["/platform/matters/{matter_id}/agent-review"]
    assert "post" in paths["/platform/matters/{matter_id}/quality-report"]
    assert "get" in paths["/platform/matters/{matter_id}/reports"]
