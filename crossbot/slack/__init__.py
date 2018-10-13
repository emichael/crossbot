from .handler import Handler, SlashCommandRequest

def handle_slash_command(slash_command):
    """Convenience methods used to handle slash commands.

    Args:
        slash_command: str

    Returns:
        A Response object or None. (??)
    """

    handler = Handler()
    request = SlashCommandRequest(slash_command)

    return handler.handle_request(request)
