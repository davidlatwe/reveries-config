
import os
import contextlib

import pyblish.api
from reveries import plugins


class ExtractPointCache(plugins.PackageExtractor):
    """
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract PointCache"
    families = [
        "reveries.pointcache",
    ]

    representations = [
        "Alembic",
        "FBXCache",
        "GPUCache",
    ]

    def extract(self, instance):
        from reveries.maya import capsule
        from maya import cmds

        if instance.data.get("staticCache"):
            self.start_frame = cmds.currentTime(query=True)
            self.end_frame = cmds.currentTime(query=True)
        else:
            context_data = instance.context.data
            self.start_frame = context_data.get("startFrame")
            self.end_frame = context_data.get("endFrame")

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_refresh(),
            capsule.evaluation("off"),
            capsule.maintained_selection(),
        ):
            super(ExtractPointCache, self).extract(instance)

    def add_range_data(self, instance):
        if not instance.data.get("staticCache"):
            instance.data["startFrame"] = self.start_frame
            instance.data["endFrame"] = self.end_frame

    def extract_Alembic(self, instance):

        packager = instance.data["packager"]
        packager.skip_stage()
        package_path = packager.create_package()

        entry_file = packager.file_name("abc")
        entry_path = os.path.join(package_path, entry_file)

        packager.add_data({"entryFileName": entry_file})
        self.add_range_data(instance)

        euler_filter = instance.data.get("eulerFilter", False)

        root = instance.data["outCache"]

        self.export_alembic(root, entry_path, euler_filter)

    @plugins.delay_extract
    def export_alembic(self, root, entry_path, start, end, euler_filter):
        from reveries.maya import io, lib, capsule
        from maya import cmds

        with capsule.maintained_selection():
            # Selection may change if there are duplicate named nodes and
            # require instancing them to resolve

            with capsule.delete_after() as delete_bin:

                # (NOTE) We need to check any duplicate named nodes, or
                #        error will raised during Alembic export.
                result = lib.ls_duplicated_name(root)
                duplicated = [n for m in result.values() for n in m]
                if duplicated:
                    # Duplicate it so we could have a unique named new node
                    unique_named = list()
                    for node in duplicated:
                        new_nodes = cmds.duplicate(node,
                                                   inputConnections=True,
                                                   renameChildren=True)
                        new_nodes = cmds.ls(new_nodes, long=True)
                        unique_named.append(new_nodes[0])
                        # New nodes will be deleted after the export
                        delete_bin.extend(new_nodes)

                    # Replace duplicat named nodes with unique named
                    root = list(set(root) - set(duplicated)) + unique_named

                for node in set(root):
                    # (NOTE) If a descendent is instanced, it will appear only
                    #        once on the list returned.
                    root += cmds.listRelatives(node,
                                               allDescendents=True,
                                               fullPath=True,
                                               noIntermediate=True) or []
                root = list(set(root))
                cmds.select(root, replace=True, noExpand=True)

                io.export_alembic(
                    entry_path,
                    start,
                    end,
                    selection=True,
                    renderableOnly=True,
                    writeVisibility=True,
                    writeCreases=True,
                    worldSpace=True,
                    eulerFilter=euler_filter,
                    attr=[
                        lib.AVALON_ID_ATTR_LONG,
                    ],
                    attrPrefix=[
                        "ai",  # Write out Arnold attributes
                    ],
                )

    def extract_FBXCache(self, instance):
        packager = instance.data["packager"]
        packager.skip_stage()
        package_path = packager.create_package()

        entry_file = packager.file_name("ma")
        cache_file = packager.file_name("fbx")
        entry_path = os.path.join(package_path, entry_file)
        cache_path = os.path.join(package_path, cache_file)

        packager.add_data({"entryFileName": entry_file})
        self.add_range_data(instance)

        # (TODO) Make namespace preserving optional on GUI
        keep_namespace = instance.data.get("keepNamespace", False)
        out_cache = instance.data["outCache"]

        self.export_fbx(entry_path,
                        cache_path,
                        cache_file,
                        out_cache,
                        keep_namespace)

    @plugins.delay_extract
    def export_fbx(self,
                   entry_path,
                   cache_path,
                   cache_file,
                   out_cache,
                   keep_namespace):
        from reveries.maya import io, capsule
        from maya import cmds

        cmds.select(out_cache, replace=True)

        with capsule.StripNamespace([] if keep_namespace else out_cache):
            with io.export_fbx_set_pointcache("FBXCacheSET"):
                io.export_fbx(cache_path)

            io.wrap_fbx(entry_path, [(cache_file, "ROOT")])

    def extract_GPUCache(self, instance):
        from reveries import lib
        from maya import cmds

        packager = instance.data["packager"]
        packager.skip_stage()
        package_path = packager.create_package()

        entry_file = packager.file_name("ma")
        cache_file = packager.file_name("abc")
        entry_path = os.path.join(package_path, entry_file)
        cache_path = os.path.join(package_path, cache_file)

        packager.add_data({"entryFileName": entry_file})
        self.add_range_data(instance)

        # Collect root nodes
        assemblies = set()
        for node in instance.data["outCache"]:
            assemblies.add("|" + node[1:].split("|", 1)[0])
        assemblies = list(assemblies)

        # Collect all parent nodes
        out_hierarchy = set()
        for node in instance.data["outCache"]:
            out_hierarchy.add(node)
            out_hierarchy.update(lib.iter_uri(node, "|"))

        # Hide unwanted nodes (nodes that were not parents)
        attr_values = dict()
        for node in cmds.listRelatives(assemblies,
                                       allDescendents=True,
                                       type="transform",
                                       fullPath=True) or []:
            if node not in out_hierarchy:
                attr = node + ".visibility"

                locked = cmds.getAttr(attr, lock=True)
                has_connections = cmds.listConnections(attr,
                                                       source=True,
                                                       destination=False)
                if locked or has_connections:
                    continue

                attr_values[attr] = False

        self.export_gpu(entry_path,
                        cache_path,
                        cache_file,
                        self.start_frame,
                        self.end_frame,
                        assemblies,
                        attr_values)

    @plugins.delay_extract
    def export_gpu(self,
                   entry_path,
                   cache_path,
                   cache_file,
                   start,
                   end,
                   assemblies,
                   attr_values):
        from reveries.maya import io, capsule
        from maya import cmds
        # Export
        cmds.select(assemblies, replace=True, noExpand=True)

        with contextlib.nested(
            capsule.attribute_values(attr_values),
            # Mute animated visibility channels
            capsule.attribute_mute(list(attr_values.keys())),
        ):
            io.export_gpu(cache_path, start, end)
            io.wrap_gpu(entry_path, [(cache_file, "ROOT")])
