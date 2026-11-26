from app.main import app

def test_legal_drafting_routes_registered():
    paths = app.openapi()["paths"]
    expected = {
        "/drafting/drafts",
        "/drafting/drafts/{draft_id}",
    }
    assert expected.issubset(set(paths))

def test_legal_drafting_methods_registered():
    paths = app.openapi()["paths"]
    assert "post" in paths["/drafting/drafts"]
    assert "get" in paths["/drafting/drafts"]
    assert "get" in paths["/drafting/drafts/{draft_id}"]
    assert "patch" in paths["/drafting/drafts/{draft_id}"]
