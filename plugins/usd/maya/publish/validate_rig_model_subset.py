
import pyblish.api


class ValidateRigModelSubset(pyblish.api.InstancePlugin):
    """Get model subset from Geometry group

    """

    label = "Rig Check Model Subset"
    order = pyblish.api.ValidatorOrder + 0.13
    hosts = ["maya"]

    families = ["reveries.rig"]

    def process(self, instance):
        import maya.cmds as cmds
        from reveries.maya import lib, pipeline

        if not instance.data.get("publishUSD", True):
            return

        geometry_path = "|ROOT|Group|Geometry"
        if not cmds.objExists(geometry_path):
            raise RuntimeError(
                "{}: Get geometry group failed. It should be {}".format(
                    instance, geometry_path))

        children = cmds.listRelatives(geometry_path, children=True)
        model_subset_data = {}
        for _group in children:
            namespace = _group.split(":")[0] \
                if len(_group.split(":")) > 1 else None
            if namespace:
                try:
                    container = pipeline.get_container_from_namespace(namespace)
                except Exception as e:
                    print("{}: Get container failed: {}".format(_group, e))
                    continue

                if cmds.getAttr("{}.loader".format(container)) == "ModelLoader":
                    asset_id = cmds.getAttr("{}.assetId".format(container))
                    subset_id = cmds.getAttr("{}.subsetId".format(container))
                    version_id = cmds.getAttr("{}.versionId".format(container))
                    model_subset_data[_group] = {
                        "asset_id": asset_id,
                        "subset_id": subset_id,
                        "version_id": version_id
                    }
        if model_subset_data:
            instance.data["model_subset_data"] = model_subset_data
