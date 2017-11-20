import sys
import logging
from avalon import api

self = sys.modules[__name__]
self._menu = api.Session["AVALON_LABEL"] + "menu"

log = logging.getLogger(__name__)


def install():
    pass


def uninstall():
    pass
