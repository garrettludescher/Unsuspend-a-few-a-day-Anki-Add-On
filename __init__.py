"""Daily Unsuspend: release a set number of suspended cards per tag group each day."""

from __future__ import annotations

from html import escape
from typing import Any

from aqt import gui_hooks, mw
from aqt.deckbrowser import DeckBrowser, DeckBrowserContent
from aqt.qt import QAction

from . import core, runner
from .dialog import open_dialog

OPEN_CMD = "dailyUnsuspender:open"

# Auto-run waits for the startup sync so another device's run today is seen first.
_waiting_for_sync = False


def _maybe_auto_run() -> None:
    global _waiting_for_sync
    _waiting_for_sync = False
    if mw.col and core.should_auto_run(mw.col):
        runner.run_batch(mw, force=False)


def _on_profile_open() -> None:
    global _waiting_for_sync
    if mw.can_auto_sync():
        _waiting_for_sync = True
        # Fallback in case the sync fails and never reports finishing.
        mw.progress.single_shot(90_000, lambda: _waiting_for_sync and _maybe_auto_run())
    else:
        mw.progress.single_shot(1000, _maybe_auto_run)


def _on_sync_finished() -> None:
    if _waiting_for_sync:
        mw.progress.single_shot(300, _maybe_auto_run)


# Main deck screen button
##############################################################################

_BUTTON_CSS = """
<style>
.du-launch { margin: 18px auto 0; display: flex; gap: 12px; align-items: center;
  justify-content: center; flex-wrap: wrap; font-size: 13px; }
.du-launch button { cursor: pointer; border-radius: 999px; padding: 7px 18px;
  font: inherit; font-weight: 600; color: inherit;
  border: 1px solid rgba(255,255,255,.55);
  background: linear-gradient(180deg, rgba(255,255,255,.65), rgba(255,255,255,.25));
  box-shadow: 0 6px 18px rgba(0,0,0,.12), inset 0 1px 0 rgba(255,255,255,.8);
  backdrop-filter: blur(10px); }
.night-mode .du-launch button { border-color: rgba(255,255,255,.18);
  background: linear-gradient(180deg, rgba(255,255,255,.16), rgba(255,255,255,.05));
  box-shadow: 0 6px 18px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.15); }
.du-launch button:hover { filter: brightness(1.06); }
.du-launch span { opacity: .7; }
</style>
"""


def _status_line() -> str:
    settings = core.load(mw.col)
    batch = settings.get("last_batch")
    if batch and batch.get("day") == mw.col.sched.today:
        total = sum(s["count"] for s in batch["summary"])
        if batch.get("undone"):
            return f"Today's batch of {total} was undone"
        return f"{total} unsuspended today"
    if settings["last_run_day"] == mw.col.sched.today:
        return "Ran today · nothing left to unsuspend"
    active = sum(1 for r in settings["rules"] if r["enabled"] and r["tags"])
    if not active:
        return "No rules yet"
    return "Hasn't run today"


def _on_deck_browser_render(_: DeckBrowser, content: DeckBrowserContent) -> None:
    content.stats += (
        _BUTTON_CSS
        + '<div class="du-launch">'
        + f"<button onclick=\"pycmd('{OPEN_CMD}')\">☀ Daily Unsuspend</button>"
        + f"<span>{escape(_status_line())}</span></div>"
    )


def _on_js_message(handled: tuple[bool, Any], message: str, context: Any) -> tuple[bool, Any]:
    if message == OPEN_CMD:
        open_dialog()
        return True, None
    return handled


def _on_browser_menus(browser: Any) -> None:
    # A top-level menu bar entry that opens the window with one click.
    action = QAction("☀ Daily Unsuspend", browser)
    action.triggered.connect(open_dialog)
    browser.form.menubar.addAction(action)


# Setup
##############################################################################

mw.addonManager.setWebExports(__name__, r"web/.*\.(js|css)")
mw.addonManager.setConfigAction(__name__, open_dialog)

_action = QAction("Daily Unsuspend…", mw)
_action.triggered.connect(open_dialog)
mw.form.menuTools.addAction(_action)

gui_hooks.profile_did_open.append(_on_profile_open)
gui_hooks.sync_did_finish.append(_on_sync_finished)
gui_hooks.deck_browser_will_render_content.append(_on_deck_browser_render)
gui_hooks.webview_did_receive_js_message.append(_on_js_message)
gui_hooks.browser_menus_did_init.append(_on_browser_menus)
