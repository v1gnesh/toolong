from __future__ import annotations

import locale
from pathlib import Path

from rich import terminal_theme
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.lazy import Lazy
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane
from textual.css.query import NoMatches

from toolong.log_view import LogView
from toolong.watcher import get_watcher
from toolong.help import HelpScreen


locale.setlocale(locale.LC_ALL, "")


class LogScreen(Screen):
    """Shows log files."""

    BINDINGS = [
        Binding("f1", "help", "Help"),
    ]

    CSS = """
    LogScreen {
        layers: overlay;
        & TabPane {           
            padding: 0;
        }
        & Tabs:focus Underline > .underline--bar {
            color: $accent;
        }        
        Underline > .underline--bar {
            color: $panel;
        }
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        assert isinstance(self.app, UI)
        with TabbedContent():
            if len(self.app.file_paths) > 1:
                with TabPane("All"):
                    yield LogView(
                        self.app.file_paths,
                        self.app.watcher,
                    )
            for path in self.app.file_paths:
                with TabPane(path):
                    yield LogView(
                        [path],
                        self.app.watcher,
                    )

    async def on_mount(self) -> None:
        """Handle mount."""
        assert isinstance(self.app, UI)
        self.query("TabbedContent Tabs").set(display=len(self.query(TabPane)) > 1)
        active_pane = self.query_one(TabbedContent).active_pane
        if active_pane is not None:
            try:
                active_pane.query_one("LogView > LogLines").focus()
            except NoMatches:
                try:
                    active_pane.query_one("LogView > EliotTree").focus()
                except NoMatches:
                    pass

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())


from functools import total_ordering


@total_ordering
class CompareTokens:
    """Compare filenames."""

    def __init__(self, path: str) -> None:
        self.tokens = [
            int(token) if token.isdigit() else token.lower()
            for token in path.split("/")[-1].split(".")
        ]

    def __eq__(self, other: object) -> bool:
        return self.tokens == other.tokens

    def __lt__(self, other: CompareTokens) -> bool:
        for token1, token2 in zip(self.tokens, other.tokens):
            try:
                if token1 < token2:
                    return True
            except TypeError:
                if str(token1) < str(token2):
                    return True
        return len(self.tokens) < len(other.tokens)


class UI(App):
    """The top level App object."""

    @classmethod
    def sort_paths(cls, paths: list[str]) -> list[str]:
        return sorted(paths, key=CompareTokens)

    def __init__(
        self, file_paths: list[str], merge: bool = False, save_merge: str | None = None
    ) -> None:
        self.file_paths = self.sort_paths(file_paths)
        self.merge = merge
        self.save_merge = save_merge
        self.watcher = get_watcher()
        super().__init__()

    async def on_mount(self) -> None:
        self.ansi_theme_dark = terminal_theme.DIMMED_MONOKAI
        await self.push_screen(LogScreen())
        try:
            self.screen.query_one("LogLines").focus()
        except NoMatches:
            try:
                self.screen.query_one("EliotTree").focus()
            except NoMatches:
                pass
        self.watcher.start()

    def on_unmount(self) -> None:
        self.watcher.close()
