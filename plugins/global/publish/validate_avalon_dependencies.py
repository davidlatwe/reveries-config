
import pyblish.api
import avalon.io


class ValidateAvalonDependencies(pyblish.api.InstancePlugin):
    """Ensure dependencies is acyclic
    """

    label = "Validate Dependencies"
    order = pyblish.api.ValidatorOrder

    def process(self, instance):
        if "dependencies" not in instance.data:
            raise Exception("Dependencies not collected, this is a bug.")

        dependencies = instance.data["dependencies"]
        asset_id = instance.data["assetDoc"]["_id"]
        subset = avalon.io.find_one({"type": "subset",
                                     "parent": asset_id,
                                     "name": instance.data["subset"]})

        if subset is None:
            # Never been published
            return

        # Ensure Acyclic
        acyclic = self.is_acyclic(dependencies, subset["_id"])
        if not acyclic:
            raise Exception("Cyclic dependency detected, this is invalid.")

    def is_acyclic(self, dependencies, current_subset_id):
        for version_id in dependencies:

            version_id = avalon.io.ObjectId(version_id)
            version = avalon.io.find_one({"_id": version_id})

            if version is None:
                continue

            if version["parent"] == current_subset_id:
                return False

            dependencies = version["data"]["dependencies"]
            if not self.is_acyclic(dependencies, current_subset_id):
                return False

        return True
