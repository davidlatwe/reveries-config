import avalon.io
import avalon.api
from avalon.io import ObjectId


class SwitchUSDToABC(avalon.api.InventoryAction):
    """Switch USD stage to alembic

    """
    label = "Switch USD to Alembic"
    icon = "wrench"
    color = "#00a2ff"
    order = -10

    @staticmethod
    def is_compatible(container):
        if container["loader"] in ["USDSetdressLoader"]:
            return True

        return False

    def process(self, containers):
        from maya import cmds, mel
        from reveries.maya.pipeline import update_container
        from reveries.common import get_publish_files
        from reveries.common import path_resolver

        container = containers[0]
        container_node = container["objectName"]

        # Get alembic file path
        subset_id = container["subsetId"]
        version_num = container["version"]

        abc_files = get_publish_files.get_files(
            subset_id, version=version_num).get("Alembic", [])
        if not abc_files:
            print("Cannot found alembic file in this version.")
            return
        entry_path = abc_files[0]

        # Import alembic file
        self._load_maya_plugin()
        old_assemblies = cmds.ls(assemblies=True)
        cmds.AbcImport(entry_path, mode="import")

        # Edit hierarchy
        subset_group = container["subsetGroup"]

        new_assemblies = list(
            set(cmds.ls(assemblies=True)) - set(old_assemblies)
        )
        if not new_assemblies:
            print("Alembic file is empty: {}".format(entry_path))
            return
        cmds.sets(new_assemblies, addElement=container_node)
        for obj in new_assemblies:
            cmds.parent(obj, subset_group)
        cmds.select(cl=True)

        # Update container
        parents = avalon.io.parenthood(
            {"parent": ObjectId(container["versionId"])}
        )
        version, subset, asset, _ = parents
        resolver_obj = path_resolver.PathResolver(file_path=entry_path)
        _id = resolver_obj.get_representation_id()
        representation = {"_id": _id}
        update_container(container, asset, subset, version, representation,
                         rename_group=False)

        # Delete usd proxyShape node
        proxy_shape_node = cmds.listRelatives(subset_group, children=True)[0]
        cmds.delete(proxy_shape_node)
        return True

    def _load_maya_plugin(self):
        """
        Load usd plugin in current session
        """
        import maya.cmds as cmds

        try:
            PLUGIN_NAMES = ["AbcImport"]
            for plugin_name in PLUGIN_NAMES:
                cmds.loadPlugin(plugin_name, quiet=True)
        except Exception as e:
            print("Load plugin failed: ", e)
