import pyblish.api
from maya import cmds


class ValidateTranformFreezed(pyblish.api.InstancePlugin):
    """ All transform must be freezed

    Checking `translate`, `rotate`, `scale` and `shear` are all freezed

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.45
    hosts = ["maya"]
    label = "Model Transform"

    def process(self, instance):

        invalid = list()

        transform_attrs = {
            ".translate": [(0.0, 0.0, 0.0)],
            ".rotate": [(0.0, 0.0, 0.0)],
            ".scale": [(1.0, 1.0, 1.0)],
            ".shear": [(0.0, 0.0, 0.0)]
        }

        for transform in instance.data['transforms']:
            has_freeze = (
                all([cmds.getAttr(transform + attr) == transform_attrs[attr]
                    for attr in transform_attrs.keys()])
            )

            if not has_freeze:
                invalid.append(transform)

        if invalid:
            self.log.error(
                "'%s' has not freezed transforms:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Model Transform> Failed." % instance)

        self.log.info("%s <Model Transform> Passed." % instance)
