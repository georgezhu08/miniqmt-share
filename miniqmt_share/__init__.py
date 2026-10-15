"""
MiniQMT Share (miniqmt-share) - Transparent remote proxy for xtquant library

Allows using xtquant on macOS/Linux by proxying calls to a Windows server.
"""

__version__ = "1.1.3"
__author__ = "Jason Hu"

from .client import (
    XtQuantRemote,
    connect,
    disconnect,
    get_client,
    xtdata,
    xttrader,
    xttype,
    xtview,
    ConnectionError,
    AuthenticationError,
    CallbackError,
    set_logging,
    enable_logging,
    disable_logging,
    is_logging_enabled,
    set_quiet_mode,
)

__all__ = [
    "XtQuantRemote",
    "connect",
    "disconnect",
    "get_client",
    "xtdata",
    "xttrader",
    "xttype",
    "xtview",
    "ConnectionError",
    "AuthenticationError",
    "CallbackError",
    "set_logging",
    "enable_logging",
    "disable_logging",
    "is_logging_enabled",
    "set_quiet_mode",
]