
import pyblish.api
import maya.cmds as cmds
import xgenm as xg
import reveries.maya.xgen.legacy as xgen


class ValidateXGenMapsInDESC(pyblish.api.InstancePlugin):
    """All maps should be saved in folder under ${DESC}

    All map file path should be like:
        `${DESC}/something/map`

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "XGen Maps In ${DESC}"
    families = [
        "reveries.xgen.legacy",
    ]

    @classmethod
    def get_invalid(cls, instance):

        invalid = list()

        cmds.filePathEditor(refresh=True)
        resloved = (cmds.filePathEditor(query=True,
                                        listFiles="",
                                        withAttribute=True,
                                        byType="xgmDescription",
                                        unresolved=False) or [])[1::2]

        for map_attr in resloved:

            attr, palette, description, obj = xgen.parse_objects(map_attr)

            if description not in instance.data["xgenDescriptions"]:
                continue

            expr_maps = xgen.parse_expr_maps(attr, palette, description, obj)
            if not expr_maps:
                # Not expression type
                files = [xg.getAttr(attr, palette, description, obj)]
            else:
                files = [m["file"] for m in expr_maps]

            if any(not path.startswith("${DESC}") for path in files):
                invalid.append((palette, description, obj, attr))

        return list(set(invalid))

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("These attribute map does not saved under "
                            "${DESC}.")
