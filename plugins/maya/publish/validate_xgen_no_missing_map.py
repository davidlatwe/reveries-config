
import pyblish.api


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
        import reveries.maya.xgen.legacy as xgen

        invalid = list()

        cmds.filePathEditor(refresh=True)
        missing = (cmds.filePathEditor(query=True,
                                       listFiles="",
                                       withAttribute=True,
                                       byType="xgmDescription",
                                       unresolved=True) or [])[1::2]

        for map_attr in missing:
            path, parents = xgen.parse_map_path(map_attr)
            palette, description, obj, attr, index = parents

            if description in instance.data["xgenDescriptions"]:
                if obj in xgen.list_fx_modules(description, activated=False):
                    # Ignore if not active
                    continue

                if xgen.is_modifier_under_bake_manager(palette,
                                                       description,
                                                       obj):
                    # Ignore if obj is a modifier and is under an active bake
                    # groom manager
                    cls.log.warning("Map missing but baked, ignored.")
                    cls.log.warning(path)
                    continue

                invalid.append((parents, path))

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("Has missing map.")
