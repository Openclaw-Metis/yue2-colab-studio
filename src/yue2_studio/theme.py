"""Light, quiet tool styling.

Deep blue marks the one primary action per screen, pale blue-grey is surface,
amber means "in progress or needs attention", red appears only on errors.
"""

from __future__ import annotations

PRIMARY = "#2F5D8C"
SURFACE = "#E8EEF5"
INK = "#1F2933"
MUTED = "#6B7785"
ACCENT = "#E07A1F"
ERROR = "#B42318"


def build_theme():
    import gradio as gr

    blue = gr.themes.Color(
        c50="#F2F6FA",
        c100=SURFACE,
        c200="#CCDAE8",
        c300="#A5BDD6",
        c400="#6F93BA",
        c500="#44709F",
        c600=PRIMARY,
        c700="#274E76",
        c800="#1F3E5E",
        c900="#182F47",
        c950="#101F30",
    )
    return gr.themes.Base(primary_hue=blue, neutral_hue="slate").set(
        body_background_fill="#FFFFFF",
        body_text_color=INK,
        button_primary_background_fill=PRIMARY,
        button_primary_background_fill_hover="#274E76",
        button_primary_text_color="#FFFFFF",
        block_title_text_color=INK,
        block_info_text_color=MUTED,
    )


CSS = f"""
.studio-status {{
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  background: {SURFACE}; color: {INK}; border-radius: 8px; padding: 14px 18px; min-height: 28px;
}}
.studio-stage {{ font-weight: 600; }}
.studio-dot {{ width: 12px; height: 12px; border-radius: 50%; background: {ACCENT}; }}
.studio-bar {{
  flex: 1 1 240px; height: 10px; border-radius: 5px; background: #FFFFFF;
  border: 1px solid {MUTED}; overflow: hidden;
}}
.studio-bar > div {{ height: 100%; background: {ACCENT}; transition: width .4s; }}
.studio-bar-busy > div {{ width: 35%; animation: studio-slide 1.6s ease-in-out infinite; }}
@keyframes studio-slide {{ 0% {{ margin-left: -35%; }} 100% {{ margin-left: 100%; }} }}
.studio-elapsed, .studio-notice {{ color: {MUTED}; font-size: 0.95em; }}
.studio-error {{
  border: 2px solid {ERROR}; border-radius: 8px; padding: 12px 18px; color: {INK};
  background: #FFF6F5;
}}
.studio-error strong {{ color: {ERROR}; }}
.studio-error p, .studio-error ul {{ margin: 6px 0 0; }}
.studio-detail, .studio-code {{ color: {MUTED}; font-size: 0.9em; word-break: break-word; }}
.studio-score textarea {{ font-family: ui-monospace, Consolas, "Courier New", monospace; }}
.studio-songs .wrap {{ flex-direction: column; align-items: stretch; }}
.studio-quiet {{ color: {MUTED}; font-size: 0.92em; }}
"""

# The palette is designed for light mode only, so do not follow the browser's
# dark preference.
FORCE_LIGHT_HEAD = """
<script>
(function () {
  var url = new URL(window.location);
  if (url.searchParams.get("__theme") !== "light") {
    url.searchParams.set("__theme", "light");
    window.location.replace(url.href);
  }
})();
</script>
"""
