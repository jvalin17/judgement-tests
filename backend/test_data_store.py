"""Tests for CachedJsonlStore — caching, thread safety, invalidation."""

import json
import os
import tempfile
import threading

import pytest

from backend.app.ml.data_store import JsonlFileStore


@pytest.fixture
def store():
    return JsonlFileStore()


@pytest.fixture
def data_file(tmp_path):
    return str(tmp_path / "test_examples.jsonl")


def _write_examples(filepath, examples):
    """Write examples directly to disk, bypassing the store."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as fh:
        for ex in examples:
            fh.write(json.dumps(ex) + "\n")


# --- load_examples ---


class TestLoadExamples:
    def test_load_from_empty_file(self, store, data_file):
        _write_examples(data_file, [])
        result = store.load_examples(data_file)
        assert result == []

    def test_load_missing_file_returns_empty(self, store, tmp_path):
        missing = str(tmp_path / "nonexistent.jsonl")
        result = store.load_examples(missing)
        assert result == []

    def test_load_returns_all_examples(self, store, data_file):
        examples = [
            {"features": [1.0, 2.0, 3.0], "label": 2.0, "strategy_type": "human"},
            {"features": [4.0, 5.0, 6.0], "label": 0.0, "strategy_type": "easy"},
        ]
        _write_examples(data_file, examples)
        result = store.load_examples(data_file)
        assert len(result) == 2
        assert result[0]["features"] == [1.0, 2.0, 3.0]
        assert result[1]["label"] == 0.0

    def test_load_skips_malformed_json(self, store, data_file):
        with open(data_file, "w") as fh:
            fh.write('{"features": [1.0], "label": 1.0}\n')
            fh.write("this is not json\n")
            fh.write('{"features": [2.0], "label": 2.0}\n')
        result = store.load_examples(data_file)
        assert len(result) == 2

    def test_load_skips_blank_lines(self, store, data_file):
        with open(data_file, "w") as fh:
            fh.write('{"features": [1.0], "label": 1.0}\n')
            fh.write("\n")
            fh.write("   \n")
            fh.write('{"features": [2.0], "label": 2.0}\n')
        result = store.load_examples(data_file)
        assert len(result) == 2


# --- Caching ---


class TestCaching:
    def test_second_load_returns_cache(self, store, data_file):
        _write_examples(data_file, [{"features": [1.0], "label": 1.0}])
        first = store.load_examples(data_file)
        # Modify the file behind the store's back
        _write_examples(data_file, [{"features": [9.0], "label": 9.0}])
        second = store.load_examples(data_file)
        # Should still see original data (cached)
        assert second[0]["features"] == [1.0]
        assert first == second

    def test_cache_returns_copy_not_reference(self, store, data_file):
        _write_examples(data_file, [{"features": [1.0], "label": 1.0}])
        first = store.load_examples(data_file)
        first.append({"features": [99.0], "label": 99.0})
        second = store.load_examples(data_file)
        assert len(second) == 1  # Mutation did not affect cache

    def test_invalidate_specific_file(self, store, data_file):
        _write_examples(data_file, [{"features": [1.0], "label": 1.0}])
        store.load_examples(data_file)  # Populate cache
        _write_examples(data_file, [{"features": [9.0], "label": 9.0}])
        store.invalidate_cache(data_file)
        result = store.load_examples(data_file)
        assert result[0]["features"] == [9.0]

    def test_invalidate_all(self, store, tmp_path):
        file_a = str(tmp_path / "a.jsonl")
        file_b = str(tmp_path / "b.jsonl")
        _write_examples(file_a, [{"features": [1.0], "label": 1.0}])
        _write_examples(file_b, [{"features": [2.0], "label": 2.0}])
        store.load_examples(file_a)
        store.load_examples(file_b)
        # Replace both files
        _write_examples(file_a, [{"features": [10.0], "label": 10.0}])
        _write_examples(file_b, [{"features": [20.0], "label": 20.0}])
        store.invalidate_cache()  # Clear all
        assert store.load_examples(file_a)[0]["features"] == [10.0]
        assert store.load_examples(file_b)[0]["features"] == [20.0]

    def test_invalidate_nonexistent_key_is_safe(self, store):
        store.invalidate_cache("does_not_exist.jsonl")  # Should not raise


# --- append_example ---


class TestAppendExample:
    def test_append_creates_file(self, store, data_file):
        store.append_example(data_file, [1.0, 2.0], 3.0)
        result = store.load_examples(data_file)
        assert len(result) == 1
        assert result[0]["features"] == [1.0, 2.0]
        assert result[0]["label"] == 3.0

    def test_append_with_metadata(self, store, data_file):
        store.append_example(data_file, [1.0], 1.0, metadata={"strategy_type": "hard", "share_consent": True})
        result = store.load_examples(data_file)
        assert result[0]["strategy_type"] == "hard"
        assert result[0]["share_consent"] is True

    def test_append_updates_cache(self, store, data_file):
        store.append_example(data_file, [1.0], 1.0)
        store.load_examples(data_file)  # Populate cache
        store.append_example(data_file, [2.0], 2.0)
        result = store.load_examples(data_file)
        assert len(result) == 2  # Cache was updated, not stale

    def test_append_persists_to_disk(self, store, data_file):
        store.append_example(data_file, [1.0], 1.0)
        # Read directly from disk, bypassing cache
        with open(data_file, "r") as fh:
            lines = [line.strip() for line in fh if line.strip()]
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["features"] == [1.0]

    def test_append_creates_nested_directories(self, store, tmp_path):
        deep_file = str(tmp_path / "deep" / "nested" / "data.jsonl")
        store.append_example(deep_file, [1.0], 1.0)
        assert os.path.exists(deep_file)


# --- example_count ---


class TestExampleCount:
    def test_count_empty_file(self, store, data_file):
        _write_examples(data_file, [])
        assert store.example_count(data_file) == 0

    def test_count_missing_file(self, store, tmp_path):
        assert store.example_count(str(tmp_path / "nope.jsonl")) == 0

    def test_count_matches_load(self, store, data_file):
        examples = [{"features": [float(i)], "label": float(i)} for i in range(7)]
        _write_examples(data_file, examples)
        assert store.example_count(data_file) == 7
        assert len(store.load_examples(data_file)) == 7

    def test_count_uses_cache_when_available(self, store, data_file):
        _write_examples(data_file, [{"features": [1.0], "label": 1.0}])
        store.load_examples(data_file)  # Populate cache
        store.append_example(data_file, [2.0], 2.0)  # Updates cache
        assert store.example_count(data_file) == 2


# --- Thread safety ---


class TestThreadSafety:
    def test_concurrent_appends(self, store, data_file):
        """Multiple threads appending simultaneously should not corrupt data."""
        num_threads = 10
        appends_per_thread = 20
        errors = []

        def append_worker(thread_index):
            try:
                for iteration in range(appends_per_thread):
                    store.append_example(
                        data_file,
                        [float(thread_index), float(iteration)],
                        float(thread_index * 100 + iteration),
                    )
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=append_worker, args=(i,)) for i in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == [], f"Thread errors: {errors}"
        result = store.load_examples(data_file)
        assert len(result) == num_threads * appends_per_thread
