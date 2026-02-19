"""AI assistant command — ask questions about AWS and get contextual help."""
import os
import re
import shutil
import subprocess
import threading

from rich.console import Console
from rich.markdown import Markdown

console = Console()

# Module-level singleton conversation, initialized lazily or via background thread
_conversation = None
_init_lock = threading.Lock()


class AIConversation:
    """Holds system prompt and message history for one session."""

    def __init__(self, system_prompt):
        self.system_prompt = system_prompt
        self.messages = []

    def add_user(self, text):
        self.messages.append({"role": "user", "content": text})

    def add_assistant(self, text):
        self.messages.append({"role": "assistant", "content": text})

    def clear(self):
        self.messages.clear()


def _load_context_doc():
    """Load the llm_context.md file from the docs package."""
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
    path = os.path.join(docs_dir, "llm_context.md")
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _build_system_prompt(config, session_manager):
    """Build the system prompt with static docs + dynamic session state."""
    context_doc = _load_context_doc()

    # Inject dynamic state
    dynamic = []
    dynamic.append(f"Current region: {config.region}")
    dynamic.append(f"Current profile: {config.profile}")
    dynamic.append(f"Output format: {config.output_format}")
    try:
        identity = session_manager.get_caller_identity()
        dynamic.append(f"Account: {identity.get('Account', 'unknown')}")
        dynamic.append(f"ARN: {identity.get('Arn', 'unknown')}")
    except Exception:
        dynamic.append("Account: (unable to determine — credentials may not be configured)")

    dynamic_block = "\n".join(dynamic)
    return f"{context_doc}\n\n---\n\n## Current Session State\n\n{dynamic_block}"


def _init_conversation_background(config, session_manager):
    """Initialize the conversation singleton in a background thread.

    Builds the system prompt (loads docs, fetches identity) so
    the first `ai` command responds without delay.
    """
    global _conversation
    with _init_lock:
        if _conversation is not None:
            return
        system_prompt = _build_system_prompt(config, session_manager)
        _conversation = AIConversation(system_prompt)


def _get_conversation(config, session_manager):
    """Get or lazily create the conversation singleton."""
    global _conversation
    if _conversation is None:
        _init_conversation_background(config, session_manager)
    return _conversation


def _call_claude_cli(conversation):
    """Fallback: call the Claude CLI when no API key is configured.

    Since the CLI is single-turn, we pack recent conversation history
    into the user message so the model has context from prior turns.
    """
    claude_path = shutil.which("claude")
    if not claude_path:
        return None  # CLI not available

    # Build a single user message that includes recent history for context
    parts = []
    # Include up to the last 10 messages for context (excluding the latest user msg)
    history = conversation.messages[:-1][-10:]
    if history:
        parts.append("## Conversation so far\n")
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            parts.append(f"**{role}:** {msg['content']}\n")
        parts.append("---\n")

    # The latest user message
    parts.append(conversation.messages[-1]["content"])
    user_message = "\n".join(parts)

    try:
        result = subprocess.run(
            [
                claude_path,
                "--print",
                "--output-format", "text",
                "--system-prompt", conversation.system_prompt,
                user_message,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        if result.stderr.strip():
            console.print(f"[bold red]Claude CLI error:[/bold red] {result.stderr.strip()}")
        return None
    except subprocess.TimeoutExpired:
        console.print("[bold red]Error:[/bold red] Claude CLI timed out after 120 seconds.")
        return None
    except Exception as e:
        console.print(f"[bold red]Claude CLI error:[/bold red] {e}")
        return None


def _call_llm(conversation, config):
    """Call the Anthropic API with the conversation history.

    Falls back to the Claude CLI if no API key is configured.
    """
    api_key = config.llm_api_key

    # If we have an API key, use the Anthropic SDK directly
    if api_key:
        try:
            import anthropic
        except ImportError:
            console.print(
                "[bold red]Error:[/bold red] The `anthropic` package is required. "
                "Install it with: pip install anthropic"
            )
            return None

        client = anthropic.Anthropic(api_key=api_key)
        try:
            response = client.messages.create(
                model=config.llm_model,
                max_tokens=4096,
                system=conversation.system_prompt,
                messages=conversation.messages,
            )
            return response.content[0].text
        except Exception as e:
            console.print(f"[bold red]LLM Error:[/bold red] {e}")
            return None

    # No API key — fallback to Claude CLI
    cli_result = _call_claude_cli(conversation)
    if cli_result is not None:
        return cli_result

    console.print(
        "[bold red]Error:[/bold red] No API key configured and `claude` CLI not found.\n"
        "Set via: [cyan]set-config llm.api_key <your-key>[/cyan]\n"
        "Or set the [cyan]ANTHROPIC_API_KEY[/cyan] environment variable.\n"
        "Or install the [cyan]claude[/cyan] CLI: [cyan]npm install -g @anthropic-ai/claude-code[/cyan]"
    )
    return None


def _extract_commands(text):
    """Extract commands from ```command fenced code blocks."""
    pattern = r"```command\s*\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    commands = []
    for match in matches:
        for line in match.strip().splitlines():
            line = line.strip()
            if line:
                commands.append(line)
    return commands


def _execute_with_approval(commands, registry, config, session_manager):
    """Print suggested commands and ask for confirmation before running."""
    for cmd_text in commands:
        console.print(f"\n[bold cyan]Suggested command:[/bold cyan] {cmd_text}")
        try:
            answer = input("Execute? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Skipped.[/dim]")
            continue

        if answer in ("y", "yes"):
            import shlex
            try:
                parts = shlex.split(cmd_text)
            except ValueError as e:
                console.print(f"[bold red]Parse error:[/bold red] {e}")
                continue
            command_name = parts[0].lower()
            args = parts[1:]
            registry.dispatch(command_name, args)
        else:
            console.print("[dim]Skipped.[/dim]")


def _render_response(text):
    """Render LLM output as Rich Markdown."""
    console.print()
    console.print(Markdown(text))
    console.print()


def cmd_ai(args, config, session_manager, registry=None):
    """Handle the `ai` command — send a question or clear history."""
    if not args:
        console.print(
            "[yellow]Usage:[/yellow] ai <your question about AWS>\n"
            "[dim]Example: ai how do I list all running EC2 instances?[/dim]\n"
            "[dim]         ai clear  — reset conversation history[/dim]"
        )
        return

    conversation = _get_conversation(config, session_manager)

    # Handle "ai clear"
    if len(args) == 1 and args[0].lower() == "clear":
        conversation.clear()
        console.print("[green]Conversation history cleared.[/green]")
        return

    question = " ".join(args)
    conversation.add_user(question)

    with console.status("[bold cyan]Thinking...[/bold cyan]"):
        response_text = _call_llm(conversation, config)

    if response_text is None:
        # Remove the unanswered question from history
        conversation.messages.pop()
        return

    conversation.add_assistant(response_text)
    _render_response(response_text)

    # Check for suggested commands
    if registry is not None:
        commands = _extract_commands(response_text)
        if commands:
            _execute_with_approval(commands, registry, config, session_manager)


def register(registry):
    """Register the ai command, capturing registry ref for execute-with-approval."""

    def _handler(args, config, session_manager):
        cmd_ai(args, config, session_manager, registry=registry)

    registry.register("ai", _handler, "Ask AI about AWS")
