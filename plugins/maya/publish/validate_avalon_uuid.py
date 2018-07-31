
from collections import defaultdict
from maya import cmds
import pyblish.api

from reveries.maya.lib import AVALON_ID_ATTR_SHORT, set_avalon_uuid


class SelectInvalid(pyblish.api.Action):
    label = "Select Invalid"
    on = "failed"
    icon = "hand-o-up"

    def process(self, context, plugin):
        cmds.select(plugin.invalid)


class RepairInvalid(pyblish.api.Action):
    label = "Regenerate AvalonUUID"
    on = "failed"

    def process(self, context, plugin):
        for node in plugin.invalid:
            set_avalon_uuid(node, renew=True)


class ValidateAvalonUUID(pyblish.api.InstancePlugin):
    """All models ( mesh node's transfrom ) must have an UUID
    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Avalon UUID"
    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    invalid = []

    def process(self, instance):
        uuids = get_avalon_uuid(instance)

        self.invalid = uuids[None]
        if self.invalid:
            self.log.error(
                "'%s' Missing ID attribute on:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in self.invalid))
            )
            raise Exception("%s <Avalon UUID> Failed." % instance)

        self.log.info("%s <Avalon UUID> Passed." % instance)

        self.invalid = [n for _id, nds in uuids if len(nds) > 1 for n in nds]
        if self.invalid:
            self.log.error(
                "'%s' Duplicated IDs on:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in self.invalid))
            )
            raise Exception("%s <Avalon UUID> Failed." % instance)

        self.log.info("%s <Avalon UUID> Passed." % instance)


def get_avalon_uuid(instance):
    """
    Recoed every mesh's transform node's avalon uuid attribute
    """
    uuids = defaultdict(list)

    for node in instance:
        # Only check transforms with shapes that are meshes
        if not cmds.nodeType(node) == "transform":
            continue
        shapes = cmds.listRelatives(node, shapes=True, type="mesh") or []
        meshes = cmds.ls(shapes, type="mesh", ni=True)
        if not meshes:
            continue
        # get uuid
        try:
            uuid = cmds.getAttr(node + "." + AVALON_ID_ATTR_SHORT)
        except ValueError:
            uuid = None
        uuids[uuid].append(node)

    return uuids
