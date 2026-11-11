"""Start the studio server.

On Colab this runs as a child process of notebook cell 3. For a local look at
the interface without a GPU:

    python -m yue2_studio.launch --stand-in --workdir .studio-data
"""

from __future__ import annotations

import argparse
import os
from importlib import metadata
from pathlib import Path

from . import MODEL_REVISION, VAE_REVISION, YUE2_COMMIT, __version__, notebook_steps
from .draft_store import DraftStore
from .engine import Engine
from .event_log import EventLog
from .generation_job import JobRunner
from .song_store import SongStore
from .studio import Studio

LOGIN_USER = "studio"


def _installed(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "未安裝"


def build_studio(workdir: Path, *, stand_in: bool, persistent: bool) -> Studio:
    environment_info = notebook_steps.read_env_marker()
    versions = {
        "yue2-colab-studio": __version__,
        "yue2 commit": YUE2_COMMIT[:7],
        "YuE2-3B revision": MODEL_REVISION[:7],
        "YuE2-Vae revision": VAE_REVISION[:7],
        "torch": _installed("torch"),
        "gradio": _installed("gradio"),
    }
    if stand_in:
        from .stand_in_pipeline import StandInPipeline

        versions["engine"] = "stand-in（不是真的 YuE2）"
        engine = Engine(lambda cache_dir: StandInPipeline(step_delay=0.4, audio_seconds=6.0))
    else:
        engine = Engine()

    log = EventLog(workdir / "logs" / "app.log")
    store = SongStore(workdir)
    runner = JobRunner(engine, store, log, versions=versions)
    log.write(
        "app_started",
        gpu=environment_info.get("report", {}).get("gpu_name"),
        persistent=persistent,
        stand_in=stand_in,
        version=__version__,
    )
    return Studio(
        engine,
        store,
        DraftStore(workdir),
        runner,
        log,
        environment_info=environment_info,
        persistent=persistent,
    )


def login_for(share: bool, passcode: str | None, no_passcode: bool) -> tuple[str, str] | None:
    """Gradio auth for this launch.

    A public link without a passcode lets anyone holding it spend the owner's
    compute units and write to their storage, so it has to be an explicit
    choice: cell 2 passes --no-passcode when USE_PASSCODE is off.
    """
    if passcode:
        return (LOGIN_USER, passcode)
    if share and not no_passcode:
        raise SystemExit("--share needs YUE2_STUDIO_PASSCODE or --no-passcode")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--share", action="store_true", help="open a public gradio.live link")
    parser.add_argument("--persistent", action="store_true", help="workdir survives the runtime")
    parser.add_argument("--stand-in", action="store_true", help="use the GPU-free stand-in engine")
    parser.add_argument(
        "--no-passcode", action="store_true", help="allow --share without a login screen"
    )
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    workdir = Path(args.workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    from .app import build_app
    from .theme import CSS, FORCE_LIGHT_HEAD, build_theme

    studio = build_studio(workdir, stand_in=args.stand_in, persistent=args.persistent)
    auth = login_for(args.share, os.environ.get("YUE2_STUDIO_PASSCODE"), args.no_passcode)

    demo = build_app(studio)
    demo.queue(default_concurrency_limit=8)
    demo.launch(
        share=args.share,
        auth=auth,
        server_port=args.port,
        allowed_paths=[str(workdir)],
        theme=build_theme(),
        css=CSS,
        head=FORCE_LIGHT_HEAD,
        footer_links=[],
        show_error=True,
    )


if __name__ == "__main__":
    main()
