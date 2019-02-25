
import pyblish.api
import reveries.maya.xgen.legacy as xgen


class ValidateXGenNoMissingMap(pyblish.api.InstancePlugin):
    """No missing map in descriptions

    All path must be resloved.

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "XGen No Missing Map"
    families = [
        "reveries.xgen.legacy",
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        invalid = list()

        cmds.filePathEditor(refresh=True)
        missing = (cmds.filePathEditor(query=True,
                                       listFiles="",
                                       withAttribute=True,
                                       byType="xgmDescription",
                                       unresolved=True) or [])[1::2]

        for map_attr in missing:
            attr, palette, description, obj = xgen.parse_objects(map_attr)

            if description in instance.data["xgenDescriptions"]:
                invalid.append((palette, description, obj, attr))

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("Has missing map.")
