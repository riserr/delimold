"""Exercise atomic SALAK snapshot publication with concurrent readers."""
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.adapters.salak_publisher import JsonSnapshotPublisher, JsonSnapshotReader


class SnapshotConcurrencyTests(unittest.TestCase):
    def test_readers_only_observe_complete_snapshots_during_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "published-python"
            path = destination / "catalog.json"
            publisher = JsonSnapshotPublisher()
            reader = JsonSnapshotReader()
            ready = threading.Barrier(6)
            writers_remaining = 2
            writer_guard = threading.Lock()
            observed = []
            observed_guard = threading.Lock()

            def snapshot(revision):
                return {
                    "revision": revision,
                    "collections": {
                        "molds": {
                            str(index): {"revision": revision, "value": "x" * 300}
                            for index in range(40)
                        }
                    },
                }

            publisher.publish(snapshot(0), destination)

            def write_series(writer_id):
                nonlocal writers_remaining
                ready.wait()
                for index in range(1, 16):
                    publisher.publish(snapshot(writer_id * 100 + index), destination)
                    time.sleep(0.002)
                with writer_guard:
                    writers_remaining -= 1

            def read_while_writing():
                ready.wait()
                count = 0
                while True:
                    with writer_guard:
                        writers_active = writers_remaining > 0
                    if count >= 10 and not writers_active:
                        break
                    payload = reader.read(path)
                    revision = payload["revision"]
                    records = payload["collections"]["molds"].values()
                    self.assertEqual(40, len(payload["collections"]["molds"]))
                    self.assertTrue(all(row["revision"] == revision for row in records))
                    with observed_guard:
                        observed.append(revision)
                    count += 1
                    time.sleep(0.001)

            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(write_series, writer_id) for writer_id in (1, 2)]
                futures.extend(executor.submit(read_while_writing) for _ in range(4))
                for future in futures:
                    future.result(timeout=15)

            self.assertGreaterEqual(len(observed), 40)
            self.assertTrue(all(revision >= 0 for revision in observed))


if __name__ == "__main__":
    unittest.main()
