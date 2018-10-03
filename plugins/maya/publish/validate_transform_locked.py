
import pyblish.api
from maya import cmds

from reveries.plugins import RepairInstanceAction
from reveries.maya.plugins import MayaSelectInvalidAction


class SelectInvalid(MayaSelectInvalidAction):

    label = "Select Unlocked"


class RepairInvalid(RepairInstanceAction):

    label = "Lock Transforms"


class ValidateTranformLocked(pyblish.api.InstancePlugin):
    """ All transforms that are not exposed must be locked

    Locking all transforms' keyable attributes.

    """

    order = pyblish.api.ValidatorOrder + 0.49
    hosts = ["maya"]
    label = "Transform Locked"
    families = [
        "reveries.rig",
    ]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    @staticmethod
    def get_invalid(instance):

        invalid = list()

        transforms = cmds.ls(instance, type="transform")

        exposed = cmds.sets("ControlSet", query=True) or []
        unexposed = set(transforms).difference(exposed)

        for node in unexposed:
            for attr in cmds.listAttr(node, keyable=True) or []:
                if not cmds.getAttr(node + "." + attr, lock=True):
                    invalid.append(node)
                    break

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            self.log.error(
                "{!r} has not locked transform:".format(instance.name)
            )
            for node in invalid:
                self.log.error(node)

            raise ValueError("%s <Transform Locked> Failed." % instance.name)

    @classmethod
    def fix(cls, instance):
        invalid = cls.get_invalid(instance)

        for node in invalid:
            for attr in cmds.listAttr(node, keyable=True):
                cmds.setAttr(node + "." + attr, lock=True)
