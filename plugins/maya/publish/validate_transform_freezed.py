
import pyblish.api
from maya import cmds


class ValidateTranformFreezed(pyblish.api.InstancePlugin):
    """ All transform must be freezed

    Checking `translate`, `rotate`, `scale` and `shear` are all freezed

    """

    order = pyblish.api.ValidatorOrder + 0.45
    hosts = ["maya"]
    label = "Transform Freezed"
    families = [
        "reveries.model",
        "reveries.rig",
    ]

    @staticmethod
    def get_invalid(instance):

        invalid = dict()

        transform_attrs = {
            ".translate": [(0.0, 0.0, 0.0)],
            ".rotate": [(0.0, 0.0, 0.0)],
            ".scale": [(1.0, 1.0, 1.0)],
            ".shear": [(0.0, 0.0, 0.0)]
        }

        for node in instance:
            if not cmds.nodeType(node) == "transform":
                continue

            not_freezed = dict()

            for attr, values in transform_attrs.items():
                node_values = cmds.getAttr(node + attr)
                if not node_values == values:
                    not_freezed[attr] = node_values

            if not_freezed:
                invalid[node] = not_freezed

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            self.log.error(
                "{!r} has not freezed transform:".format(instance)
            )
            for node, not_freezed in invalid.items():
                print(node)
                for attr, values in not_freezed.items():
                    print("{0}: {1}".format(attr, values))

            raise ValueError("%s <Transform Freezed> Failed." % instance)

        self.log.info("%s <Transform Freezed> Passed." % instance)
