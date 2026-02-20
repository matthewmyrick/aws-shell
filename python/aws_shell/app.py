"""Main AWS Shell application - the REPL loop."""
import os
import shlex
import threading

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
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
    def __init__(self, config_path=None):
        self.config = ShellConfig(config_path=config_path)
        self.session_manager = AWSSessionManager(self.config)
        self.registry = CommandRegistry(self.config, self.session_manager)
        self.completer = build_completer(self.registry, self.session_manager)

        history_path = os.path.expanduser("~/.aws_shell_history")

        bindings = KeyBindings()

        @bindings.add(Keys.Escape, eager=True)
        def _handle_escape(event):
            """Dismiss the completion menu on Escape."""
            buf = event.current_buffer
            if buf.complete_state:
                buf.cancel_completion()

        self.prompt_session = PromptSession(
            history=FileHistory(history_path),
            completer=self.completer,
            lexer=PygmentsLexer(AWSShellLexer),
            style=get_style(),
            auto_suggest=AutoSuggestFromHistory(),
            complete_while_typing=True,
            key_bindings=bindings,
        )

        # Background-initialize AI conversation (loads docs + builds system prompt)
        self._init_ai_background()

    def _init_ai_background(self):
        """Spawn a daemon thread to pre-build the AI system prompt."""
        from .commands.ai_cmd import _init_conversation_background

        def _init():
            try:
                _init_conversation_background(self.config, self.session_manager)
            except Exception:
                pass  # Non-critical — will be retried lazily on first `ai` call

        t = threading.Thread(target=_init, daemon=True)
        t.start()

    def run(self, start_in_python=False):
        show_welcome(self.config, self.session_manager)

        if start_in_python:
            self.registry.dispatch("py", [])

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
