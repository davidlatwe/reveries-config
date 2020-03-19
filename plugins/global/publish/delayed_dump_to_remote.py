import os
import json
import pyblish.api
import avalon.api
from avalon import io
from avalon.vendor import toml
from reveries import lib


class DelayedDumpToRemote(pyblish.api.ContextPlugin):
    """Dump context with instances and delayed extractors to remote publish

    This plugin will dump context and instances that have unprocessed delayed
    extractors into TOML and JSON files for continuing the publish process in
    remote side.

    At the remote side, it should pick up the extractor dump file (JSON) and
    start extraction from there without re-run the publish from beginning.

    After the remote extraction complete, *filesys* publish should pick the
    context dump file (TOML) and start validating extracted files and publish
    them.

    """

    order = pyblish.api.ExtractorOrder + 0.491
    label = "Delayed Dump To Remote"

    EXTRACTOR_DUMP = "{package}/.extractor.json"
    INSTANCE_DUMP = "{version}/.instance.toml"
    CONTEXT_DUMP = "{filesys}/dumps/.context.{user}.{oid}.toml"

    def process(self, context):
        # Skip if any error occurred
        if not all(result["success"] for result in context.data["results"]):
            self.log.warning("Atomicity not held, aborting.")
            return

        instances = list()
        for instance in context:
            if not instance.data.get("publish", True):
                continue

            instances.append(instance)

        if not instances:
            return

        dump_id = str(io.ObjectId())
        dump_user = context.data["user"]

        # Dump instances
        dumps = dict()
        for instance in instances:
            extractors = list(instance.data["packager"].delayed_extractors())
            if not extractors:
                continue
            dump_path, dump = self.instance_dump(instance, extractors)
            dumps[instance.name] = (dump_path, dump)

            instance.data["dumpPath"] = dump_path

        if not dumps:
            self.log.info("Nothing to dump.")
            return

        # Get context dump path
        root = self.get_filesys_dir(context)
        outpath = self.CONTEXT_DUMP.format(filesys=root,
                                           user=dump_user,
                                           oid=dump_id)

        for dump_path, dump in dumps.values():
            dump["context"] = outpath

            with open(dump_path, "w") as file:
                toml.dump(dump, file)

        # Dump context
        self.log.info("Dumping context ..")

        dump = {
            "by": dump_user,
            "from": context.data["currentMaking"],
            "date": lib.avalon_id_timestamp(dump_id),
            "instances": [
                {
                    "id": instance.id,
                    "name": instance.name,
                    "asset": instance.data["asset"],
                    "family": instance.data["family"],
                    "families": instance.data.get("families", []),
                    "version": instance.data["versionNext"],
                    "instance": dumps[instance.name][0],
                    "childInstances": [
                        c.id for c in instance.data.get("childInstances", [])
                    ],
                }
                for instance in context
            ],
        }

        outdir = os.path.dirname(outpath)
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        with open(outpath, "w") as file:
            toml.dump(dump, file)

    def instance_dump(self, instance, extractors):
        self.log.info("Dumping instance %s .." % instance)

        packages = instance.data["packages"]
        instance.data["dumpedExtractors"] = list()

        # Dump extractors
        for extractor in extractors:

            repr = extractor["representation"]
            obj = extractor["obj"]
            func = extractor["func"]
            args = extractor["args"]
            kwargs = extractor["kwargs"]

            dump = {
                "representation": repr,
                "module": obj.__module__,
                "class": obj.__class__.__name__,
                "func": func.__name__,
                "args": args,
                "kwargs": kwargs,
            }

            pkg_dir = packages[repr]["packageDir"]
            outpath = self.EXTRACTOR_DUMP.format(package=pkg_dir)

            with open(outpath, "w") as file:
                json.dump(dump, file, indent=4)

            instance.data["dumpedExtractors"].append(outpath)

        # Dump instance
        dirpaths = list()
        for repr, repr_data in packages.items():
            dirpaths.append(repr_data["packageDir"])

        filepaths = list()
        filepaths += instance.data["files"]
        filepaths += instance.data["hardlinks"]

        dump = {
            "context": None,  # Wait for context dump
            "data": instance.data,
            "dirpaths": dirpaths,
            "filepaths": filepaths,
        }

        version_dir = instance.data["versionDir"]
        outpath = self.INSTANCE_DUMP.format(version=version_dir)
        outpath = outpath.replace("\\", "/")

        return outpath, dump

    def get_filesys_dir(self, context):
        APP = "filesys"

        project = context.data["projectDoc"]
        root = avalon.api.registered_root()

        template_work = project["config"]["template"]["work"]
        template_data = {
            "root": root,
            "project": avalon.Session["AVALON_PROJECT"],
            "silo": avalon.Session["AVALON_SILO"],
            "asset": avalon.Session["AVALON_ASSET"],
            "task": avalon.Session["AVALON_TASK"],
            "app": APP,
        }

        # (TODO) Run by action ?

        return template_work.format(**template_data)
