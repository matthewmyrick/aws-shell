"""Main AWS Shell application - the REPL loop."""
import os
import shlex

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from .completer import build_completer
from .lexer import AWSShellLexer
from .style import get_style
from .toolbar import get_toolbar
from .welcome import show_welcome
from .config import ShellConfig
from .commands import CommandRegistry
from .utils.aws_session import AWSSessionManager


class AWSShell:
    def __init__(self):
        self.config = ShellConfig()
        self.session_manager = AWSSessionManager(self.config)
        self.registry = CommandRegistry(self.config, self.session_manager)
        self.completer = build_completer(self.registry, self.session_manager)

        history_path = os.path.expanduser("~/.aws_shell_history")
        self.prompt_session = PromptSession(
            history=FileHistory(history_path),
            completer=self.completer,
            lexer=PygmentsLexer(AWSShellLexer),
            style=get_style(),
            auto_suggest=AutoSuggestFromHistory(),
            complete_while_typing=True,
        )

    def run(self):
        show_welcome(self.config, self.session_manager)

        while True:
            try:
                toolbar = get_toolbar(self.config, self.session_manager)
                text = self.prompt_session.prompt(
                    "aws> ",
                    bottom_toolbar=toolbar,
                ).strip()

                if not text:
                    continue
                self._execute(text)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

    def _execute(self, text):
        try:
            parts = shlex.split(text)
        except ValueError as e:
            from rich.console import Console
            Console().print(f"[bold red]Parse error:[/bold red] {e}")
            return

        command_name = parts[0].lower()
        args = parts[1:]
        self.registry.dispatch(command_name, args)
