
import pyblish.api
from avalon import io


class IntegrateAvalonDatabase(pyblish.api.InstancePlugin):
    """寫入本次發佈的相關資料至資料庫
    """

    label = "寫入資料庫"
    order = pyblish.api.IntegratorOrder + 0.1

    targets = ["localhost"]

    def process(self, instance):

        context = instance.context

        if not all(result["success"] for result in context.data["results"]):
            self.log.warning("Atomicity not held, aborting.")
            return

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
        existed_version = io.find_one(filter)
        if existed_version is None:
            # Write version and representations to database
            version_id = self.write_database(instance,
                                             version,
                                             representations)
            instance.data["insertedVersionId"] = version_id

            # Update dependent
            self.update_dependent(instance, version_id)

        else:
            if context.data.get("_progressivePublishing"):
                if instance.data.get("_progressiveOutput") is None:
                    pass  # Not given any output, no progress change

                else:
                    self.log.info("Update version publish progress.")
                    # Update version document "data.time"
                    filter_ = {"_id": existed_version["_id"]}
                    update = {"$set": {"data.time": context.data["time"]}}
                    if "progress" in version["data"]:
                        # Update version document "progress.current"
                        progress = version["data"]["progress"]["current"]
                        update["$inc"] = {"data.progress.current": progress}
                    else:
                        pass  # progress == -1, no progress update needed.
                    io.update_many(filter_, update)

            else:
                self.log.info("Version existed, representation file has been "
                              "overwritten.")
                # Update version document "data.time"
                filter_ = {"_id": existed_version["_id"]}
                update = {"$set": {"data.time": context.data["time"]}}
                io.update_many(filter_, update)

                # Update representation documents "data"
                for representation in representations:
                    filter_ = {
                        "name": representation["name"],
                        "parent": existed_version["_id"],
                    }
                    update = {"$set": {"data": representation["data"]}}
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
