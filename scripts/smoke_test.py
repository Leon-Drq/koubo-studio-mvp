import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    client = TestClient(app)
    health = client.get("/api/health")
    assert health.status_code == 200, health.text
    page = client.get("/")
    assert page.status_code == 200, page.text[:200]
    assert "口播视频智能体" in page.text
    print("smoke ok")


if __name__ == "__main__":
    Path("data").mkdir(exist_ok=True)
    main()
