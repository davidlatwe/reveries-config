from maya import cmds

from .attrs import (
    attributes_gather,
    attributes_scatter,
)

from .utils import (
    create_vray_settings,
)

# Requirement, obviously
# Version: 3.52
cmds.loadPlugin('vrayformaya', quiet=True)


__all__ = (
    "attributes_gather",
    "attributes_scatter",
    "create_vray_settings",
)
