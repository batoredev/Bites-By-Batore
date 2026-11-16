"""Optional Ollama cloud models: routing, local fallback and where the key may go."""

import json

import httpx
import pytest

from app import local_models
from app.config import settings
from app.providers import Unavailable

ANSWER = json.dumps(
    {"summary": "s", "languages": ["en"], "observations": [], "venue_candidates": [], "unknowns": []}
)


class Recorder:
    """Stands in for the HTTP client; answers by host."""

    def __init__(self, cloud_status=200, cloud_body=None):
        self.calls, self.cloud_status, self.cloud_body = [], cloud_status, cloud_body

    def post(self, url, json=None, headers=None, **kwargs):
        self.calls.append({"url": url, "model": json["model"], "headers": headers or {}})
        request = httpx.Request("POST", url)
        if url.startswith("https://ollama.com"):
            body = self.cloud_body or {"message": {"content": ANSWER}, "done_reason": "stop"}
            return httpx.Response(self.cloud_status, json=body, request=request)
        return httpx.Response(
            200, json={"message": {"content": ANSWER}, "done_reason": "stop"}, request=request
        )


@pytest.fixture
def cloud(monkeypatch):
    cfg = settings()
    for key, value in {
        "ollama_api_key": "test-key",
        "ollama_cloud_url": "https://ollama.com",
        "ollama_cloud_text_model": "big-text",
        "ollama_cloud_vision_model": "",
        "ollama_text_model": "",
        "ollama_model": "small-local",
    }.items():
        monkeypatch.setattr(cfg, key, value)
    monkeypatch.setattr("app.local_tokenizer.input_tokens", lambda *args: 50)
    recorder = Recorder()
    monkeypatch.setattr(local_models, "inference_client", lambda: recorder)
    return recorder


def run(model):
    token = local_models.ACTIVE_MODEL.set(model)
    used = []
    local_models.USED_MODELS.set(used)
    try:
        return local_models.local_chat("prompt", {"caption": "Zircon Cafe, Coimbatore"}, {}), used
    finally:
        local_models.ACTIVE_MODEL.reset(token)


def test_roles_route_to_cloud_only_when_configured(cloud, monkeypatch):
    assert local_models.model_for("caption") == "cloud/big-text"
    assert local_models.model_for("comments") == "cloud/big-text"
    assert local_models.model_for("video") == "small-local"
    monkeypatch.setattr(settings(), "ollama_cloud_vision_model", "big-vision")
    assert local_models.model_for("video") == "cloud/big-vision"
    monkeypatch.setattr(settings(), "ollama_api_key", "")
    assert local_models.model_for("caption") == "small-local"


def test_cloud_answer_is_used_and_recorded(cloud):
    answer, used = run("cloud/big-text")
    assert answer == ANSWER and used == ["cloud/big-text"]
    assert [c["url"] for c in cloud.calls] == ["https://ollama.com/api/chat"]
    assert cloud.calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert cloud.calls[0]["model"] == "big-text"


@pytest.mark.parametrize(
    "status,body",
    [
        (402, {"error": "Add usage credits"}),
        (429, {"error": "rate limited"}),
        (503, {"error": "unavailable"}),
        (200, {"message": {"content": "not json"}, "done_reason": "stop"}),
        (200, {"message": {"content": ANSWER}, "done_reason": "length"}),
    ],
)
def test_any_cloud_failure_falls_back_to_the_local_model(cloud, status, body):
    cloud.cloud_status, cloud.cloud_body = status, body
    answer, used = run("cloud/big-text")
    assert answer == ANSWER and used == ["small-local"]
    assert [c["model"] for c in cloud.calls] == ["big-text", "small-local"]
    assert "Authorization" not in cloud.calls[1]["headers"]
    assert cloud.calls[1]["url"].startswith("http://127.0.0.1")


@pytest.mark.parametrize(
    "url",
    ["http://ollama.com", "https://ollama.com.evil.example", "https://evil.example", "https://ollama.com/x"],
)
def test_key_is_never_sent_anywhere_but_ollama(cloud, monkeypatch, url):
    monkeypatch.setattr(settings(), "ollama_cloud_url", url)
    with pytest.raises(Unavailable):
        local_models.cloud_endpoint()
    answer, used = run("cloud/big-text")
    # The misconfigured cloud call never leaves; the local model answers instead.
    assert used == ["small-local"]
    assert all("Authorization" not in c["headers"] for c in cloud.calls)


def test_local_model_names_cannot_smuggle_cloud_models(cloud, monkeypatch):
    monkeypatch.setattr(settings(), "ollama_model", "gpt-oss:120b-cloud")
    with pytest.raises(Unavailable):
        local_models.endpoint()
