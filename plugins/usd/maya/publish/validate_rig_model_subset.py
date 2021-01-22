
import pyblish.api


class ValidateRigModelSubset(pyblish.api.InstancePlugin):
    """Get model subset from Geometry group.

    """

    label = "Validate Model Subset Data"
    order = pyblish.api.ValidatorOrder + 0.13
    hosts = ["maya"]

    families = [
        # "reveries.rig",
        "reveries.rig.skeleton"
    ]

    def process(self, instance):
        import maya.cmds as cmds
        from reveries.maya.usd import rig_prim_export

        if not instance.data.get("publishUSD", True):
            return

        geometry_path = "|ROOT|Group|Geometry"
        if not cmds.objExists(geometry_path):
            raise RuntimeError(
                "{}: Get geometry group failed. It should be {}".format(
                    instance, geometry_path))

        validator = rig_prim_export.RigPrimValidation()
        model_subset_data = validator.get_model_subset_data()
        invalid_group = validator.get_invalid_group()
        model_data = {
            "model_data": model_subset_data,
            "invalid_group": invalid_group
        }

        if not validator.validation_result or not model_subset_data:
            for log in validator.validation_log:
                self.log.error(log)
            raise Exception("Model subset data validation failed.")

        if model_subset_data:
            instance.data["model_subset_data"] = model_data
            # instance.data["model_subset_data"] = model_subset_data
