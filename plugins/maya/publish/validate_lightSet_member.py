
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

        if invalid:
            if "aiMeshLight" in instance.data["lightsByType"]:
                for lit in instance.data["lightsByType"]["aiMeshLight"]:
                    mesh = cmds.listConnections(lit + ".inMesh", shapes=True)
                    invalid.difference_update(cmds.ls(mesh, long=True))

        if invalid:
            # Opt-in shader emission as light
            for node in list(invalid):
                shadings = cmds.listConnections(node,
                                                type="shadingEngine",
                                                source=False,
                                                destination=True) or []
                if not len(shadings) == 1:
                    continue

                shaders = cmds.listConnections(shadings[0] + ".surfaceShader",
                                               type="aiStandardSurface",
                                               source=True,
                                               destination=False) or []
                if not len(shaders) == 1:
                    continue

                emission = cmds.listConnections(shaders[0] + ".emissionColor",
                                                source=True,
                                                destination=False) or []
                if emission:
                    invalid.remove(node)

        return list(invalid)

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error("'%s' has invalid nodes:" % instance)
            for node in invalid:
                self.log.error(node)

            raise Exception("%s <LightSet Member> Failed." % instance)
