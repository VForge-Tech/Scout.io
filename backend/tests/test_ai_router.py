from unittest.mock import MagicMock, patch

import pytest

from app.core.ai.router import AIRouter


@pytest.fixture
def mock_litellm():
    with patch("app.core.ai.router.litellm_completion") as mock:
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="This is a test response")
            )
        ]
        mock.return_value = mock_response
        yield mock


def test_generate_success(mock_litellm):
    router = AIRouter(behaviour="balanced")
    response = router.generate(
        messages=[{"role": "user", "content": "Hello"}]
    )
    assert response == "This is a test response"
    assert mock_litellm.called


def test_generate_with_temperature(mock_litellm):
    router = AIRouter(behaviour="balanced")
    router.generate(
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.5,
    )
    call_kwargs = mock_litellm.call_args[1]
    assert call_kwargs["temperature"] == 0.5


def test_generate_with_max_tokens(mock_litellm):
    router = AIRouter(behaviour="balanced")
    router.generate(
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=500,
    )
    call_kwargs = mock_litellm.call_args[1]
    assert call_kwargs["max_tokens"] == 500


def test_fallback_on_failure():
    with patch("app.core.ai.router.litellm_completion") as mock:
        mock.side_effect = [
            Exception("Primary model failed"),
            MagicMock(
                choices=[
                    MagicMock(message=MagicMock(content="Fallback response"))
                ]
            ),
        ]
        router = AIRouter(behaviour="balanced")
        response = router.generate(
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert response == "Fallback response"


def test_all_models_fail():
    with patch("app.core.ai.router.litellm_completion") as mock:
        mock.side_effect = Exception("All models failed")
        router = AIRouter(behaviour="balanced")
        response = router.generate(
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert "having trouble" in response.lower()


def test_different_behaviours():
    router = AIRouter(behaviour="fast")
    assert router.primary_model is not None

    router = AIRouter(behaviour="accurate")
    assert router.primary_model is not None


def test_count_tokens(mock_litellm):
    mock_litellm.side_effect = Exception("token counting not supported")
    router = AIRouter(behaviour="balanced")
    count = router.count_tokens("Hello world")
    assert count > 0
