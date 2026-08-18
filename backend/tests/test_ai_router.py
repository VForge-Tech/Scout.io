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


def _stream_chunk(text: str):
    return MagicMock(choices=[MagicMock(delta=MagicMock(content=text))])


def test_generate_stream_yields_tokens():
    with patch("app.core.ai.router.litellm_completion") as mock:
        mock.return_value = iter([_stream_chunk("Hello"), _stream_chunk(" world")])
        router = AIRouter(behaviour="balanced")
        out = list(router.generate_stream([{"role": "user", "content": "Hi"}]))
        assert out == ["Hello", " world"]
        assert router.last_stream_error is False
        assert router.last_usage and router.last_usage["total_tokens"] is not None


def test_generate_stream_mock_mode():
    from app.core.config import get_settings

    settings = get_settings()
    orig = settings.mock_llm
    settings.mock_llm = True
    try:
        with patch("app.core.ai.router.litellm_completion") as mock:
            router = AIRouter(behaviour="balanced")
            out = list(router.generate_stream([{"role": "user", "content": "hi"}]))
            assert len(out) == 1
            assert "[mock]" in out[0]
            mock.assert_not_called()
    finally:
        settings.mock_llm = orig


def test_generate_stream_start_failure_falls_back():
    with patch("app.core.ai.router.litellm_completion") as mock:
        mock.side_effect = [
            Exception("start fail"),
            iter([_stream_chunk("Fallback"), _stream_chunk("!")]),
        ]
        router = AIRouter(behaviour="balanced")
        out = list(router.generate_stream([{"role": "user", "content": "Hi"}]))
        assert out == ["Fallback", "!"]
        assert router.last_stream_error is False
        assert router.last_usage and router.last_usage["model"] is not None


def test_generate_stream_mid_stream_failure_stops_and_marks_error():
    def broken():
        yield _stream_chunk("Partial")
        raise Exception("mid-stream boom")

    with patch("app.core.ai.router.litellm_completion") as mock:
        mock.return_value = broken()
        router = AIRouter(behaviour="balanced")
        out = list(router.generate_stream([{"role": "user", "content": "Hi"}]))
        # Only the already-emitted token is returned; no fallback retry.
        assert out == ["Partial"]
        assert router.last_stream_error is True


def test_generate_stream_all_fail_graceful():
    with patch("app.core.ai.router.litellm_completion") as mock:
        mock.side_effect = Exception("all failed")
        router = AIRouter(behaviour="balanced")
        out = list(router.generate_stream([{"role": "user", "content": "Hi"}]))
        assert "trouble" in "".join(out).lower()
