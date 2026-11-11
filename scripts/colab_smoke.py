"""Generate the upstream example on a real GPU and print a measurement table.

Run on a Colab L4 runtime after notebook cell 1:

    cd /content/yue2-colab-studio
    PYTHONPATH=src python scripts/colab_smoke.py --repeat 5

Paste the table into docs/colab-baseline.md.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from yue2_studio.engine import Engine, EngineError
from yue2_studio.request_rules import validate
from yue2_studio.ui_text import EXAMPLE_LYRICS, EXAMPLE_STYLE

# seed from upstream examples/song.json
EXAMPLE_SEED = 831001


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--output", default="/content/yue2_studio_data/_smoke")
    parser.add_argument("--cot", default="full", choices=["full", "melody", "off"])
    args = parser.parse_args()

    engine = Engine()
    start = time.perf_counter()
    try:
        engine.load()
    except EngineError as error:
        print(f"load failed: {error}", file=sys.stderr)
        return 1
    print(f"load_seconds (includes any download): {time.perf_counter() - start:.1f}")

    header = (
        "| run | plan s | semantic s | nar s | vae s | total s | audio s | peak GiB | truncated |"
    )
    print(header)
    print("|" + "---|" * 9)
    failures = 0
    for index in range(1, args.repeat + 1):
        request = validate(
            {
                "style": EXAMPLE_STYLE,
                "lyrics": EXAMPLE_LYRICS,
                "cot": args.cot,
                "seed": EXAMPLE_SEED + index - 1,
            }
        )
        stages = []
        try:
            outcome = engine.render(
                request,
                abc=None,
                cancelled=lambda: False,
                on_stage=lambda event, seen=stages: (
                    seen.append(event.stage) if event.stage not in seen else None
                ),
            )
        except EngineError as error:
            failures += 1
            print(f"| {index} | FAILED {error.code} {error.detail[:80]} |")
            continue
        result = outcome.result
        target = Path(args.output) / f"run-{index}"
        result.save_artifacts(target)
        timing = result.timing
        audio_seconds = len(result.audio) / result.sample_rate
        print(
            f"| {index} "
            f"| {timing['abc'].get('seconds', 0):.1f} "
            f"| {timing['semantic'].get('seconds', 0):.1f} "
            f"| {timing['nar_seconds']:.1f} "
            f"| {timing['vae_seconds']:.1f} "
            f"| {timing['e2e_seconds']:.1f} "
            f"| {audio_seconds:.1f} "
            f"| {outcome.peak_vram_gib:.2f} "
            f"| {result.truncated} |"
        )
        print(f"  stages seen: {' > '.join(stages)}; artifacts: {target}")
    engine.close()
    print(f"{args.repeat - failures}/{args.repeat} runs succeeded")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
