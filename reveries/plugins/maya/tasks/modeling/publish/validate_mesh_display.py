import pyblish.api


class ValidateShapeDisplay(pyblish.api.InstancePlugin):
    """All mesh must be a visible mesh

    This ensures all model shape node is not hidden.

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.4
    hosts = ["maya"]
    label = "Hidden Shape"

    def process(self, instance):
        from maya import cmds

        assert instance.data.get("meshes", None), (
            "Instance has no meshes!")

        invalid = list()

        display_attrs = {
            ".visibility": True,
            ".lodVisibility": True,
            ".template": False,
            ".hideOnPlayback": False,
            ".intermediateObject": False,
            ".hiddenInOutliner": False,
            ".ghosting": False
        }

        for mesh in instance.data['meshes']:
            # Ensure mesh shape is not hidden
            not_hidden = (
                all([cmds.getAttr(mesh + attr) is display_attrs[attr]
                    for attr in display_attrs.keys()])
            )

            if not not_hidden:
                invalid.append(mesh)

        if invalid:
            self.log.error(
                "'%s' has hidden shapes:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Hidden Shape> Failed." % instance)

        self.log.info("%s <Hidden Shape> Passed." % instance)
