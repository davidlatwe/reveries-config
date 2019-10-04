
import os
import shutil

import errno
import pyblish.api
from avalon import api, io
from avalon.vendor import filelink


class IntegrateAvalonSubset(pyblish.api.InstancePlugin):
    """Write to files and metadata, Resolve any dependency issues

    This plug-in exposes your data to others by encapsulating it
    into a new version.

    This plug-in resolves any paths which, if not updated might break
    the published file.

    The order of families is important, when working with lookdev you want to
    first publish the texture, update the texture paths in the nodes and then
    publish the shading network. Same goes for file dependent assets.

    (NOTE) No database write happens here, only file transfer.

    """

    label = "Integrate Subset"
    order = pyblish.api.IntegratorOrder

    def process(self, instance):

        self.transfers = dict(packages=list(),
                              files=list(),
                              hardlinks=list())

        # Check Delegation
        #
        # Contractor completed long-run publish process
        delegated = instance.context.data.get("contractorAccepted")
        # Is delegating long-run publish process
        if instance.data.get("useContractor") and not delegated:
            return

        # Assemble data and create version, representations
        subset, version, representations = self.register(instance)

        instance.data["toDatabase"] = (subset, version, representations)

        # Integrate representations' files to shareable space
        self.log.info("Integrating representations to shareable space ...")
        self.integrate()

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

        # Find the representations to transfer amongst the files
        # Each should be a single representation (as such, a single extension)
        #
        representations = []

        versioner = instance.data["versioner"]

        # Should not have any kind of check on files here, that should be done
        # by extractors, here only need to publish representation dirs.

        for package, repr_data in packages.items():

            publish_path = versioner.representation_dir(package)

            representation = {
                "schema": "avalon-core:representation-2.0",
                "type": "representation",
                "parent": None,  # write this later
                "name": package,
                "data": repr_data,
            }
            representations.append(representation)

            if instance.data.get("bareStaging"):
                src = stagingdir
            else:
                src = os.path.join(stagingdir, package)

            dst = publish_path

            self.transfers["packages"].append([src, dst])

        self.transfers["files"] += instance.data["files"]
        self.transfers["hardlinks"] += instance.data["hardlinks"]

        return subset, version, representations

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

        transfered = list()

        for job in self.transfers:
            transfers = self.transfers[job]

            for src, dst in transfers:
                # normpath
                # self.log.debug("Src. Before: {!r}".format(src))
                # self.log.debug("Dst. Before: {!r}".format(dst))

                src = os.path.abspath(
                    os.path.normpath(os.path.expandvars(src)))
                dst = os.path.abspath(
                    os.path.normpath(os.path.expandvars(dst)))

                self.log.debug("Src: {!r}".format(src))
                self.log.debug("Dst: {!r}".format(dst))

                self.log.info("Copying {0}: {1} -> {2}".format(job, src, dst))
                if src == dst:
                    self.log.debug("Source and destination are the same, "
                                   "will not copy.")
                    continue

                if dst in transfered:
                    # (TODO) Should not implement like this. This is a hot-fix.
                    self.log.warning("File transfered: %s" % dst)
                    continue

                if job == "packages":
                    self.copy_dir(src, dst)
                if job == "files":
                    self.copy_file(src, dst)
                if job == "hardlinks":
                    self.hardlink_file(src, dst)

                transfered.append(dst)

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
                msg = ("Representation dir existed, this should "
                       "not happen. Copy aborted.")
            else:
                msg = "An unexpected error occurred."

            self.log.critical(msg)
            raise OSError(msg)

    def copy_file(self, src, dst):
        file_dir = os.path.dirname(dst)
        if not os.path.isdir(file_dir):
            os.makedirs(file_dir)

        try:
            shutil.copy2(src, dst)
        except OSError:
            msg = "An unexpected error occurred."
            self.log.critical(msg)
            raise OSError(msg)

    def hardlink_file(self, src, dst):

        dirname = os.path.dirname(dst)
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                self.log.critical("An unexpected error occurred.")
                raise

        filelink.create(src, dst, filelink.HARDLINK)

    def get_subset(self, instance, families):

        asset_id = instance.context.data["assetDoc"]["_id"]

        subset = io.find_one({"type": "subset",
                              "parent": asset_id,
                              "name": instance.data["subset"]})

        if subset is None:
            subset_name = instance.data["subset"]
            self.log.info("Subset '%s' not found, creating.." % subset_name)

            subset = {
                "_id": io.ObjectId(),  # Pre-generate subset id
                "schema": "avalon-core:subset-3.0",
                "type": "subset",
                "name": subset_name,
                "data": {
                    "families": families,
                },
                "parent": asset_id,
            }

        return subset

    def create_version(self,
                       subset,
                       families,
                       version_number,
                       locations,
                       data=None):
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
        ]
        for key in optionals:
            if key in instance.data:
                version_data[key] = instance.data[key]

        return version_data
