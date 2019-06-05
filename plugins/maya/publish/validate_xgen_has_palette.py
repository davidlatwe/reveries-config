
import pyblish.api


class ValidateXGenHasPalette(pyblish.api.InstancePlugin):
    """Ensure there's palette node in XGen pyblish instance
    """

    order = pyblish.api.ValidatorOrder - 0.1
    hosts = ["maya"]
    label = "XGen Has Palette"
    families = [
        "reveries.xgen.legacy",
    ]

    def process(self, instance):
        if not instance.data["xgenPalettes"]:
            raise Exception("No XGen palette node collected.")
