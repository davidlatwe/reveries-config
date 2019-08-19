
import pyblish.api
from reveries.maya.utils import Identifier, get_id_status
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectMissing(MayaSelectInvalidInstanceAction):

    label = "Select ID Missing"


class ValidateAvalonUUIDProvided(pyblish.api.InstancePlugin):
    """Ensure upstream nodes have Avalon UUID
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Upstream Has Avalon UUID"
    families = [
        "reveries.animation",
        "reveries.pointcache",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectMissing,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        if instance.data.get("isDummy"):
            return []

        invalid = list()
        nodes = cmds.ls(instance.data["requireAvalonUUID"], long=True)
        for node in nodes:
            if get_id_status(node) == Identifier.Untracked:
                invalid.append(node)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)

        if invalid:
            raise Exception("Found node that has no ID assigned. "
                            "Require upstream to fix.")
