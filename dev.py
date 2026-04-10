from __future__ import annotations

import argparse
from pathlib import Path

from src.devtools.scaffold import scaffold_adapter, scaffold_skill


def main() -> int:
    parser = argparse.ArgumentParser(description="Developer helpers for Whisper Learning Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    skill_parser = subparsers.add_parser("create-skill")
    skill_parser.add_argument("skill_name")
    skill_parser.add_argument("--description", default="New project skill")
    skill_parser.add_argument("--mode", default="free")

    adapter_parser = subparsers.add_parser("create-adapter")
    adapter_parser.add_argument("adapter_name")
    adapter_parser.add_argument("--port-kind", default="custom")

    args = parser.parse_args()
    root = Path(__file__).parent

    if args.command == "create-skill":
        files = scaffold_skill(root, args.skill_name, args.description, args.mode)
        for path in files:
            print(path)
        return 0

    if args.command == "create-adapter":
        path = scaffold_adapter(root, args.adapter_name, args.port_kind)
        print(path)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
