
import os

import avalon.api

import reveries.maya.lib
from reveries.plugins import message_box_warning
from reveries.maya.plugins import ReferenceLoader, ImportLoader


class PointCacheReferenceLoader(ReferenceLoader, avalon.api.Loader):

    label = "Reference PointCache"
    order = -10
    icon = "flash"
    color = "orange"

    hosts = ["maya"]

    families = [
        "reveries.animation",
        "reveries.pointcache",
    ]

    representations = [
        "Alembic",
        "FBXCache",
        "GPUCache",
    ]

    def process_reference(self, context, name, namespace, options):
        import maya.cmds as cmds
        from reveries.maya.lib import get_highest_in_hierarchy

        representation = context["representation"]

        entry_path = self.file_path(representation["data"]["entry_fname"])

        group_name = "{}:{}".format(namespace, name)
        nodes = cmds.file(entry_path,
                          namespace=namespace,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName=group_name,
                          reference=True,
                          lockReference=True,
                          returnNewNodes=True)

        reveries.maya.lib.lock_transform(group_name)
        self[:] = nodes

        transforms = cmds.ls(nodes, type="transform", long=True)
        self.interface = get_highest_in_hierarchy(transforms)

        return group_name

    def switch(self, container, representation):
        self.update(container, representation)


class PointCacheImportLoader(ImportLoader, avalon.api.Loader):

    label = "Import PointCache"
    order = -10
    icon = "flash"
    color = "orange"

    hosts = ["maya"]

    families = [
        "reveries.animation",
        "reveries.pointcache",
    ]

    representations = [
        "GPUCache",
        "FBXCache",
    ]

    def process_import(self, context, name, namespace, options):
        import maya.cmds as cmds

        representation = context["representation"]

        entry_path = self.file_path(representation["data"]["entry_fname"])

        group_name = "{}:{}".format(namespace, name)
        nodes = cmds.file(entry_path,
                          i=True,
                          namespace=namespace,
                          returnNewNodes=True,
                          groupReference=True,
                          groupName=group_name)

        reveries.maya.lib.lock_transform(group_name)
        self[:] = nodes

        return group_name

    def update(self, container, representation):
        import maya.cmds as cmds
        import avalon.api

        representation_name = representation["name"]

        self.package_path = avalon.api.get_representation_path(representation)

        entry_path = self.file_path(representation["data"]["entry_fname"])

        # Update the cache
        members = cmds.sets(container['objectName'], query=True)

        if representation_name == "GPUCache":
            caches = cmds.ls(members, type="gpuCache", long=True)

            assert len(caches) == 1, "This is a bug"

            for cache in caches:
                cmds.setAttr(cache + ".cacheFileName",
                             entry_path,
                             type="string")

        elif representation_name == "FBXCache":
            geo_cache_dir = entry_path[:-4] + "_fpc"
            in_coming_cache_count = len([f for f in os.listdir(geo_cache_dir)
                                         if f.endswith(".mcx")])

            caches = cmds.ls(members, type="cacheFile", long=True)

            if not in_coming_cache_count == len(caches):
                title = "FBXCache Update Warning"
                message = ("The FBXCache geometry count does not match with "
                           "current asset.\nUpdate will proceed, but the "
                           "result may incomplete.\n\nBetter to remove "
                           "and re-import, or use referencing.")
                self.log.Warning(message)
                res = message_box_warning(title, message, optional=True)

                if not res:
                    return

            for cache in caches:
                cmds.setAttr(cache + ".cachePath",
                             self.repr_dir,
                             type="string")

        else:
            raise RuntimeError("This is a bug.")

        cmds.setAttr(container["objectName"] + ".representation",
                     str(representation["_id"]),
                     type="string")

    def remove(self, container):
        import maya.cmds as cmds

        members = cmds.sets(container['objectName'], query=True)
        cmds.lockNode(members, lock=False)
        cmds.delete([container['objectName']] + members)

        # Clean up the namespace
        try:
            cmds.namespace(removeNamespace=container['namespace'],
                           deleteNamespaceContent=True)
        except RuntimeError:
            pass
