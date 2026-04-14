from pathlib import Path
import sys

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.main import app

def test_backend_architecture_guide_exists_with_required_sections() -> None:
    guide_path = REPO_ROOT / "docs" / "backend-architecture-guide.md"
    assert guide_path.exists(), "Expected docs/backend-architecture-guide.md to exist."

    content = guide_path.read_text(encoding="utf-8")
    required_markers = [
        "# Backend Architecture Guide",
        "## System Overview",
        "## Core Techniques Used",
        "## Request Lifecycle",
        "`POST /api/chat`",
        "```mermaid",
    ]
    for marker in required_markers:
        assert marker in content, f"Missing required marker: {marker}"


def test_backend_api_guide_exists_with_required_sections() -> None:
    guide_path = REPO_ROOT / "docs" / "backend-api-guide.md"
    assert guide_path.exists(), "Expected docs/backend-api-guide.md to exist."

    content = guide_path.read_text(encoding="utf-8")
    required_markers = [
        "# Backend API Guide",
        "## Authentication",
        "## Session Continuity",
        "## Endpoints",
        "## Error Handling Matrix",
    ]
    for marker in required_markers:
        assert marker in content, f"Missing required marker: {marker}"


def test_openapi_has_professional_top_level_metadata() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    info = payload.get("info", {})

    title = info.get("title", "")
    summary = info.get("summary", "")
    description = info.get("description", "")
    contact = info.get("contact", {})
    license_info = info.get("license", {})

    assert "Wasla" in title and "API" in title
    assert len(summary.strip()) >= 40
    assert "Customer Portal" in description
    assert "Company CRM" in description
    assert "session_id" in description
    assert "tool_calls_made" in description
    assert contact.get("name"), "OpenAPI info.contact.name should be present."
    assert contact.get("url"), "OpenAPI info.contact.url should be present."
    assert license_info.get("name"), "OpenAPI info.license.name should be present."


def test_chat_routes_have_descriptive_docs() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    paths = payload.get("paths", {})

    chat_post = paths["/api/chat"]["post"]
    company_post = paths["/api/company/chat"]["post"]

    assert "summary" in chat_post and len(chat_post["summary"].strip()) >= 15
    assert "description" in chat_post and len(chat_post["description"].strip()) >= 80
    assert "responses" in chat_post and "503" in chat_post["responses"]
    assert "service unavailable" in chat_post["responses"]["503"]["description"].lower()

    assert "summary" in company_post and len(company_post["summary"].strip()) >= 15
    assert "description" in company_post and len(company_post["description"].strip()) >= 80
    assert "responses" in company_post and "503" in company_post["responses"]
    assert "service unavailable" in company_post["responses"]["503"]["description"].lower()


def test_docs_use_consistent_session_terminology() -> None:
    backend_api_guide = (REPO_ROOT / "docs" / "backend-api-guide.md").read_text(encoding="utf-8")
    backend_architecture_guide = (REPO_ROOT / "docs" / "backend-architecture-guide.md").read_text(
        encoding="utf-8"
    )

    for expected_term in ("session_id", "tool_calls_made"):
        assert expected_term in backend_api_guide
        assert expected_term in backend_architecture_guide

    # Keep model naming aligned across docs when available.
    assert "model_used" in backend_api_guide
    assert "model_used" in backend_architecture_guide
