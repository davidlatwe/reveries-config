import avalon

import pyblish.api


class ValidatePointCacheUSDOutputs(pyblish.api.InstancePlugin):
    """Validate asset already published usd."""

    order = pyblish.api.ValidatorOrder + 0.492

    label = "Validate PointCache USD Outputs"
    hosts = ["maya"]
    families = [
        "reveries.pointcache.usd",
        "reveries.pointcache.child.usd"
    ]

    def process(self, instance):
        from reveries.maya.usd import get_export_hierarchy

        if instance.data.get("isDummy"):
            return

        self.out_cache = instance.data.get("usd_outCache")

        # Check MOD group long name
        export_node, root_usd_path = get_export_hierarchy(self.out_cache[0])
        if not export_node or not root_usd_path:
            raise Exception("Can't get correct model hierarchy, "
                            "please check with TD.")

        # r'|..|..|HanMaleA_rig_02:HanMaleA_model_01_:Geometry'
        instance.data["export_node"] = export_node
        # r'/rigDefault/ROOT/Group/Geometry/modelDefault/ROOT'
        instance.data["root_usd_path"] = root_usd_path
