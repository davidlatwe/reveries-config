
import pyblish.api


class ValidateAtomsCrowdVariationStr(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Variation String"
    hosts = ["maya"]
    families = [
        "reveries.atomscrowd",
    ]

    def process(self, instance):
        variation_str = instance.data["variationStr"]

        try:
            variation = eval(variation_str)
        except SyntaxError:
            raise SyntaxError("Atoms variation data corrupted, "
                              "possible licensing issue.")

        if not next(iter(variation["agentTypes"])):
            self.log.warning("No variation loaded.")
