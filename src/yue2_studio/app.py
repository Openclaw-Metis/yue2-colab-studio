"""Gradio layout and event wiring. All behaviour lives in studio.py."""

from __future__ import annotations

import inspect

import gradio as gr

from . import request_rules, ui_text
from .studio import FORM_FIELDS, Studio, as_form

# Polling keeps the status bar alive after a page reload, when the handler
# that was streaming progress is gone.
TICK_SECONDS = 2


def build_app(studio: Studio) -> gr.Blocks:
    c: dict[str, gr.components.Component] = {}

    with gr.Blocks(title=ui_text.APP_TITLE, analytics_enabled=False) as demo:
        with gr.Row(equal_height=True):
            c["status_html"] = gr.HTML(scale=8)
            c["cancel_btn"] = gr.Button(ui_text.BTN_CANCEL, visible=False, scale=1, min_width=90)
        c["error_html"] = gr.HTML(visible=False)

        with gr.Tabs(selected="compose") as tabs:
            c["tabs"] = tabs

            with gr.Tab(ui_text.TAB_COMPOSE, id="compose"):
                c["style_box"] = gr.Textbox(
                    label=ui_text.STYLE_LABEL, info=ui_text.STYLE_INFO, lines=3, max_lines=6
                )
                c["lyrics_box"] = gr.Textbox(
                    label=ui_text.LYRICS_LABEL, info=ui_text.LYRICS_INFO, lines=10, max_lines=24
                )
                with gr.Row():
                    c["counter_md"] = gr.Markdown(elem_classes="studio-quiet")
                    c["fill_example_btn"] = gr.Button(
                        ui_text.FILL_EXAMPLE, variant="secondary", size="sm", scale=0, min_width=120
                    )
                with gr.Row(equal_height=True):
                    c["score_first_chk"] = gr.Checkbox(label=ui_text.SCORE_FIRST_LABEL, scale=3)
                    c["restart_btn"] = gr.Button(ui_text.BTN_RESTART, scale=1, min_width=120)
                    c["primary_btn"] = gr.Button(
                        ui_text.BTN_GENERATE, variant="primary", scale=2, min_width=200
                    )
                with gr.Column(visible=False) as restart_confirm_group:
                    c["restart_confirm_group"] = restart_confirm_group
                    gr.Markdown(ui_text.RESTART_WARNING)
                    with gr.Row():
                        restart_confirm_btn = gr.Button(ui_text.BTN_RESTART_CONFIRM, variant="stop")
                        restart_back_btn = gr.Button(ui_text.BTN_BACK)
                with gr.Accordion(ui_text.ADVANCED_LABEL, open=False):
                    c["cot_radio"] = gr.Radio(
                        ui_text.COT_CHOICES, value="full", label=ui_text.COT_LABEL
                    )
                    c["seed_box"] = gr.Number(
                        label=ui_text.SEED_LABEL,
                        info=ui_text.SEED_INFO,
                        value=None,
                        precision=0,
                        minimum=0,
                        maximum=request_rules.SEED_MAX,
                    )
                    c["cfg_auto_chk"] = gr.Checkbox(label=ui_text.CFG_AUTO_LABEL, value=True)
                    c["cfg_slider"] = gr.Slider(
                        request_rules.CFG_MIN,
                        request_rules.CFG_MAX,
                        value=1.0,
                        step=0.05,
                        label=ui_text.CFG_LABEL,
                        info=ui_text.CFG_INFO,
                        interactive=False,
                    )

            with gr.Tab(ui_text.TAB_SCORE, id="score"):
                c["score_empty_md"] = gr.Markdown(ui_text.SCORE_EMPTY)
                c["abc_source_md"] = gr.Markdown()
                c["abc_editor"] = gr.Textbox(
                    label=ui_text.SCORE_LABEL,
                    info=ui_text.SCORE_VOICES_NOTE,
                    lines=16,
                    max_lines=40,
                    elem_classes="studio-score",
                )
                with gr.Row():
                    c["abc_clear_btn"] = gr.Button(ui_text.BTN_CLEAR_SCORE, visible=False, scale=1)
                    c["render_btn"] = gr.Button(
                        ui_text.BTN_RENDER_FROM_SCORE, variant="primary", visible=False, scale=2
                    )
                with gr.Accordion(ui_text.UPLOAD_LABEL, open=False):
                    c["abc_upload"] = gr.File(
                        label=ui_text.UPLOAD_LABEL,
                        file_types=list(request_rules.ABC_SUFFIXES),
                        file_count="single",
                        type="filepath",
                    )

            with gr.Tab(ui_text.TAB_RESULT, id="result"):
                c["result_empty_md"] = gr.Markdown(ui_text.RESULT_EMPTY)
                with gr.Column(visible=False) as result_group:
                    c["result_group"] = result_group
                    c["result_title_md"] = gr.Markdown()
                    c["truncated_md"] = gr.Markdown(ui_text.TRUNCATED_NOTICE, visible=False)
                    c["result_audio"] = gr.Audio(
                        label=ui_text.RESULT_AUDIO_LABEL,
                        type="filepath",
                        interactive=False,
                        editable=False,
                    )
                    with gr.Row():
                        c["download_btn"] = gr.DownloadButton(ui_text.BTN_DOWNLOAD_AUDIO)
                        c["pack_btn"] = gr.Button(ui_text.BTN_PACK)
                        c["remix_btn"] = gr.Button(ui_text.BTN_REMIX, variant="primary")
                    c["pack_file"] = gr.File(
                        label=ui_text.PACK_LABEL, visible=False, interactive=False
                    )
                    with gr.Accordion(ui_text.RESULT_SCORE_LABEL, open=False) as result_score_acc:
                        c["result_score_acc"] = result_score_acc
                        c["result_score"] = gr.Textbox(
                            show_label=False,
                            lines=12,
                            max_lines=40,
                            interactive=False,
                            elem_classes="studio-score",
                        )

            with gr.Tab(ui_text.TAB_LIBRARY, id="library") as library_tab:
                c["library_empty_md"] = gr.Markdown(ui_text.LIBRARY_EMPTY)
                c["library_radio"] = gr.Radio(
                    choices=[],
                    label=ui_text.LIBRARY_PICK,
                    visible=False,
                    elem_classes="studio-songs",
                )
                refresh_btn = gr.Button(ui_text.BTN_REFRESH, size="sm")
                with gr.Column(visible=False) as detail_group:
                    c["detail_group"] = detail_group
                    c["detail_audio"] = gr.Audio(
                        label=ui_text.RESULT_AUDIO_LABEL,
                        type="filepath",
                        interactive=False,
                        editable=False,
                    )
                    c["detail_parent_md"] = gr.Markdown(visible=False, elem_classes="studio-quiet")
                    c["title_box"] = gr.Textbox(label=ui_text.TITLE_LABEL, max_lines=1)
                    c["note_box"] = gr.Textbox(label=ui_text.NOTE_LABEL, lines=2, max_lines=6)
                    with gr.Row():
                        save_meta_btn = gr.Button(ui_text.BTN_SAVE_META)
                        c["load_btn"] = gr.Button(ui_text.BTN_LOAD_TO_FORM, variant="primary")
                        detail_pack_btn = gr.Button(ui_text.BTN_PACK)
                        delete_btn = gr.Button(ui_text.BTN_DELETE)
                    c["delete_confirm_btn"] = gr.Button(
                        ui_text.BTN_DELETE_CONFIRM, variant="stop", visible=False
                    )
                    c["detail_pack_file"] = gr.File(
                        label=ui_text.PACK_LABEL, visible=False, interactive=False
                    )

        with gr.Accordion(ui_text.ENV_LABEL, open=False) as env_acc:
            c["env_acc"] = env_acc
            c["env_md"] = gr.Markdown()
            with gr.Row():
                release_btn = gr.Button(ui_text.BTN_RELEASE_ENGINE)
                diag_btn = gr.Button(ui_text.BTN_DIAGNOSTICS)
            c["diag_box"] = gr.Textbox(
                label=ui_text.DIAGNOSTICS_LABEL,
                lines=10,
                max_lines=20,
                visible=False,
                interactive=False,
                buttons=["copy"],
            )

        c["footer_warning_md"] = gr.Markdown(ui_text.EPHEMERAL_WARNING, elem_classes="studio-quiet")
        gr.Markdown(ui_text.LICENSE_FOOTER, elem_classes="studio-quiet")

        c["abc_source_state"] = gr.State("none")
        c["result_song_state"] = gr.State(None)
        c["selected_song_state"] = gr.State(None)
        timer = gr.Timer(TICK_SECONDS)

        outputs = list(c.values())

        def to_updates(patch: dict) -> dict:
            patch = dict(patch)
            toast = patch.pop("_toast", None)
            if toast:
                (gr.Warning if toast[0] == "warning" else gr.Info)(toast[1])
            updates = {}
            for name, props in patch.items():
                component = c[name]
                if isinstance(component, gr.State):
                    updates[component] = props["value"]
                else:
                    updates[component] = gr.update(**props)
            return updates

        def bind(handler):
            """Adapt a Studio method returning patches to a Gradio handler."""
            if inspect.isgeneratorfunction(handler):

                def streaming(*args):
                    for patch in handler(*args):
                        yield to_updates(patch)

                return streaming

            def single(*args):
                return to_updates(handler(*args))

            return single

        form = [
            c["style_box"],
            c["lyrics_box"],
            c["cot_radio"],
            c["seed_box"],
            c["cfg_auto_chk"],
            c["cfg_slider"],
            c["score_first_chk"],
            c["abc_editor"],
            c["abc_source_state"],
        ]
        assert len(form) == len(FORM_FIELDS)

        def with_form(method):
            if inspect.isgeneratorfunction(method):

                def streaming(*values):
                    yield from method(as_form(*values))

                return bind(streaming)
            return bind(lambda *values: method(as_form(*values)))

        quiet = {"show_progress": "hidden", "api_visibility": "private"}
        # No concurrency limit on generation events: a second click must reach
        # the job runner and be refused at once, not wait in Gradio's queue and
        # start another song when the first finishes.
        unqueued = {**quiet, "concurrency_limit": None}

        demo.load(bind(studio.page_load), None, outputs, **quiet)
        timer.tick(bind(studio.tick), None, outputs, **quiet)

        # .change, not .input: with Gradio 6.17.3 the Textbox .input listener did
        # not fire for typed text in browser testing, while .change did. .change
        # also fires for values set by handlers, so no handler bound here may
        # write back to a form field.
        save_draft = with_form(studio.form_changed)
        for control in (
            c["style_box"],
            c["lyrics_box"],
            c["cot_radio"],
            c["seed_box"],
            c["cfg_auto_chk"],
            c["cfg_slider"],
            c["score_first_chk"],
        ):
            control.change(save_draft, form, outputs, trigger_mode="always_last", **quiet)

        c["fill_example_btn"].click(with_form(studio.fill_example), form, outputs, **quiet)
        c["primary_btn"].click(with_form(studio.submit), form, outputs, **unqueued)
        c["render_btn"].click(with_form(studio.render_from_score), form, outputs, **unqueued)
        c["cancel_btn"].click(bind(studio.cancel), None, outputs, **unqueued)

        c["restart_btn"].click(bind(studio.restart_ask), None, outputs, **quiet)
        restart_back_btn.click(bind(studio.restart_back), None, outputs, **quiet)
        restart_confirm_btn.click(bind(studio.restart_confirm), None, outputs, **quiet)

        c["abc_editor"].change(
            with_form(studio.abc_edited), form, outputs, trigger_mode="always_last", **quiet
        )
        c["abc_upload"].upload(
            bind(lambda path, *values: studio.abc_uploaded(path, as_form(*values))),
            [c["abc_upload"], *form],
            outputs,
            **quiet,
        )
        c["abc_clear_btn"].click(with_form(studio.abc_cleared), form, outputs, **quiet)

        c["pack_btn"].click(bind(studio.pack), c["result_song_state"], outputs, **quiet)
        c["remix_btn"].click(bind(studio.load_to_form), c["result_song_state"], outputs, **quiet)

        library_tab.select(bind(studio.refresh_library), None, outputs, **quiet)
        refresh_btn.click(bind(studio.refresh_library), None, outputs, **quiet)

        c["library_radio"].change(bind(studio.select_song), c["library_radio"], outputs, **quiet)
        save_meta_btn.click(
            bind(studio.save_meta),
            [c["selected_song_state"], c["title_box"], c["note_box"]],
            outputs,
            **quiet,
        )
        c["load_btn"].click(bind(studio.load_to_form), c["selected_song_state"], outputs, **quiet)
        detail_pack_btn.click(
            bind(lambda song_id: studio.pack(song_id, "detail_pack_file")),
            c["selected_song_state"],
            outputs,
            **quiet,
        )
        delete_btn.click(bind(studio.delete_ask), c["selected_song_state"], outputs, **quiet)
        c["delete_confirm_btn"].click(
            bind(studio.delete_confirm),
            [c["selected_song_state"], c["result_song_state"]],
            outputs,
            **quiet,
        )

        release_btn.click(bind(studio.release_engine), None, outputs, **quiet)
        diag_btn.click(bind(studio.diagnostics), None, outputs, **quiet)

    return demo
