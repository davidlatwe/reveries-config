
import pyblish.api
import avalon.io


class ValidateAvalonDependencies(pyblish.api.InstancePlugin):
    """Ensure subset dependencies is acyclic

    Subset should not depend on the previous version of itself.

    Normaly, a subset may depend (reference) on other subset.

    For example:
        * `rigLow` version 1 is depending `modelLow` version 5

    It's also possible that a subset is depending on an older
    version of itself. Which will create a dependency loop.

    For example:
        * `modelLow` version 4 is depending `modelLow` version 2

    This may or may not be a problem in practice, but better not
    to be that way.

    """

    label = "Avalon Dependencies Acyclic"
    order = pyblish.api.ValidatorOrder + 0.4

    # These families are allowed to publish the works that were build
    # upon the previous version of themself.
    IGNORE = [
        "reveries.pointcache",
    ]

    def process(self, instance):
        if "dependencies" not in instance.data:
            raise Exception("Dependencies not collected, this is a bug.")

        if instance.data["family"] in self.IGNORE:
            return

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
                # Current subset has been found in dependency chain.
                # This is not okay. :(
                return False

            dependencies = version["data"]["dependencies"]
            if not self.is_acyclic(dependencies, current_subset_id):
                return False

        return True
