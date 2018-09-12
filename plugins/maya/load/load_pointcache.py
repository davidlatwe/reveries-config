
import os
import reveries.maya.lib
from reveries.plugins import message_box_warning
from reveries.maya.plugins import ReferenceLoader, ImportLoader


class PointCacheReferenceLoader(ReferenceLoader):

    label = "Reference PointCache"
    order = -10
    icon = "code-fork"
    color = "orange"

    families = [
        "reveries.model",
        "reveries.animation",
        "reveries.pointcache",
    ]

    representations = [
        "Alembic",
        "FBXCache",
    ]

    def process_reference(self, context, name, namespace, options):
        import maya.cmds as cmds

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

        return nodes

    def switch(self, container, representation):
        self.update(container, representation)


class PointCacheImportLoader(ImportLoader):

    label = "Import PointCache"
    order = -10
    icon = "code-fork"
    color = "orange"

    families = [
        "reveries.model",
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
        representation_name = representation["name"]

        entry_path = self.file_path(representation["data"]["entry_fname"])

        # Root group
        label = "{}:{}".format(namespace, name)
        root = cmds.group(name=label, empty=True)

        if representation_name == "GPUCache":
            # Create transform with shape
            transform_name = label + "_GPU"
            transform = cmds.createNode("transform", name=transform_name,
                                        parent=root)
            cache = cmds.createNode("gpuCache",
                                    parent=transform,
                                    name="{0}Shape".format(transform_name))

            # Set the cache filepath
            cmds.setAttr(cache + '.cacheFileName',
                         entry_path,
                         type="string")
            cmds.setAttr(cache + '.cacheGeomPath', "|", type="string")  # root

            # Lock parenting of the transform and cache
            cmds.lockNode([transform, cache], lock=True)

            nodes = [root, transform, cache]

        elif representation_name == "FBXCache":
            nodes = cmds.file(entry_path,
                              i=True,
                              namespace=namespace,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))
        else:
            raise RuntimeError("Unsupported format: {}\nThis is a bug."
                               "".format(representation_name))

        self[:] = nodes

    def update(self, container, representation):
        import maya.cmds as cmds

        representation_name = representation["name"]

        entry_path = self.file_path(representation["data"]["entry_fname"])

        # Update the cache
        members = cmds.sets(container['objectName'], query=True)

        if representation_name == "GPUCache":
            caches = cmds.ls(members, type="gpuCache", long=True)

            assert len(caches) == 1, "This is a bug"

            for cache in caches:
                cmds.setAttr(cache + ".cacheFileName",
                             self.entry_file,
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
