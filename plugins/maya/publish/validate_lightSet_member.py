
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class ValidateLightSetMember(pyblish.api.InstancePlugin):
    """Validate lightSet nodes' node type

    Only these types of node allow to be exists in LightSet:
        * light
        * transform
        * nurbsCurve
        * constraint

    """

    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    label = "Validate LightSet Member"
    families = [
        "reveries.lightset",
    ]
    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidInstanceAction,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        VALID_TYPES = [
            "transform",
            "nurbsCurve",
            "constraint",
        ]

        invalid = set()

        lights = set(cmds.ls(instance.data["lights"], long=True))
        dag_nodes = cmds.ls(instance.data["dagMembers"],
                            long=True,
                            noIntermediate=True)
        valid_nodes = set(cmds.ls(dag_nodes, type=VALID_TYPES, long=True))

        invalid = set(dag_nodes) - valid_nodes - lights

        return list(invalid)

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error("'%s' has invalid nodes:" % instance)
            for node in invalid:
                self.log.error(node)

            raise Exception("%s <LightSet Member> Failed." % instance)
