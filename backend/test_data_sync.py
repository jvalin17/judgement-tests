"""Tests for data_sync module — upload counter, consent filtering, merge dedup."""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from backend.app.ml.learning.data_sync import (
    increment_upload_counter,
    reset_upload_counter,
    UPLOAD_THRESHOLD,
    _download_and_merge_asset,
    upload_server_data,
    _github_headers,
)
from backend.app.ml.data_store import JsonlFileStore


# --- Upload counter ---


class TestUploadCounter:
    def setup_method(self):
        reset_upload_counter()

    def test_increment_below_threshold(self):
        result = increment_upload_counter(1)
        assert result is False

    def test_increment_reaches_threshold(self):
        result = increment_upload_counter(UPLOAD_THRESHOLD)
        assert result is True

    def test_increment_exceeds_threshold(self):
        result = increment_upload_counter(UPLOAD_THRESHOLD + 10)
        assert result is True

    def test_incremental_accumulation(self):
        for _ in range(UPLOAD_THRESHOLD - 1):
            result = increment_upload_counter(1)
            assert result is False
        result = increment_upload_counter(1)
        assert result is True

    def test_reset_clears_counter(self):
        increment_upload_counter(UPLOAD_THRESHOLD)
        reset_upload_counter()
        result = increment_upload_counter(1)
        assert result is False


# --- GitHub headers ---


class TestGithubHeaders:
    def test_headers_without_token(self):
        headers = _github_headers()
        assert "Authorization" not in headers
        assert headers["User-Agent"] == "Judgement-App"
        assert "application/vnd.github" in headers["Accept"]

    def test_headers_with_token(self):
        headers = _github_headers("ghp_test123")
        assert headers["Authorization"] == "token ghp_test123"


# --- Merge deduplication ---


class TestDownloadAndMerge:
    def test_merge_deduplicates(self, tmp_path):
        """Existing examples should not be duplicated when merging."""
        target = str(tmp_path / "data.jsonl")
        existing = {"features": [1.0, 2.0], "label": 3.0}
        with open(target, "w") as fh:
            fh.write(json.dumps(existing) + "\n")

        # Simulate downloaded content with one dup and one new
        download_content = (
            json.dumps({"features": [1.0, 2.0], "label": 3.0}) + "\n"  # duplicate
            + json.dumps({"features": [4.0, 5.0], "label": 6.0}) + "\n"  # new
        )

        mock_response = MagicMock()
        mock_response.read.return_value = download_content.encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        asset = {
            "name": "bid_decisions.jsonl",
            "browser_download_url": "https://example.com/data.jsonl",
        }

        with patch("backend.app.ml.learning.data_sync.urllib.request.urlopen", return_value=mock_response):
            new_count = _download_and_merge_asset(asset, target)

        assert new_count == 1  # Only the new example added

        with open(target, "r") as fh:
            lines = [line.strip() for line in fh if line.strip()]
        assert len(lines) == 2

    def test_merge_into_empty_file(self, tmp_path):
        """Merging into a non-existent file creates it with all examples."""
        target = str(tmp_path / "new_data.jsonl")
        download_content = (
            json.dumps({"features": [1.0], "label": 1.0}) + "\n"
            + json.dumps({"features": [2.0], "label": 2.0}) + "\n"
        )

        mock_response = MagicMock()
        mock_response.read.return_value = download_content.encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        asset = {
            "name": "bid_decisions.jsonl",
            "browser_download_url": "https://example.com/data.jsonl",
        }

        with patch("backend.app.ml.learning.data_sync.urllib.request.urlopen", return_value=mock_response):
            new_count = _download_and_merge_asset(asset, target)

        assert new_count == 2

    def test_merge_skips_malformed_lines(self, tmp_path):
        target = str(tmp_path / "data.jsonl")
        download_content = (
            json.dumps({"features": [1.0], "label": 1.0}) + "\n"
            + "not valid json\n"
            + json.dumps({"features": [2.0], "label": 2.0}) + "\n"
        )

        mock_response = MagicMock()
        mock_response.read.return_value = download_content.encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        asset = {
            "name": "bid_decisions.jsonl",
            "browser_download_url": "https://example.com/data.jsonl",
        }

        with patch("backend.app.ml.learning.data_sync.urllib.request.urlopen", return_value=mock_response):
            new_count = _download_and_merge_asset(asset, target)

        assert new_count == 2  # Only valid lines counted


# --- Consent filtering ---


class TestConsentFiltering:
    def test_upload_filters_non_consented(self):
        """upload_server_data with consent_only=True should skip non-consented examples."""
        store = JsonlFileStore()
        consented = {"features": [1.0], "label": 1.0, "share_consent": True, "strategy_type": "human"}
        not_consented = {"features": [2.0], "label": 2.0, "share_consent": False, "strategy_type": "human"}
        no_field = {"features": [3.0], "label": 3.0, "strategy_type": "easy"}

        with patch("backend.app.ml.learning.data_sync.get_default_store", return_value=store):
            with patch.object(store, "load_examples") as mock_load:
                mock_load.return_value = [consented, not_consented, no_field]
                with patch("backend.app.ml.learning.data_sync._get_github_token", return_value="ghp_test"):
                    with patch("backend.app.ml.learning.data_sync._ensure_release", return_value=12345):
                        with patch("backend.app.ml.learning.data_sync._upload_asset") as mock_upload:
                            result = upload_server_data(consent_only=True)

        assert result is True
        # Should have been called once for bid file (1 consented example)
        assert mock_upload.called
        uploaded_content = mock_upload.call_args_list[0][0][3].decode("utf-8")
        uploaded_entries = [json.loads(line) for line in uploaded_content.strip().split("\n")]
        assert len(uploaded_entries) == 1
        assert uploaded_entries[0]["share_consent"] is True

    def test_upload_without_token_returns_false(self):
        with patch("backend.app.ml.learning.data_sync._get_github_token", return_value=None):
            result = upload_server_data()
        assert result is False
