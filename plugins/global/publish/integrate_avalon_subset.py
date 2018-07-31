
import os
import logging
import shutil

import errno
import pyblish.api
from avalon import api, io

from reveries.pipeline import PENDING_SUFFIX


log = logging.getLogger(__name__)


class IntegrateAvalonSubset(pyblish.api.InstancePlugin):
    """Write to files and metadata, Resolve any dependency issies

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

    delegating = False
    delegated = False

    def process(self, instance):

        # Check Delegation
        #
        # Contractor completed long-run publish process
        self.delegated = instance.context.data.get("contractor_accepted")
        # Delegating long-run publish process
        self.delegating = (bool(instance.data.get("use_contractor")) and
                           not self.delegated)

        self.log.debug("Delegating: {}".format(self.delegating))
        self.log.debug("Delegated: {}".format(self.delegated))

        if self.delegating and self.delegated:
            raise RuntimeError("Flag `delegating` and `delegated` can not "
                               "both be True, this is a bug.")

        # Assemble data and create version, representations
        version, representations = self.register(instance)

        # Integrate representations' files to shareable space
        if not self.delegating:
            self.log.info("Integrating representations to shareable space ...")
            self.integrate(instance)

        # Write version and representations to database
        self.write_database(instance, version, representations)

    def version_bumpable(self):
        # `version_bump` will remain False if:
        # `delegating is False and delegated is True`
        #
        bumpable = False
        if self.delegating or not any([self.delegating, self.delegated]):
            bumpable = True

        return bumpable

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

        # Check files
        #
        all_files = instance.data.get("files")

        if not all_files:
            raise RuntimeError("No files to publish.")

        stagingdir = instance.data.get("stagingDir")
        assert stagingdir, ("Incomplete instance \"%s\": "
                            "Missing reference to staging dir." % instance)

        if "transfers" not in instance.data:
            instance.data["transfers"] = list()

        # Assemble
        #
        #       |
        #       v
        #  --->   <----
        #       ^
        #       |
        #
        subset = self.get_subset(instance)

        if self.version_bumpable():
            # get next version

            version_data = self.create_version_data(context, instance)

            locations = [api.Session["AVALON_LOCATION"]]
            next_version = instance.data["version_next"]
            version = self.create_version(subset=subset,
                                          version_number=next_version,
                                          locations=locations,
                                          data=version_data)

        else:
            self.log.info("Publish contractor updating version ...")
            # Retrive exact version
            version = io.find_one({"_id": instance.data["version_id"]})

            if version is None:
                raise RuntimeError("No verison found, this is a bug.")

        # Find the representations to transfer amongst the files
        # Each should be a single representation (as such, a single extension)
        #
        representations = []

        template_data = instance.data["template"][0]
        template_publish = instance.data["template"][1]

        for files in all_files:

            # Collection
            #   _______
            #  |______|\
            # |      |\|
            # |       ||
            # |       ||
            # |       ||
            # |_______|
            #
            if isinstance(files, list):
                collection = files
                # Assert that each member has identical suffix
                _, ext = os.path.splitext(collection[0])
                assert all(ext == os.path.splitext(name)[1]
                           for name in collection), (
                    "Files had varying suffixes, this is a bug"
                )

                assert not any(os.path.isabs(name) for name in collection)

                template_data["representation"] = ext[1:]
                publish_path = template_publish.format(**template_data)

                for fname in collection:

                    src = os.path.join(stagingdir, fname)
                    dst = os.path.join(publish_path, fname)

                    instance.data["transfers"].append([src, dst])

            else:
                # Single file
                #  _______
                # |      |\
                # |       |
                # |       |
                # |       |
                # |_______|
                #
                fname = files
                assert not os.path.isabs(fname)
                _, ext = os.path.splitext(fname)

                template_data["representation"] = ext[1:]
                publish_path = template_publish.format(**template_data)

                src = os.path.join(stagingdir, fname)
                dst = publish_path

                instance.data["transfers"].append([src, dst])

            representation = {
                "schema": "avalon-core:representation-2.0",
                "type": "representation",
                "parent": None,  # write this later
                "name": ext[1:],
                "data": {},
                "dependencies": instance.data.get("dependencies", "").split(),
            }
            representations.append(representation)

        return version, representations

    def write_database(self, instance, version, representations):
        """Write version and representations to database

        Should write version documents until files collecting passed
        without error.

        """
        # Write version
        #
        if self.version_bumpable():
            self.log.debug("Inserting version to database ...")
            version_id = io.insert_one(version).inserted_id
        else:
            version_id = version["_id"]

        # Write representations
        #
        action_name = "Delegating" if self.delegating else "Registering"
        self.log.info("{0} {1} representations ..."
                      "".format(action_name, len(representations)))

        if not self.delegated:
            for representation in representations:
                representation["parent"] = version_id
            io.insert_many(representations)
            instance.data["version_id"] = version_id

        else:
            for representation in representations:
                representation["parent"] = version_id
                name = representation["name"] + PENDING_SUFFIX
                io.replace_one({"type": "representation",
                                "parent": version_id,
                                "name": name},
                               representation)

    def integrate(self, instance):
        """Move the files

        Through `instance.data["transfers"]`

        Args:
            instance: the instance to integrate
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

        transfers = instance.data["transfers"]

        for src, dst in transfers:
            # normpath
            src = os.path.abspath(os.path.normpath(src))
            dst = os.path.abspath(os.path.normpath(dst))
            # Skip same file.
            # `src` and `dst` might be the same by directly write into
            # publish area for some reason during extraction.
            if os.path.normpath(src) == os.path.normpath(dst):
                continue

            self.log.info("Copying file .. {} -> {}".format(src, dst))
            self.copy_file(src, dst)

    def copy_file(self, src, dst):
        """ Copy given source to destination

        Arguments:
            src (str): the source file which needs to be copied
            dst (str): the destination of the sourc file
        Returns:
            None
        """

        dirname = os.path.dirname(dst)
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                self.log.critical("An unexpected error occurred.")
                raise

        shutil.copy(src, dst)

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
