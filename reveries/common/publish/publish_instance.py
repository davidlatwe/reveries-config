import os
import shutil
import errno

from avalon import api, io
from avalon.vendor import filelink


class PublishInstance(object):
    def __init__(self):
        pass

    def publish(self, instance):

        context = instance.context

        if not all(result["success"] for result in context.data["results"]):
            print("Atomicity not held, aborting.")
            return

        # Integrate representations' to database
        print("Integrating representations to database ...")

        asset = instance.data["assetDoc"]
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
                    print("Update version publish progress.")
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
                print("Version existed, representation file has been "
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
        print("Registering version {} to database ...".format(version["name"]))

        if "pregeneratedVersionId" in instance.data:
            version["_id"] = instance.data["pregeneratedVersionId"]

        version_id = io.insert_one(version).inserted_id

        # Write representations
        print("Registering {} representations ...".format(len(representations)))

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


class IntegrateAvalonSubset(object):

    def __init__(self, *args, **kwargs):
        super(IntegrateAvalonSubset, self).__init__(*args, **kwargs)
        self.is_progressive = None
        self.progress = 0
        self.progress_output = None
        self.transfers = dict(files=list(),
                              hardlinks=list())

    def process(self, instance):

        # Atomicity
        #
        # Guarantee atomic publishes - each asset contains
        # an identical set of members.
        #     __
        #    /     o
        #   /       \
        #  |    o    |
        #   \       /
        #    o   __/
        #
        context = instance.context
        if not all(result["success"] for result in context.data["results"]):
            print("Atomicity not held, aborting.")
            return

        # Assemble data and create version, representations
        subset, version, representations = self.register(instance)

        instance.data["toDatabase"] = (subset, version, representations)

        # Integrate representations' files to shareable space
        print("Integrating representations to shareable space ...")
        self.integrate()

        return instance

    def register(self, instance):
        context = instance.context

        self.is_progressive = context.data.get("_progressivePublishing")
        self.progress = instance.data.get("_progressiveStep", -1)
        self.progress_output = instance.data.get("_progressiveOutput")

        # Assemble
        #
        #       |
        #       v
        #  --->   <----
        #       ^
        #       |
        #

        # Assemble families
        families = []
        current_families = instance.data.get("families", list())
        instance_family = instance.data.get("family", None)
        if instance_family is not None:
            families.append(instance_family)
        families += current_families

        # It's okay to create subset before integration complete if not exists
        subset = self.get_subset(instance, families)

        # get next version
        next_version = instance.data["versionNext"]
        version_data = self.create_version_data(context, instance)
        locations = [api.Session["AVALON_LOCATION"]]
        version = self.create_version(subset=subset,
                                      families=families,
                                      version_number=next_version,
                                      locations=locations,
                                      data=version_data)

        # Find the representations to transfer
        #
        representations = dict()
        _repr_data = dict()

        # Should not have any kind of check on files here, that should be done
        # by extractors, here only need to publish representation dirs.

        template_publish = instance.data["publishPathTemplate"]
        template_data = instance.data["publishPathTemplateData"]

        for key in sorted(instance.data.keys()):
            if not key.startswith("repr."):
                continue

            _, repr_name, entry = key.split(".", 2)

            if repr_name.startswith("_"):
                continue

            if repr_name not in representations:

                repr_data = dict()

                representation = {
                    "schema": "avalon-core:representation-2.0",
                    "type": "representation",
                    "parent": None,  # write this later
                    "name": repr_name,
                    "data": repr_data,
                }
                representations[repr_name] = representation
                _repr_data[repr_name] = repr_data

                src = instance.data["repr.%s._stage" % repr_name]
                dst = template_publish.format(representation=repr_name,
                                              **template_data)

                self.transfers["files"] += [
                    ("%s/%s" % (src, tail), "%s/%s" % (dst, tail)) for tail in
                    instance.data.get("repr.%s._files" % repr_name, [])
                ]
                self.transfers["hardlinks"] += [
                    ("%s/%s" % (src, tail), "%s/%s" % (dst, tail)) for tail in
                    instance.data.get("repr.%s._hardlinks" % repr_name, [])
                ]

            # Filtering representation data
            if not entry.startswith("_"):
                _repr_data[repr_name][entry] = instance.data[key]

        return subset, version, list(representations.values())

    def integrate(self):
        """Move the files

        Through `self.transfers`

        """
        if self.progress_output is None:
            progress_output = None
        else:
            progress_output = [
                os.path.abspath(
                    os.path.normpath(os.path.expandvars(file)))
                for file in self.progress_output
            ]

        # Write to disk
        #          _
        #         | |
        #        _| |_
        #    ____\   /
        #   |\    \ / \
        #   \ \    v   \
        #    \ \________.
        #     \|________|
        #

        transfered = list()

        for job in self.transfers:
            transfers = self.transfers[job]

            for src, dst in transfers:
                src = os.path.abspath(
                    os.path.normpath(os.path.expandvars(src)))
                dst = os.path.abspath(
                    os.path.normpath(os.path.expandvars(dst)))

                if self.is_progressive:
                    if os.path.isfile(dst):
                        continue
                    if (progress_output is not None
                            and src not in progress_output):
                        continue

                print("Copying {0}: {1} \n"
                      "          -> {2}".format(job, src, dst))

                if src == dst:
                    print("Source and destination are the same, "
                                   "will not copy.")
                    continue

                if dst in transfered:
                    # (TODO) Should not implement like this. This is a hot-fix.
                    print("File transfered: %s" % dst)
                    continue

                if job == "files":
                    self.copy_file(src, dst)
                if job == "hardlinks":
                    self.hardlink_file(src, dst)

                transfered.append(dst)

    def copy_file(self, src, dst):
        file_dir = os.path.dirname(dst)
        if not os.path.isdir(file_dir):
            os.makedirs(file_dir)

        try:
            shutil.copy2(src, dst)
        except OSError:
            msg = "An unexpected error occurred."
            print(msg)
            raise OSError(msg)

    def hardlink_file(self, src, dst):
        if os.path.isfile(dst):
            print("File exists, skip creating hardlink: %s" % dst)
            return

        dirname = os.path.dirname(dst)
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                print("An unexpected error occurred.")
                raise

        filelink.create(src, dst, filelink.HARDLINK)

    def get_subset(self, instance, families):

        asset_id = instance.data["assetDoc"]["_id"]

        subset = io.find_one({"type": "subset",
                              "parent": asset_id,
                              "name": instance.data["subset"]})

        if subset is None:
            subset_name = instance.data["subset"]
            print("Subset '%s' not found, creating.." % subset_name)

            subset = {
                "_id": io.ObjectId(),  # Pre-generate subset id
                "schema": "avalon-core:subset-3.0",
                "type": "subset",
                "name": subset_name,
                "data": {
                    "families": families,
                    "subsetGroup": instance.data.get("subsetGroup", ""),
                },
                "parent": asset_id,
                # "step_type": instance.data.get("step_type", "")
            }

            if instance.data.get("task", None):
                subset["data"]["task"] = instance.data["task"]

            if instance.data.get("step_type", None):
                subset["step_type"] = instance.data["step_type"]

        return subset

    def create_version(self,
                       subset,
                       families,
                       version_number,
                       locations,
                       data):
        """ Copy given source to destination

        Args:
            subset (dict): the registered subset of the asset
            families (list): instance's families
            version_number (int): the version number
            locations (list): the currently registered locations
            data (dict): version data

        Returns:
            dict: collection of data to create a version
        """
        # Imprint currently registered location
        version_locations = [location for location in locations if
                             location is not None]

        version = {
            "type": "version",
            "parent": subset["_id"],
            "name": version_number,
            "locations": version_locations,
            "data": data
        }

        if subset["schema"] == "avalon-core:subset-3.0":
            version["schema"] = "avalon-core:version-3.0"
        else:
            version["schema"] = "avalon-core:version-2.0"
            version["data"]["families"] = families

        if self.is_progressive and self.progress >= 0:
            try:
                start = int(data["startFrame"])
                end = int(data["endFrame"])
                step = int(data["step"])

            except KeyError:
                raise KeyError("Missing frame range data, this is a bug.")

            else:
                version["data"]["progress"] = {
                    "total": len(range(start, end + 1, step)),
                    "current": self.progress,
                }

        return version

    def create_version_data(self, context, instance):
        """Create the data collection for the version

        Args:
            context: the current context
            instance: the current instance being published

        Returns:
            dict: the required information with instance.data as key
        """
        # create relative source path for DB
        source = context.data["currentMaking"]
        source = source.replace(api.registered_root(), "{root}")
        source = source.replace("\\", "/")

        work_dir = api.Session.get("AVALON_WORKDIR")
        work_dir = work_dir.replace(api.registered_root(), "{root}")
        work_dir = work_dir.replace("\\", "/")

        version_data = {
            "time": context.data["time"],
            "author": context.data["user"],
            "task": api.Session.get("AVALON_TASK"),
            "source": source,
            "workDir": work_dir,
            "comment": context.data.get("comment"),
            "dependencies": instance.data.get("dependencies", dict()),
            "dependents": dict(),
        }

        # Include optional data if present in
        optionals = [
            "startFrame",
            "endFrame",
            "step",
            "handles",
            "hasUnversionedSurfaces",
            "deadlineJobId",
        ]
        for key in optionals:
            if key in instance.data:
                version_data[key] = instance.data[key]

        return version_data


def run(instance):
    integrater = IntegrateAvalonSubset()
    instance = integrater.process(instance)

    publisher = PublishInstance()
    publisher.publish(instance)
