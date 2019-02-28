
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Select Animated"


class ValidateContentNotAnimated(pyblish.api.InstancePlugin):
    """No animation allowed on any objects

    Should not have any animCurve connected to any object of the content,
    or components.

    """

    order = pyblish.api.ValidatorOrder + 0.1
    hosts = ["maya"]
    label = "No Animation"
    families = [
        "reveries.model",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        invalid = list()

        for node in cmds.ls(instance, long=True):
            if cmds.listConnections(node, source=True, type="animCurve"):
                invalid.append(node)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error("These nodes are not allowed: %s" % invalid)
            raise Exception("%s <Model Content> Failed." % instance)

        self.log.info("%s <Model Content> Passed." % instance)
