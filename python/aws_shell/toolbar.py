"""Bottom toolbar for the shell prompt."""
from prompt_toolkit.formatted_text import HTML


def get_toolbar(config, session_manager):
    account_id = session_manager.get_account_id_cached()
    profile = config.profile
    region = config.region
    output_fmt = config.output_format

    return HTML(
        f"  <b>Profile:</b> {profile}  |  "
        f"<b>Region:</b> {region}  |  "
        f"<b>Account:</b> {account_id}  |  "
        f"<b>Output:</b> {output_fmt}"
    )
