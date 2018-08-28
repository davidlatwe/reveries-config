
from collections import defaultdict
from maya import cmds
import pyblish.api

from reveries.maya.lib import AVALON_ID_ATTR_SHORT, set_avalon_uuid
from reveries.plugins import RepairInstanceAction
from reveries.maya.plugins import MayaSelectInvalidAction


class SelectMissing(MayaSelectInvalidAction):

    label = "Select ID Missing"
    symptom = "missing"


class SelectDuplicated(MayaSelectInvalidAction):

    label = "Select ID Duplicated"
    symptom = "duplicated"


class RepairInvalid(RepairInstanceAction):

    label = "Regenerate AvalonUUID"


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


class ValidateAvalonUUID(pyblish.api.InstancePlugin):
    """All models ( mesh node's transfrom ) must have an UUID
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Avalon UUID"
    actions = [
        pyblish.api.Category("Select"),
        SelectMissing,
        SelectDuplicated,
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    families = [
        "reveries.model",
        "reveries.look",
    ]

    @staticmethod
    def get_invalid_missing(instance, uuids=None):

        if uuids is None:
            uuids = get_avalon_uuid(instance)

        invalid = uuids[None]

        return invalid

    @staticmethod
    def get_invalid_duplicated(instance, uuids=None):

        if uuids is None:
            uuids = get_avalon_uuid(instance)

        invalid = [n for _id, nds in uuids.items()
                   if len(nds) > 1 for n in nds]

        return invalid

    def process(self, instance):

        uuids_dict = get_avalon_uuid(instance)

        invalid = self.get_invalid_missing(instance, uuids_dict)
        if invalid:
            self.log.error(
                "'%s' Missing ID attribute on:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Avalon UUID> Failed." % instance)

        invalid = self.get_invalid_duplicated(instance, uuids_dict)
        if invalid:
            self.log.error(
                "'%s' Duplicated IDs on:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Avalon UUID> Failed." % instance)

        self.log.info("%s <Avalon UUID> Passed." % instance)

    @classmethod
    def fix(cls, instance):
        invalid = (cls.get_invalid_missing(instance) +
                   cls.get_invalid_duplicated(instance))
        for node in invalid:
            set_avalon_uuid(node, renew=True)
