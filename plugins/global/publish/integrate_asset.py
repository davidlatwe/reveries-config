
import pyblish.api


class IntegrateAvalonAsset(pyblish.api.InstancePlugin):
    """Write to files and metadata

    This plug-in exposes your data to others by encapsulating it
    into a new version.

    """

    label = "Publish Content"
    order = pyblish.api.IntegratorOrder
    families = ["*"]

    def process(self, instance):
        import os
        import errno
        import shutil
        from pprint import pformat

        from avalon import api, io
        from avalon.vendor import filelink

        # Required environment variables
        PROJECT = api.Session["AVALON_PROJECT"]
        ASSET = instance.data.get("asset") or api.Session["AVALON_ASSET"]
        SILO = api.Session["AVALON_SILO"]
        LOCATION = api.Session["AVALON_LOCATION"]

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

        # Assemble
        #
        #       |
        #       v
        #  --->   <----
        #       ^
        #       |
        #
        stagingdir = instance.data.get("stagingDir")
        assert stagingdir, ("Incomplete instance \"%s\": "
                            "Missing reference to staging area." % instance)

        self.log.debug("Establishing staging directory @ %s" % stagingdir)

        project = io.find_one({"type": "project"})
        asset = io.find_one({"name": ASSET})

        assert all([project, asset]), ("Could not find current project or "
                                       "asset '%s'" % ASSET)

        subset = io.find_one({"type": "subset",
                              "parent": asset["_id"],
                              "name": instance.data["subset"]})

        if subset is None:
            subset_name = instance.data["subset"]
            self.log.info("Subset '%s' not found, creating.." % subset_name)

            _id = io.insert_one({
                "schema": "avalon-core:subset-2.0",
                "type": "subset",
                "name": subset_name,
                "data": {},
                "parent": asset["_id"]
            }).inserted_id

            subset = io.find_one({"_id": _id})

        latest_version = io.find_one({"type": "version",
                                      "parent": subset["_id"]},
                                     {"name": True},
                                     sort=[("name", -1)])

        next_version = 1
        if latest_version is not None:
            next_version += latest_version["name"]

        self.log.debug("Next version: %i" % next_version)

        version = {
            "schema": "avalon-core:version-2.0",
            "type": "version",
            "parent": subset["_id"],
            "name": next_version,
            "locations": [LOCATION] if LOCATION else [],
            "data": {
                "families": (
                    instance.data.get("families", list()) +
                    [instance.data["family"]]
                ),

                # Enable overriding with current information from instance
                "time": instance.data.get("time", context.data["time"]),
                "author": instance.data.get("user", context.data["user"]),
                "source": instance.data.get(
                    "source", context.data["currentFile"]).replace(
                    api.registered_root(), "{root}"
                ).replace("\\", "/"),

                "comment": context.data.get("comment")
            }
        }

        self.log.debug("Creating version: %s" % pformat(version))
        version_id = io.insert_one(version).inserted_id

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
        template_data = {
            "root": api.registered_root(),
            "project": PROJECT,
            "silo": SILO,
            "asset": ASSET,
            "subset": subset["name"],
            "version": version["name"],
        }

        template_publish = project["config"]["template"]["publish"]

        if "output" not in instance.data:
            instance.data["output"] = list()

        def copy(src, dst):
            dirname = os.path.dirname(dst)
            try:
                os.makedirs(dirname)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    pass
                else:
                    self.log.critical("An unexpected error occurred.")
                    raise

            try:
                filelink.create(src, dst)
                self.log.info("Linking %s -> %s" % (src, dst))
            except Exception:
                # Revert to a normal copy
                # TODO(marcus): Once filelink is proven stable,
                # improve upon or remove this fallback.
                shutil.copy(src, dst)
                self.log.info("Linking failed, copying %s -> %s"
                              % (src, dst))

        for _ in instance.data["files"]:

            # Collection
            #   _______
            #  |______|\
            # |      |\|
            # |       ||
            # |       ||
            # |       ||
            # |_______|
            #
            if isinstance(_, list):
                collection = _

                # Assert that each member has identical suffix
                _, ext = os.path.splitext(collection[0])
                assert all(ext == os.path.splitext(name)[1]
                           for name in collection), (
                    "Files had varying suffixes, this is a bug"
                )

                template_data["representation"] = ext[1:]

                for fname in collection:
                    src = os.path.join(stagingdir, fname)
                    dst = os.path.join(
                        template_publish.format(**template_data),
                        fname
                    )

                    copy(src, dst)

                    instance.data["output"].append(dst)

            else:
                # Single file
                #  _______
                # |      |\
                # |       |
                # |       |
                # |       |
                # |_______|
                #
                fname = _

                _, ext = os.path.splitext(fname)

                template_data["representation"] = ext[1:]

                src = os.path.join(stagingdir, fname)
                dst = template_publish.format(**template_data)

                copy(src, dst)

                instance.data["output"].append(dst)

            representation = {
                "schema": "avalon-core:representation-2.0",
                "type": "representation",
                "parent": version_id,
                "name": template_data["representation"],
                "data": {},
                "dependencies": instance.data.get("dependencies", "").split(),

                # Imprint shortcut to context for performance reasons.
                "context": {
                    "project": PROJECT,
                    "asset": ASSET,
                    "silo": SILO,
                    "subset": subset["name"],
                    "version": version["name"],
                    "representation": template_data["representation"]
                }
            }

            io.insert_one(representation)

        context.data["published_version"] = str(version_id)

        self.log.info("Successfully integrated \"%s\" to \"%s\"" % (
            instance, dst))
