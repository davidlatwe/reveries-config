
import pyblish.api
from avalon import io


class IntegrateAvalonDatabase(pyblish.api.InstancePlugin):
    """Write to database
    """

    label = "Integrate Database"
    order = pyblish.api.IntegratorOrder + 0.1

    def process(self, instance):

        context = instance.context

        # Check Delegation
        #
        # Contractor completed long-run publish process
        delegated = context.data.get("contractorAccepted")
        # Is delegating long-run publish process
        if instance.data.get("useContractor") and not delegated:
            return

        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        # Integrate representations' to database
        self.log.info("Integrating representations to database ...")

        asset = context.data["assetDoc"]
        subset, version, representations = instance.data["toDatabase"]

        # Write subset if not exists
        filter = {"parent": asset["_id"], "name": subset["name"]}
        if io.find_one(filter) is None:
            io.insert_one(subset)

        # Write version if not exists
        filter = {"parent": subset["_id"], "name": version["name"]}
        if io.find_one(filter) is None:
            # Write version and representations to database
            version_id = self.write_database(instance,
                                             version,
                                             representations)
            instance.data["insertedVersionId"] = version_id

            # Update dependent
            self.update_dependent(instance, version_id)

        else:
            self.log.info("Version existed, representation file has been "
                          "overwritten.")
            filter_ = {"_id": version["_id"]}
            update = {"$set": {"data.time": context.data["time"]}}
            io.update_many(filter_, update)

    def write_database(self, instance, version, representations):
        """Write version and representations to database

        Should write version documents until files collecting passed
        without error.

        """
        # Write version
        #
        self.log.info("Registering version {} to database ..."
                      "".format(version["name"]))

        if "pregeneratedVersionId" in instance.data:
            version["_id"] = instance.data["pregeneratedVersionId"]

        version_id = io.insert_one(version).inserted_id

        # Write representations
        #
        self.log.info("Registering {} representations ..."
                      "".format(len(representations)))
        for representation in representations:
            representation["parent"] = version_id

        io.insert_many(representations)

        return version_id

    def update_dependent(self, instance, version_id):

        version_id = str(version_id)
        field = "data.dependents." + version_id

        for version_id_, data in instance.data["dependencies"].items():
            filter_ = {"_id": io.ObjectId(version_id_)}
            update = {"$set": {field: {"count": data["count"]}}}
            io.update_many(filter_, update)
