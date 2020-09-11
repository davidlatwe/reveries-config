import pyblish.api
from reveries import plugins


class ValidateIntermediateUSD(pyblish.api.InstancePlugin):
    """Transforms with a mesh must ever only contain a single mesh

    This ensures models only contain a single Non-Intermediate shape node."""

    order = pyblish.api.ValidatorOrder

    label = "Validate Intermediate Shape"
    hosts = ["maya"]
    families = [
        "reveries.model"
    ]

    actions = [
        pyblish.api.Category("Select"),
        plugins.MayaSelectInvalidInstanceAction,
    ]

    def process(self, instance):
        invalid = self.get_invalid(instance)

        if invalid:
            raise Exception("Below mesh has intermediate shape, please delete it:<br>{}".format(invalid))

    @classmethod
    def get_invalid(cls, instance):
        import pymel.core as pm

        invalid = []

        for _shape in pm.ls(type="mesh"):
            if _shape.hasAttr('intermediateObject'):
                if _shape.getAttr('intermediateObject'):
                    invalid.append(_shape.name())

        return invalid
