
import avalon.api
import avalon.maya
from avalon import io


# Cache for faster action filtering on GUI
cache = {
    "mainContainers": None,
    "loadedNamespaces": None,
}


class FixNamespaceUnique(avalon.api.InventoryAction):
    """Fix container to ensure namespace unique

    Artist may import scene themselve which contain loaded subsets, and
    create dupication.

    This action aim to resolve namespace duplication only, duplicated
    main containers is not responsible by this action.

    """

    label = "Fix Namespace Unique"
    icon = "wrench"
    color = "#F13A3A"
    order = -100

    @staticmethod
    def is_compatible(container):
        """Action will be visibile only if the selected container require this fix
        """
        from maya import cmds
        from avalon.maya.pipeline import AVALON_CONTAINERS

        if not container:
            return False

        if cache["mainContainers"] is None:
            cache["mainContainers"] = cmds.ls(AVALON_CONTAINERS[1:] + "*",
                                              recursive=True)
        if cache["loadedNamespaces"] is None:
            cache["loadedNamespaces"] = [cmds.getAttr(con + ".namespace")
                                         for con in avalon.maya.pipeline._ls()]

        main_containers = cache["mainContainers"]
        namespaces = cache["loadedNamespaces"]

        parents = cmds.listSets(object=container["objectName"]) or []
        # Must be a root container
        if any(main in parents for main in main_containers):
            if namespaces.count(container["namespace"]) > 1:
                return True
        return False

    def process(self, containers):
        from maya import cmds
        from reveries.maya import lib, pipeline
        from avalon.tools import sceneinventory

        cached_document = dict()

        def get_document(id):
            if id in cached_document:
                doc = cached_document[id]
            else:
                doc = io.find_one({"_id": io.ObjectId(id)})
                cached_document[id] = doc
            return doc

        for container in containers:
            namespace = container["namespace"]
            filter = {"id": "pyblish.avalon.container", "namespace": namespace}
            if len(lib.lsAttrs(filter)) == 1:
                # Namespace is unique
                continue

            # Create new namespace
            asset = get_document(container["assetId"])
            asset_name = asset["name"]

            subset = get_document(container["subsetId"])
            if subset["schema"] == "avalon-core:subset-3.0":
                family = subset["data"]["families"][0]
            else:
                version = get_document(container["versionId"])
                family = version["data"]["families"][0]
            family_name = family.split(".")[-1]

            new_namespace = pipeline.unique_root_namespace(
                asset_name=asset_name,
                family_name=family_name,
            )

            CON = container["objectName"]
            members = cmds.ls(cmds.sets(CON, query=True, nodesOnly=True),
                              long=True)
            reference_node = lib.get_highest_reference_node(members)

            if reference_node:
                filename = cmds.referenceQuery(reference_node, filename=True)
                cmds.file(filename, edit=True, namespace=new_namespace)
            else:
                cmds.namespace(add=new_namespace)

            for node in members:
                if not cmds.objExists(node):
                    continue
                if cmds.referenceQuery(node, isNodeReferenced=True):
                    continue
                if cmds.lockNode(node, query=True)[0]:
                    continue

                new = "|".join(p.replace(namespace[1:], new_namespace[1:], 1)
                               for p in node.split("|"))
                if node != new:
                    cmds.rename(node, new)

            cmds.setAttr(CON + ".namespace", new_namespace, type="string")
            container["namespace"] = new_namespace

        sceneinventory.app.window.refresh()
