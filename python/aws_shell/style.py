"""AWS-themed color scheme for the shell."""
from prompt_toolkit.styles import Style


def get_style():
    return Style.from_dict({
        # Prompt
        "prompt": "bold #ff9900",
        # Bottom toolbar
        "bottom-toolbar": "bg:#232f3e #ffffff",
        "bottom-toolbar.text": "#ff9900",
        # Completion menu
        "completion-menu.completion": "bg:#232f3e #ffffff",
        "completion-menu.completion.current": "bg:#ff9900 #000000",
        # Pygments token styles
        "pygments.keyword": "bold #ff9900",
        "pygments.name.function": "#66d9ef",
        "pygments.name.attribute": "#a6e22e",
        "pygments.literal.string": "#e6db74",
        "pygments.literal.number": "#ae81ff",
    })
