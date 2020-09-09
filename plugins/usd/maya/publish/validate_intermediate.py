import pyblish.api


class ValidateIntermediateUSD(pyblish.api.InstancePlugin):
    """Transforms with a mesh must ever only contain a single mesh

    This ensures models only contain a single Non-Intermediate shape node."""

    order = pyblish.api.ValidatorOrder

    label = "Validate Intermediate Value"
    hosts = ["maya"]
    families = [
        "reveries.model"
    ]

    def process(self, instance):
        import pymel.core as pm

        invalid = []

        for _shape in pm.ls(type="mesh"):
            if _shape.hasAttr('intermediateObject'):
                if _shape.getAttr('intermediateObject'):
                    invalid.append(_shape.name())

        if invalid:
            raise Exception("Below mesh has intermediate shape, please delete it:<br>{}".format(invalid))
