"""Export bindict payloads stored as marshalled PYC byte constants.

Some localization modules store their binary dictionary as a Python bytes
constant instead of the tagged layout handled by the ordinary scanner. This
loads only the marshalled code object and never executes its bytecode.
"""

from __future__ import annotations

import argparse
import json
import marshal
import sys
import types
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pyc", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--neoxtractor", type=Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.neoxtractor.resolve()))
    from core.bindict.parser import BindictParser

    pyc_bytes = args.pyc.read_bytes()
    code = marshal.loads(pyc_bytes[16:])
    if not isinstance(code, types.CodeType):
        raise ValueError("PYC payload did not contain a Python code object")

    bindict_parser = BindictParser()
    exports = {}
    for index, value in enumerate(code.co_consts):
        if not isinstance(value, bytes):
            continue
        parsed = bindict_parser._parse_dictionary_data(value)
        if parsed:
            exports[f"constant_{index}"] = parsed

    if not exports:
        raise ValueError("No bindict byte constants were found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(exports, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "source": str(args.pyc.resolve()),
                "exported_constants": len(exports),
                "top_level_entries": {
                    name: len(value) if hasattr(value, "__len__") else None
                    for name, value in exports.items()
                },
                "output": str(args.output.resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
