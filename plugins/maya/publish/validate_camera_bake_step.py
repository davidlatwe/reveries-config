import pyblish.api


class ValidateCameraBakeStep(pyblish.api.InstancePlugin):
    """Ensure camera bake step is a valid float
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Camera Bake Step"
    families = [
        "reveries.camera",
    ]

    def process(self, instance):
        bake_step = instance.data.get("bakeStep")
        if bake_step is None:
            self.log.warning("Using default bake step: 1.0")
            return

        self.log.info("Camera bake step: {}".format(bake_step))

        if bake_step <= 0.01:
            raise ValueError("Camera bake step can not less then 0.01")
