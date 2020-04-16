
import pyblish.api
from reveries import plugins


class ValidateLookUVChooser(pyblish.api.InstancePlugin):

    order = pyblish.api.ValidatorOrder
    label = "UV Chooser and UV Sets Has Id"
    hosts = ["maya"]
    families = [
        "reveries.look",
    ]
    actions = [
        plugins.MayaSelectInvalidInstanceAction,
    ]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception("Some uvChooser node or UVSet from "
                            "mesh that does not have AvalonId.")

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds
        from reveries.maya import utils

        invalid = list()

        for chooser in cmds.ls(instance, type="uvChooser"):
            if not utils.get_id(chooser):
                invalid.append(chooser)

            for node in cmds.listConnections(chooser + ".uvSets",
                                             source=True,
                                             destination=False,
                                             shapes=False) or []:
                if not utils.get_id(node):
                    invalid.append(chooser)
                    break

        return invalid
