
import os
import contextlib

import pyblish.api
# from reveries.plugins import DelegatablePackageExtractor
from reveries.plugins import PackageExtractor


class ExtractPointCache(PackageExtractor):
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

    targets = ["localhost"]

    def extract(self):
        from reveries.maya import capsule
        from maya import cmds

        if self.data.get("staticCache"):
            self.start_frame = cmds.currentTime(query=True)
            self.end_frame = cmds.currentTime(query=True)
        else:
            context_data = self.context.data
            self.start_frame = context_data.get("startFrame")
            self.end_frame = context_data.get("endFrame")

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_refresh(),
            capsule.evaluation("off"),
            capsule.maintained_selection(),
        ):
            super(ExtractPointCache, self).extract()

    def add_range_data(self):
        if not self.data.get("staticCache"):
            self.data["startFrame"] = self.start_frame
            self.data["endFrame"] = self.end_frame

    def extract_Alembic(self, packager):
        from reveries.maya import io, lib, capsule
        from maya import cmds

        packager.skip_stage()

        entry_file = packager.file_name("abc")
        package_path = packager.create_package()
        entry_path = os.path.join(package_path, entry_file)

        euler_filter = self.data.get("eulerFilter", False)

        root = self.data["outCache"]

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

                root += cmds.listRelatives(root,
                                           allDescendents=True,
                                           fullPath=True,
                                           noIntermediate=True) or []
                cmds.select(root, replace=True, noExpand=True)

                io.export_alembic(
                    entry_path,
                    self.start_frame,
                    self.end_frame,
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

        # (NOTE) Deprecated
        # io.wrap_abc(entry_path, [(cache_file, "ROOT")])

        packager.add_data({"entryFileName": entry_file})
        self.add_range_data()

    def extract_FBXCache(self, packager):
        from reveries.maya import io
        from maya import cmds

        cmds.select(self.data["outCache"], replace=True)

        packager.skip_stage()

        entry_file = packager.file_name("ma")
        cache_file = packager.file_name("fbx")
        package_path = packager.create_package()
        entry_path = os.path.join(package_path, entry_file)
        cache_path = os.path.join(package_path, cache_file)

        with io.export_fbx_set_pointcache("FBXCacheSET"):
            io.export_fbx(cache_path)

        io.wrap_fbx(entry_path, [(cache_file, "ROOT")])

        packager.add_data({"entryFileName": entry_file})
        self.add_range_data()

    def extract_GPUCache(self, packager):
        from reveries import lib
        from reveries.maya import io, capsule
        from maya import cmds

        packager.skip_stage()

        # Collect root nodes
        assemblies = set()
        for node in self.data["outCache"]:
            assemblies.add("|" + node[1:].split("|", 1)[0])
        assemblies = list(assemblies)

        # Collect all parent nodes
        out_hierarchy = set()
        for node in self.data["outCache"]:
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

        # Export
        cmds.select(assemblies, replace=True, noExpand=True)

        entry_file = packager.file_name("ma")
        cache_file = packager.file_name("abc")
        package_path = packager.create_package()
        entry_path = os.path.join(package_path, entry_file)
        cache_path = os.path.join(package_path, cache_file)

        with contextlib.nested(
            capsule.attribute_values(attr_values),
            # Mute animated visibility channels
            capsule.attribute_mute(list(attr_values.keys())),
        ):
            io.export_gpu(cache_path, self.start_frame, self.end_frame)
            io.wrap_gpu(entry_path, [(cache_file, "ROOT")])

        packager.add_data({"entryFileName": entry_file})
        self.add_range_data()
