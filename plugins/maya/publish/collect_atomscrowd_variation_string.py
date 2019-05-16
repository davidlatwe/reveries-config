
import pyblish.api


class CollectAtomsCrowdVariationStr(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.CollectorOrder + 0.21
    label = "AtomsCrowd Variation String"
    hosts = ["maya"]
    families = [
        "reveries.atomscrowd",
    ]

    def process(self, instance):
        if not instance.data["AtomsNodes"]:
            self.log.info("No AtomsNode found, skip variation collecting.")

        host_bridge = self.get_atoms_host_bridge()

        variation_str = host_bridge.get_variation_string()
        instance.data["variationStr"] = variation_str

    def get_atoms_host_bridge(self):
        from AtomsMaya.hostbridge.atomsnode import MayaAtomsNodeHostBridge
        return MayaAtomsNodeHostBridge
