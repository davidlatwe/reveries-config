
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
        asset_id = instance.data["asset_doc"]["_id"]

        # Ensure Acyclic
        acyclic = self.is_acyclic(dependencies, asset_id)
        if not acyclic:
            raise Exception("Cyclic dependency detected, this is invalid.")

    def is_acyclic(self, dependencies, current_asset_id):
        for dependency in dependencies:
            if dependency["asset"]["_id"] == current_asset_id:
                return False

            version_id = dependency["version"]["_id"]
            version = avalon.io.find_one({"_id": version_id})
            dependencies = version["data"]["dependencies"]

            if not self.is_acyclic(dependencies, current_asset_id):
                return False

        return True
