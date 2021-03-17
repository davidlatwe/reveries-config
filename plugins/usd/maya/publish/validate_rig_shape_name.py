import json

import pyblish.api
from reveries import plugins


class SelectMissing(plugins.MayaSelectInvalidInstanceAction):

    label = "Missing Hierarchy File"
    symptom = "missing"
    on = "processed"


class SelectInvalid(plugins.MayaSelectInvalidInstanceAction):

    label = "Invalid Shape Name"
    symptom = "invalid"
    on = "processed"


class _ValidateRigShapeName(pyblish.api.InstancePlugin):
    """Check shape name are same with model publish.
    """

    label = "Validate Shape Name"
    order = pyblish.api.ValidatorOrder + 0.132
    hosts = ["maya"]

    families = ["reveries.rig.skeleton"]

    actions = [
        pyblish.api.Category("選取"),
        SelectMissing,
        SelectInvalid,
    ]

    def process(self, instance):
        IS_INVALID = False

        invalid = self.get_invalid_missing(instance)
        if invalid:
            IS_INVALID = True
            self.log.error(
                "Missing Hierarchy File: "
                "Missing model hierarchy file from model publish.")

        invalid = self.get_invalid_invalid(instance)
        if invalid:
            IS_INVALID = True
            self.log.error(
                "Invalid Shape Name: "
                "Few shape name different with model publish.")

        if IS_INVALID:
            raise Exception("%s Shape Name Validation Failed." % instance)

    @classmethod
    def get_invalid_missing(cls, instance):
        from reveries.common import get_publish_files

        invalid = []
        model_subset_data = instance.data["model_subset_data"]["model_data"]

        for _grp, _data in model_subset_data.items():
            # Get model hierarchy file
            subset_id = _data["subset_id"]
            hierarchy_file = get_publish_files.get_files(
                subset_id, key='hierarchyFileName').get("USD", "")
            if not hierarchy_file:
                invalid.append(_grp)

        return invalid

    @classmethod
    def get_invalid_invalid(cls, instance):
        from reveries.maya import utils
        from reveries.common import get_publish_files

        invalid = []
        model_subset_data = instance.data["model_subset_data"]["model_data"]

        for _grp, _data in model_subset_data.items():
            # Get model hierarchy file
            subset_id = _data["subset_id"]
            hierarchy_file = get_publish_files.get_files(
                subset_id, key='hierarchyFileName').get("USD", "")
            if not hierarchy_file:
                continue

            with open(hierarchy_file, "r") as fp:
                model_data = json.load(fp)
            model_data_str = str(model_data)

            # Get current shape name
            hierarchy_obj = utils.HierarchyGetter()
            shapes = hierarchy_obj.get_shapes(_data["maya_long_path"])

            # Get invalid shapes
            for _shape in shapes:
                __shape = _shape.split("|")[-1].split(":")[-1]
                if __shape not in model_data_str:
                    invalid.append(_shape)
        return invalid
