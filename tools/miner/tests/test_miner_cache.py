import json
import sys
import tempfile
import unittest
from pathlib import Path


MINER_ROOT = Path(__file__).resolve().parents[1]
SRC = MINER_ROOT / "src"
EXTRACTOR = SRC / "extractor"
NEOXTRACTOR = SRC / "neoxtractor"
sys.path[:0] = [str(SRC), str(EXTRACTOR), str(NEOXTRACTOR)]

from miner_core import BASE_REQUIRED, CURRENT_REQUIRED, cache_is_complete


class MinerCacheTests(unittest.TestCase):
    def _cache(self, root: Path, layer: str, names) -> tuple[Path, Path]:
        raw = root / "raw"
        mined = root / "tables"
        (mined / "translate").mkdir(parents=True)
        raw.mkdir(parents=True)
        (raw / ".dead-signal-complete.json").write_text(json.dumps({"archive_sha256": "abc", "mode": "full"}), encoding="utf-8")
        (mined / "snapshot.json").write_text("{}", encoding="utf-8")
        # A non-empty snapshot is required by the production cache contract.
        (mined / "snapshot.json").write_text('{"layer":"%s"}' % layer, encoding="utf-8")
        (mined / "translate" / "translate_data_en.json").write_text("{}", encoding="utf-8")
        data = mined / "game_common" / "data"
        data.mkdir(parents=True)
        for name in names:
            (data / f"{name}.json").write_text("{}", encoding="utf-8")
        return raw, mined

    def test_complete_current_cache_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw, mined = self._cache(Path(directory), "current", CURRENT_REQUIRED)
            self.assertTrue(cache_is_complete(raw, mined, "abc", "full", "current"))

    def test_stale_current_cache_missing_required_table_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw, mined = self._cache(Path(directory), "current", CURRENT_REQUIRED[:-1])
            self.assertFalse(cache_is_complete(raw, mined, "abc", "full", "current"))

    def test_base_cache_uses_base_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw, mined = self._cache(Path(directory), "base", BASE_REQUIRED)
            self.assertTrue(cache_is_complete(raw, mined, "abc", "full", "base"))


if __name__ == "__main__":
    unittest.main()
