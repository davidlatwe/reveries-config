
import os
import logging
import shutil

import errno
import pyblish.api
from avalon import api, io


log = logging.getLogger(__name__)


class IntegrateAvalonSubset(pyblish.api.InstancePlugin):
    """Write to files and metadata, Resolve any dependency issues

    This plug-in exposes your data to others by encapsulating it
    into a new version.

    This plug-in resolves any paths which, if not updated might break
    the published file.

    The order of families is important, when working with lookdev you want to
    first publish the texture, update the texture paths in the nodes and then
    publish the shading network. Same goes for file dependent assets.

    """

    label = "Integrate Subset"
    order = pyblish.api.IntegratorOrder

    transfers = dict(packages=list(), auxiliaries=list())

    def process(self, instance):

        # Check Delegation
        #
        # Contractor completed long-run publish process
        delegated = instance.context.data.get("contractor_accepted")
        # Is delegating long-run publish process
        if instance.data.get("use_contractor") and not delegated:
            return

        # Assemble data and create version, representations
        version, representations = self.register(instance)

        # Integrate representations' files to shareable space
        self.log.info("Integrating representations to shareable space ...")
        self.integrate()

        # Write version and representations to database
        self.write_database(instance, version, representations)

    def register(self, instance):

        context = instance.context

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
        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        # Check packages
        #
        packages = instance.data.get("packages")

        if not packages:
            raise RuntimeError("No representation to publish.")

        stagingdir = instance.data.get("stagingDir")

        assert stagingdir, ("Incomplete instance \"%s\": "
                            "Missing reference to staging dir." % instance)

        # Assemble
        #
        #       |
        #       v
        #  --->   <----
        #       ^
        #       |
        #

        # It's okay to create subset before integration complete if not exists
        subset = self.get_subset(instance)

        # get next version
        next_version = instance.data["version_next"]
        version_data = self.create_version_data(context, instance)
        locations = [api.Session["AVALON_LOCATION"]]
        version = self.create_version(subset=subset,
                                      version_number=next_version,
                                      locations=locations,
                                      data=version_data)

        # Find the representations to transfer amongst the files
        # Each should be a single representation (as such, a single extension)
        #
        representations = []

        # `template` extracted from `ExtractPublishDir` plugin
        template_data = instance.data["template"][0]
        template_publish = instance.data["template"][1]

        # Should not have any kind of check on files here, that should be done
        # by extractors, here only need to publish representation dirs.

        for package, repr_data in packages.items():

            template_data["representation"] = package
            publish_path = template_publish.format(**template_data)

            src = os.path.join(stagingdir, package)
            dst = publish_path

            self.transfers["packages"].append([src, dst])

            representation = {
                "schema": "avalon-core:representation-2.0",
                "type": "representation",
                "parent": None,  # write this later
                "name": package,
                "data": repr_data,
                "dependencies": instance.data.get("dependencies", "").split(),
            }
            representations.append(representation)

        self.transfers["auxiliaries"] += instance.data["auxiliaries"]

        return version, representations

    def integrate(self):
        """Move the files

        Through `self.transfers`

        """

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

        for job in self.transfers:
            transfers = self.transfers[job]

            for src, dst in transfers:
                # normpath
                src = os.path.abspath(os.path.normpath(src))
                dst = os.path.abspath(os.path.normpath(dst))

                self.log.info("Copying {0}: {1} -> {2}".format(job, src, dst))
                if src == dst:
                    self.log.warning("Source and destination are the same, "
                                     "will not copy.")
                    continue

                if job == "packages":
                    self.copy_dir(src, dst)
                if job == "auxiliaries":
                    self.copy_file(src, dst)

    def copy_dir(self, src, dst):
        """ Copy given source to destination

        Arguments:
            src (str): the source dir which needs to be copied
            dst (str): the destination of the sourc dir
        Returns:
            None
        """
        try:
            shutil.copytree(src, dst)
        except OSError as e:
            if e.errno == errno.EEXIST:
                self.log.warning("Representation dir existed, this should not "
                                 "happen. Copy skipped.")
            else:
                self.log.critical("An unexpected error occurred.")
                raise

    def copy_file(self, src, dst):
        try:
            shutil.copyfile(src, dst)
        except OSError:
            self.log.critical("An unexpected error occurred.")
            raise

    def write_database(self, instance, version, representations):
        """Write version and representations to database

        Should write version documents until files collecting passed
        without error.

        """
        # Write version
        #
        self.log.info("Registering version {} to database ..."
                      "".format(version["name"]))
        version_id = io.insert_one(version).inserted_id

        # Write representations
        #
        self.log.info("Registering {} representations ..."
                      "".format(len(representations)))
        for representation in representations:
            representation["parent"] = version_id

        io.insert_many(representations)

    def get_subset(self, instance):

        asset_id = instance.data["asset_id"]

        subset = io.find_one({"type": "subset",
                              "parent": asset_id,
                              "name": instance.data["subset"]})

        if subset is None:
            subset_name = instance.data["subset"]
            self.log.info("Subset '%s' not found, creating.." % subset_name)

            _id = io.insert_one({
                "schema": "avalon-core:subset-2.0",
                "type": "subset",
                "name": subset_name,
                "data": {},
                "parent": asset_id
            }).inserted_id

            subset = io.find_one({"_id": _id})

        return subset

    def create_version(self, subset, version_number, locations, data=None):
        """ Copy given source to destination

        Args:
            subset (dict): the registered subset of the asset
            version_number (int): the version number
            locations (list): the currently registered locations

        Returns:
            dict: collection of data to create a version
        """
        # Imprint currently registered location
        version_locations = [location for location in locations if
                             location is not None]

        return {"schema": "avalon-core:version-2.0",
                "type": "version",
                "parent": subset["_id"],
                "name": version_number,
                "locations": version_locations,
                "data": data}

    def create_version_data(self, context, instance):
        """Create the data collection for the version

        Args:
            context: the current context
            instance: the current instance being published

        Returns:
            dict: the required information with instance.data as key
        """

        families = []
        current_families = instance.data.get("families", list())
        instance_family = instance.data.get("family", None)

        if instance_family is not None:
            families.append(instance_family)
        families += current_families

        # create relative source path for DB
        relative_path = os.path.relpath(context.data["currentFile"],
                                        api.registered_root())
        source = os.path.join("{root}", relative_path).replace("\\", "/")

        version_data = {"families": families,
                        "time": context.data["time"],
                        "author": context.data["user"],
                        "source": source,
                        "comment": context.data.get("comment")}

        # Include optional data if present in
        optionals = ["startFrame", "endFrame", "step", "handles"]
        for key in optionals:
            if key in instance.data:
                version_data[key] = instance.data[key]

        return version_data
