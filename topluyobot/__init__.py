"""
Topluyo Bot Python kütüphanesi
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Topluyo platformu için WebSocket tabanlı bot istemcisi.

Örnek:
    >>> from topluyobot import TopluyoBOT
    >>> bot = TopluyoBOT("TOKEN")
    >>>
    >>> @bot.on("message")
    >>> def handler(data):
    ...     print(data)
    >>>
    >>> bot.run()
"""

from .bot import (
    TopluyoBOT,
    BotMessage,
    PostAddMessage,
    PostMentionMessage,
    PostBumoteMessage,
    MessageSendMessage,
    GroupJoinMessage,
    GroupLeaveMessage,
    GroupKickMessage,
    TurboTransferMessage,
)

__version__ = "1.0.0"
__author__ = "Topluyo"
__all__ = [
    "TopluyoBOT",
    "BotMessage",
    "PostAddMessage",
    "PostMentionMessage",
    "PostBumoteMessage",
    "MessageSendMessage",
    "GroupJoinMessage",
    "GroupLeaveMessage",
    "GroupKickMessage",
    "TurboTransferMessage",
]
