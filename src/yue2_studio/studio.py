"""What each UI action does, independent of Gradio.

Every method returns a "patch": a dict of component name to the properties
that should change, for example ``{"tabs": {"selected": "score"}}``. app.py
turns patches into Gradio updates. Keeping this layer free of Gradio makes
the whole interaction model testable with plain asserts.

A patch may carry ``"_toast": (level, text)`` for a transient message.
"""

from __future__ import annotations

import html
from collections.abc import Iterator
from datetime import datetime

from . import request_rules, ui_text
from .draft_store import Draft, DraftStore
from .engine import Engine
from .generation_job import JobRunner, JobUpdate
from .song_store import (
    InvalidMetadata,
    InvalidSongId,
    SongNotFound,
    SongRecord,
    SongStore,
    StorageError,
)

Patch = dict
FORM_FIELDS = (
    "style",
    "lyrics",
    "cot",
    "seed",
    "cfg_auto",
    "cfg",
    "score_first",
    "abc_text",
    "abc_source",
)
DEFAULT_CFG = 1.0
COT_LABELS = {value: label.split("（")[0] for label, value in ui_text.COT_CHOICES}
# The MP3 download button in each place a song can be shown. It stays visible
# and is only enabled or disabled: in browser testing (2026-11-12) Gradio 6.17.3
# lost track of buttons that were shown and hidden repeatedly inside a Column
# that is itself shown and hidden, and then ignored further visibility updates.
MP3_BUTTONS = {"result": "download_mp3_btn", "library": "detail_mp3_btn"}


def as_form(*values) -> dict:
    return dict(zip(FORM_FIELDS, values, strict=True))


def _toast(level: str, text: str) -> Patch:
    return {"_toast": (level, text)}


def _duration(seconds: float) -> str:
    minutes, rest = divmod(int(round(seconds)), 60)
    return f"{minutes}:{rest:02d}"


def _created(stamp: str) -> str:
    try:
        return datetime.fromisoformat(stamp).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError):
        return ""


def render_status(update: JobUpdate) -> str:
    label = html.escape(ui_text.STAGE_LABELS.get(update.state, update.state))
    if not update.running:
        return f'<div class="studio-status"><span class="studio-stage">{label}</span></div>'

    if update.total:
        percent = max(0, min(100, round(100 * (update.completed or 0) / update.total)))
        bar = f'<div class="studio-bar"><div style="width:{percent}%"></div></div>'
    else:
        bar = '<div class="studio-bar studio-bar-busy"><div></div></div>'
    minutes, seconds = divmod(int(update.elapsed), 60)
    elapsed = ui_text.ELAPSED.format(minutes=minutes, seconds=seconds)
    notice = ""
    if update.notice:
        notice = f'<span class="studio-notice">{html.escape(update.notice)}</span>'
    return (
        '<div class="studio-status studio-running">'
        f'<span class="studio-dot"></span><span class="studio-stage">{label}</span>'
        f'{bar}<span class="studio-elapsed">{elapsed}</span>{notice}</div>'
    )


def render_error(update: JobUpdate) -> str:
    if update.state != "failed" or not update.error_code:
        return ""
    code = update.error_code
    message = ui_text.ERRORS.get(code, ui_text.ERRORS["E_UNKNOWN"])
    parts = [f"<strong>{html.escape(message)}</strong>"]
    if update.field_errors:
        items = "".join(
            f"<li>{html.escape(ui_text.FIELD_NAMES.get(error.field, error.field))}："
            f"{html.escape(error.message)}</li>"
            for error in update.field_errors
        )
        parts.append(f"<ul>{items}</ul>")
    if code in ui_text.ERROR_NEXT_STEP:
        parts.append(f"<p>{ui_text.ERROR_NEXT}：{html.escape(ui_text.ERROR_NEXT_STEP[code])}</p>")
    if update.rescue_path:
        parts.append(f"<p><code>{html.escape(update.rescue_path)}</code></p>")
    if update.error_detail and code != "E_VALIDATION":
        parts.append(f"<p class='studio-detail'>{html.escape(update.error_detail[:300])}</p>")
    parts.append(f"<p class='studio-code'>{ui_text.ERROR_CODE}：{code}</p>")
    return f'<div class="studio-error">{"".join(parts)}</div>'


class Studio:
    def __init__(
        self,
        engine: Engine,
        store: SongStore,
        drafts: DraftStore,
        runner: JobRunner,
        log,
        *,
        environment_info: dict | None = None,
        persistent: bool = False,
    ):
        self.engine = engine
        self.store = store
        self.drafts = drafts
        self.runner = runner
        self.log = log
        self.environment_info = environment_info or {}
        self.persistent = persistent

    # --- shared pieces ------------------------------------------------------------

    def _progress(self, update: JobUpdate) -> Patch:
        idle = not update.running
        return {
            "status_html": {"value": render_status(update)},
            "error_html": {"value": render_error(update), "visible": update.state == "failed"},
            "cancel_btn": {"visible": update.running},
            "primary_btn": {"interactive": idle},
            "render_btn": {"interactive": idle},
            "restart_btn": {"interactive": idle},
        }

    @staticmethod
    def _raw(form: dict) -> dict:
        return {
            "style": form["style"],
            "lyrics": form["lyrics"],
            "cot": form["cot"],
            "seed": form["seed"],
            "cfg_scale": None if form["cfg_auto"] else form["cfg"],
        }

    def _save_draft(self, form: dict) -> None:
        previous = self.drafts.load()
        seed = form["seed"]
        try:
            seed = None if seed in (None, "") else int(seed)
        except (TypeError, ValueError):
            seed = None
        draft = Draft(
            style=form["style"] or "",
            lyrics=form["lyrics"] or "",
            cot=form["cot"] or "full",
            seed=seed,
            cfg_scale=None if form["cfg_auto"] else form["cfg"],
            score_first=bool(form["score_first"]),
            abc_text=form["abc_text"] or "",
            abc_source=form["abc_source"] if form["abc_text"] else "none",
            parent_song_id=previous.parent_song_id,
        )
        try:
            self.drafts.save(draft)
        except OSError:
            # Losing an autosave is not worth interrupting the user for.
            pass

    @staticmethod
    def _form_hints(form: dict) -> Patch:
        planning = form["cot"] != "off"
        score_first = bool(form["score_first"]) and planning
        has_score = bool((form["abc_text"] or "").strip())
        return {
            "counter_md": {
                "value": ui_text.COUNTER.format(
                    style=len((form["style"] or "").strip()),
                    style_limit=request_rules.STYLE_LIMIT,
                    lyrics=len((form["lyrics"] or "").strip()),
                    lyrics_limit=request_rules.LYRICS_LIMIT,
                )
            },
            "primary_btn": {"value": ui_text.BTN_PLAN if score_first else ui_text.BTN_GENERATE},
            "score_first_chk": {
                "interactive": planning,
                "info": "" if planning else ui_text.SCORE_FIRST_DISABLED,
            },
            "cfg_slider": {"interactive": not form["cfg_auto"]},
            "fill_example_btn": {
                "visible": not ((form["style"] or "").strip() or (form["lyrics"] or "").strip())
            },
            "score_empty_md": {"visible": not has_score},
            "abc_source_md": {
                "value": ui_text.SCORE_SOURCE.get(form["abc_source"] if has_score else "none", "")
            },
            "render_btn": {"visible": has_score},
            "abc_clear_btn": {"visible": has_score},
        }

    def _form_values(self, draft: Draft) -> Patch:
        form = {
            "style": draft.style,
            "lyrics": draft.lyrics,
            "cot": draft.cot if draft.cot in request_rules.COT_MODES else "full",
            "seed": draft.seed,
            "cfg_auto": draft.cfg_scale is None,
            "cfg": draft.cfg_scale if draft.cfg_scale is not None else DEFAULT_CFG,
            "score_first": draft.score_first,
            "abc_text": draft.abc_text,
            "abc_source": draft.abc_source,
        }
        patch = {
            "style_box": {"value": form["style"]},
            "lyrics_box": {"value": form["lyrics"]},
            "cot_radio": {"value": form["cot"]},
            "seed_box": {"value": form["seed"]},
            "cfg_auto_chk": {"value": form["cfg_auto"]},
            "cfg_slider": {"value": form["cfg"]},
            "score_first_chk": {"value": form["score_first"]},
            "abc_editor": {"value": form["abc_text"]},
            "abc_source_state": {"value": form["abc_source"]},
        }
        for name, props in self._form_hints(form).items():
            patch.setdefault(name, {}).update(props)
        return patch

    # --- page load and polling ------------------------------------------------------

    def page_load(self) -> Patch:
        patch = self._form_values(self.drafts.load())
        update = self.runner.snapshot()
        for name, props in self._progress(update).items():
            patch.setdefault(name, {}).update(props)
        patch.update(self._library())
        patch.update(self._result(update.song_id if update.state == "done" else None))
        patch["env_md"] = {"value": self.environment_markdown()}
        patch["footer_warning_md"] = {"visible": not self.persistent}
        patch["restart_confirm_group"] = {"visible": False}
        return patch

    def tick(self) -> Patch:
        update = self.runner.snapshot()
        return {
            "status_html": {"value": render_status(update)},
            "cancel_btn": {"visible": update.running},
        }

    # --- compose tab ----------------------------------------------------------------

    def form_changed(self, form: dict) -> Patch:
        self._save_draft(form)
        return self._form_hints(form)

    def fill_example(self, form: dict) -> Patch:
        form = {**form, "style": ui_text.EXAMPLE_STYLE, "lyrics": ui_text.EXAMPLE_LYRICS}
        self._save_draft(form)
        patch = self._form_hints(form)
        patch["style_box"] = {"value": form["style"]}
        patch["lyrics_box"] = {"value": form["lyrics"]}
        return patch

    def submit(self, form: dict) -> Iterator[Patch]:
        """Primary button: plan first when asked to, otherwise make the song."""
        self._save_draft(form)
        raw = self._raw(form)
        if form["score_first"] and form["cot"] != "off":
            yield from self._drive(self.runner.run_plan(raw), form)
        else:
            parent = self.drafts.load().parent_song_id
            yield from self._drive(self.runner.run_render(raw, parent_song_id=parent), form)

    def render_from_score(self, form: dict) -> Iterator[Patch]:
        self._save_draft(form)
        abc = (form["abc_text"] or "").strip()
        if not abc:
            yield _toast("warning", ui_text.SCORE_EMPTY)
            return
        source = form["abc_source"] if form["abc_source"] != "none" else "edited"
        parent = self.drafts.load().parent_song_id
        updates = self.runner.run_render(
            self._raw(form), abc=abc, abc_source=source, parent_song_id=parent
        )
        yield from self._drive(updates, form)

    def _drive(self, updates: Iterator[JobUpdate], form: dict) -> Iterator[Patch]:
        last = None
        for update in updates:
            if update.rejected:
                yield _toast("warning", ui_text.ERRORS["E_BUSY"])
                return
            last = update
            yield self._progress(update)
        if last is None:
            return

        patch = self._progress(last)
        if last.state == "score_ready":
            planned = {**form, "abc_text": last.abc or "", "abc_source": "planned"}
            self._save_draft(planned)
            patch["abc_editor"] = {"value": planned["abc_text"]}
            patch["abc_source_state"] = {"value": "planned"}
            for name, props in self._form_hints(planned).items():
                if name.startswith(("score_", "abc_", "render_")):
                    patch.setdefault(name, {}).update(props)
            patch["tabs"] = {"selected": "score"}
        elif last.state == "done":
            patch.update(self._result(last.song_id))
            patch.update(self._library())
            patch["tabs"] = {"selected": "result"}
            patch["env_md"] = {"value": self.environment_markdown()}
            patch["_toast"] = ("info", ui_text.SONG_DONE_TOAST)
        elif last.state == "cancelled":
            patch["_toast"] = ("info", ui_text.ERRORS["E_CANCELLED"])
        elif last.state == "failed" and last.error_code not in ("E_VALIDATION", "E_ABC_INVALID"):
            patch["env_acc"] = {"open": True}
            patch["env_md"] = {"value": self.environment_markdown()}
        yield patch

    def cancel(self) -> Patch:
        outcome = self.runner.cancel()
        patch = self.tick()
        if outcome == "too_late":
            patch["_toast"] = ("warning", ui_text.CANCEL_TOO_LATE)
        return patch

    def restart_ask(self) -> Patch:
        if self.runner.snapshot().running:
            return _toast("warning", ui_text.ERRORS["E_BUSY"])
        return {"restart_confirm_group": {"visible": True}}

    def restart_back(self) -> Patch:
        return {"restart_confirm_group": {"visible": False}}

    def restart_confirm(self) -> Patch:
        if self.runner.snapshot().running:
            return _toast("warning", ui_text.ERRORS["E_BUSY"])
        self.drafts.clear()
        self.log.write("draft_cleared")
        patch = self._form_values(Draft())
        patch["restart_confirm_group"] = {"visible": False}
        patch["error_html"] = {"value": "", "visible": False}
        patch["tabs"] = {"selected": "compose"}
        return patch

    # --- score tab ------------------------------------------------------------------

    def abc_edited(self, form: dict) -> Patch:
        """The score box changed, by the user or by a handler that filled it.

        Handlers save the draft before filling the box, so text equal to the
        saved draft is not a user edit and keeps its source.
        """
        text = form["abc_text"] or ""
        source = form["abc_source"]
        if not text.strip():
            source = "none"
        elif text == self.drafts.load().abc_text:
            source = source if source != "none" else "edited"
        elif source in ("planned", "none"):
            source = "edited"
        form = {**form, "abc_source": source}
        self._save_draft(form)
        patch = self._form_hints(form)
        patch["abc_source_state"] = {"value": source}
        return patch

    def abc_uploaded(self, path: str | None, form: dict) -> Patch:
        if not path:
            return {}
        try:
            text = request_rules.read_abc_file(path)
        except request_rules.AbcFileRejected as rejected:
            self.log.write("abc_uploaded", accepted=False)
            return {**_toast("warning", str(rejected)), "abc_upload": {"value": None}}
        except OSError:
            return {**_toast("warning", ui_text.ABC_NOT_TEXT), "abc_upload": {"value": None}}
        self.log.write("abc_uploaded", accepted=True, bytes=len(text.encode("utf-8")))
        form = {**form, "abc_text": text, "abc_source": "uploaded"}
        self._save_draft(form)
        patch = self._form_hints(form)
        patch["abc_editor"] = {"value": text}
        patch["abc_source_state"] = {"value": "uploaded"}
        patch["abc_upload"] = {"value": None}
        patch["_toast"] = ("info", ui_text.UPLOAD_LOADED)
        return patch

    def abc_cleared(self, form: dict) -> Patch:
        form = {**form, "abc_text": "", "abc_source": "none"}
        self._save_draft(form)
        patch = self._form_hints(form)
        patch["abc_editor"] = {"value": ""}
        patch["abc_source_state"] = {"value": "none"}
        return patch

    # --- result tab -----------------------------------------------------------------

    def _result(self, song_id: str | None) -> Patch:
        record = self._find(song_id)
        if record is None or not record.playable:
            return {
                "result_empty_md": {"visible": True},
                "result_group": {"visible": False},
                "result_song_state": {"value": None},
            }
        score = self.store.score_text(record.song_id)
        audio = str(self.store.audio_path(record.song_id))
        return {
            "result_empty_md": {"visible": False},
            "result_group": {"visible": True},
            "result_title_md": {"value": f"### {record.title}　{_duration(record.duration_sec)}"},
            "result_audio": {"value": audio},
            "truncated_md": {"visible": record.truncated},
            "download_btn": {"value": audio},
            "pack_file": {"value": None, "visible": False},
            "result_score_acc": {"visible": score is not None},
            "result_score": {"value": score or ""},
            "result_song_state": {"value": record.song_id},
            **self._mp3_download(record.song_id, MP3_BUTTONS["result"]),
        }

    def _mp3_download(self, song_id: str | None, button: str) -> Patch:
        """Point the MP3 button at the song's MP3, encoding it first if needed.

        Songs saved before MP3 export existed, or whose encode failed during
        the job, are encoded here the first time they are shown; the file is
        then reused. If encoding is impossible the button stays visible but
        disabled.
        """
        path = None
        if song_id:
            try:
                path = self.store.make_mp3(song_id)
            except Exception as error:
                self.log.write(
                    "mp3_failed", song_id=song_id, detail=f"{type(error).__name__}: {error}"[:300]
                )
        return {
            button: {
                "value": str(path) if path else None,
                "interactive": path is not None,
                "label": ui_text.BTN_DOWNLOAD_MP3 if path else ui_text.MP3_UNAVAILABLE,
            }
        }

    def _find(self, song_id: str | None) -> SongRecord | None:
        if not song_id:
            return None
        try:
            return self.store.get(song_id)
        except (SongNotFound, InvalidSongId):
            return None

    def pack(self, song_id: str | None, target: str = "pack_file") -> Patch:
        if self._find(song_id) is None:
            return _toast("warning", ui_text.LIBRARY_PICK)
        try:
            archive = self.store.export_zip(song_id)
        except StorageError as error:
            return _toast("warning", f"{ui_text.ERRORS['E_STORAGE']} {error.detail}")
        self.log.write("song_exported", song_id=song_id)
        return {target: {"value": str(archive), "visible": True}}

    def load_to_form(self, song_id: str | None) -> Patch:
        """Copy a song's request back into the form as the start of a new take."""
        record = self._find(song_id)
        if record is None or not record.request:
            return _toast("warning", ui_text.LIBRARY_PICK)
        if self.runner.snapshot().running:
            return _toast("warning", ui_text.ERRORS["E_BUSY"])
        request = record.request
        edited_score = record.abc_source in ("edited", "uploaded")
        draft = Draft(
            style=request.get("style", ""),
            lyrics=request.get("lyrics", ""),
            cot=request.get("cot", "full"),
            seed=None,
            cfg_scale=request.get("cfg_scale"),
            score_first=False,
            abc_text=(request.get("abc") or "") if edited_score else "",
            abc_source=record.abc_source if edited_score else "none",
            parent_song_id=record.song_id,
        )
        self.drafts.save(draft)
        self.log.write("song_reloaded", song_id=record.song_id)
        patch = self._form_values(draft)
        patch["tabs"] = {"selected": "compose"}
        return patch

    # --- library tab ----------------------------------------------------------------

    def _library(self, selected: str | None = None) -> Patch:
        records = self.store.list_songs()
        choices = []
        for record in records:
            parts = [record.title + (record.problem or ""), _created(record.created_at)]
            if record.playable:
                parts.append(_duration(record.duration_sec))
            cot = COT_LABELS.get(record.request.get("cot"))
            if cot:
                parts.append(cot)
            choices.append(("　".join(part for part in parts if part), record.song_id))
        if selected not in [record.song_id for record in records]:
            selected = None
        return {
            "library_radio": {"choices": choices, "value": selected, "visible": bool(choices)},
            "library_empty_md": {"visible": not choices},
        }

    def refresh_library(self, selected: str | None = None) -> Patch:
        """Reload the list, keeping the open song open if it still exists."""
        patch = self._library(selected)
        patch.update(self._detail(self._find(selected)))
        return patch

    def _detail(self, record: SongRecord | None) -> Patch:
        if record is None:
            return {"detail_group": {"visible": False}, "selected_song_state": {"value": None}}
        parent = ""
        if record.parent_song_id:
            origin = self._find(record.parent_song_id)
            parent = f"來源：{origin.title if origin else ui_text.PARENT_DELETED}"
        audio = str(self.store.audio_path(record.song_id)) if record.playable else None
        return {
            "detail_group": {"visible": True},
            "selected_song_state": {"value": record.song_id},
            "detail_audio": {"value": audio, "visible": record.playable},
            "detail_audio_btn": {"value": audio, "interactive": record.playable},
            "detail_parent_md": {"value": parent, "visible": bool(parent)},
            "title_box": {"value": record.title},
            "note_box": {"value": record.note},
            "load_btn": {"interactive": bool(record.request)},
            "detail_pack_file": {"value": None, "visible": False},
            "delete_confirm_btn": {"visible": False},
            **self._mp3_download(
                record.song_id if record.playable else None, MP3_BUTTONS["library"]
            ),
        }

    def select_song(self, song_id: str | None) -> Patch:
        """The library radio changed.

        Gradio 6 also fires .change when a handler resets the radio, and on a
        first visit to the tab that reset can arrive after the user's own
        pick. An empty value therefore changes nothing; refresh_library and
        delete_confirm hide the detail themselves when they mean to.
        """
        if not song_id:
            return {}
        return self._detail(self._find(song_id))

    def save_meta(self, song_id: str | None, title: str, note: str) -> Patch:
        if self._find(song_id) is None:
            return _toast("warning", ui_text.LIBRARY_PICK)
        try:
            self.store.update(song_id, title=title, note=note)
        except InvalidMetadata as invalid:
            return _toast("warning", str(invalid))
        except (StorageError, SongNotFound) as error:
            return _toast("warning", f"{ui_text.ERRORS['E_STORAGE']} {error}")
        self.log.write("song_updated", song_id=song_id)
        patch = self._library(selected=song_id)
        patch["_toast"] = ("info", ui_text.SAVED_TOAST)
        return patch

    def delete_ask(self, song_id: str | None) -> Patch:
        if self._find(song_id) is None:
            return _toast("warning", ui_text.LIBRARY_PICK)
        return {"delete_confirm_btn": {"visible": True}}

    def delete_confirm(self, song_id: str | None, shown_song_id: str | None = None) -> Patch:
        if self._find(song_id) is None:
            return _toast("warning", ui_text.LIBRARY_PICK)
        self.store.delete(song_id)
        self.log.write("song_deleted", song_id=song_id)
        patch = self.refresh_library()
        if shown_song_id == song_id:
            patch.update(self._result(None))
        patch["_toast"] = ("info", ui_text.DELETED_TOAST)
        return patch

    # --- environment ----------------------------------------------------------------

    def environment_markdown(self) -> str:
        report = self.environment_info.get("report", {})
        capability = report.get("compute_capability")
        lines = [
            f"- GPU：{report.get('gpu_name') or '未知'}"
            + (f"（{report['vram_total_gib']:.1f} GiB）" if report.get("vram_total_gib") else ""),
            f"- 運算能力等級：{'.'.join(map(str, capability)) if capability else '未知'}",
            f"- 引擎狀態：{ui_text.ENGINE_STATES.get(self.engine.state, self.engine.state)}",
        ]
        if self.engine.load_seconds is not None:
            lines.append(f"- 上次引擎載入：{self.engine.load_seconds:.0f} 秒")
        for name, version in self.runner.versions.items():
            lines.append(f"- {name}：{version}")
        songs = self.store.list_songs()
        latest = next((song for song in songs if song.playable), None)
        if latest is not None:
            total = latest.timing.get("e2e_seconds")
            lines.append(
                f"- 最近一首：長度 {_duration(latest.duration_sec)}"
                + (f"，耗時 {total:.0f} 秒" if isinstance(total, (int, float)) else "")
                + f"，峰值 VRAM {latest.peak_vram_gib:.2f} GiB"
            )
        lines.append(f"- 歌曲數：{len(songs)}，工作目錄 {self.store.total_bytes() / 2**20:.1f} MB")
        lines.append(f"- 保存位置：`{self.store.root}`")
        return "\n".join(lines)

    def release_engine(self) -> Patch:
        if self.runner.snapshot().running:
            return _toast("warning", ui_text.ENGINE_BUSY)
        self.engine.close()
        self.log.write("engine_released")
        return {
            "env_md": {"value": self.environment_markdown()},
            "_toast": ("info", ui_text.ENGINE_RELEASED_TOAST),
        }

    def diagnostics(self) -> Patch:
        header = {
            "environment": self.environment_info,
            "versions": self.runner.versions,
            "engine_state": self.engine.state,
        }
        return {"diag_box": {"value": self.log.diagnostics(header), "visible": True}}
