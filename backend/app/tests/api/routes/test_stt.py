from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings


def test_stt_transcribe_mocked(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    mock_response = {
        "text": "Exame de tórax sem alterações agudas.",
        "language": "pt",
        "duration": 1.23,
        "segments": [
            {
                "start": 0.0,
                "end": 1.2,
                "text": "Exame de tórax sem alterações agudas.",
                "words": [
                    {"start": 0.0, "end": 0.2, "word": "Exame"},
                ],
            }
        ],
    }

    with patch("app.services.stt.transcribe_bytes", return_value=mock_response):
        files = {"file": ("audio.wav", b"FAKEAUDIO", "audio/wav")}
        r = client.post(
            f"{settings.API_V1_STR}/stt/transcribe",
            files=files,
            headers=normal_user_token_headers,
            params={"language": "pt", "word_timestamps": True},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["text"].startswith("Exame de tórax")
    assert data["language"] == "pt"
    assert "segments" in data


