import pyblish.api


class ValidateTransformDisplay(pyblish.api.InstancePlugin):
    """All transform node must be visible

    This ensures all transform node is not hidden.

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.45
    hosts = ["maya"]
    label = "Hidden Transform"

    def process(self, instance):
        from maya import cmds

        invalid = list()

        display_attrs = {
            ".visibility": True,
            ".lodVisibility": True,
            ".template": False,
            ".hideOnPlayback": False,
            ".hiddenInOutliner": False,
            ".ghosting": False
        }

        for transform in instance.data['transforms']:
            # Ensure transform shape is not hidden
            not_hidden = (
                all([cmds.getAttr(transform + attr) is display_attrs[attr]
                    for attr in display_attrs.keys()])
            )

            if not not_hidden:
                invalid.append(transform)

        if invalid:
            self.log.error(
                "'%s' has hidden transforms:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("<Hidden Transform> Failed.")

        self.log.info("%s <Hidden Transform> Passed." % instance)
