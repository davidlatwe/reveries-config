
import pyblish.api


class ValidateRenderStereoPairs(pyblish.api.InstancePlugin):
    """Stereo should be rendering with both side set to renderable

    Both side of stereo camera should be renderable.

    """

    label = "Render Stereo Pairs"
    order = pyblish.api.ValidatorOrder + 0.2
    hosts = ["maya"]
    families = [
        "reveries.renderlayer",
    ]

    def process(self, instance):
        stereo_pairs = instance.data.get("stereo")
        if stereo_pairs is None:
            return

        if stereo_pairs[0] is None:
            self.log.error("Left side of stereo cam is not renderable.")

        if stereo_pairs[1] is None:
            self.log.error("Right side of stereo cam is not renderable.")

        if not all(stereo_pairs):
            raise Exception("Invalid stereo camera render settings.")
