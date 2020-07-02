
import os
import contextlib
import avalon.api
from collections import defaultdict
from reveries.maya.plugins import ImportLoader
from reveries.maya import lib, capsule, pipeline


class AnimationLoader(ImportLoader, avalon.api.Loader):
    """Specific loader of Alembic for the reveries.animation family"""

    label = "Load Animation"
    order = -10
    icon = "code-fork"
    color = "orange"

    hosts = ["maya"]

    families = ["reveries.animation"]

    representations = [
        "anim",
    ]

    def process_import(self, context, name, namespace, group, options):
        from maya import cmds, mel
        from reveries import plugins

        representation = context["representation"]
        asset_id = representation["data"]["animatedAssetId"]
        selected = cmds.ls(selection=True, long=True)

        # Collect namespace from selected nodes
        namespaces = defaultdict(set)
        for node in selected:
            ns = lib.get_ns(node)
            if ns == ":":
                continue
            namespaces[ns].add(node)

        for ns, nodes in namespaces.items():
            try:
                container = pipeline.get_container_from_namespace(ns)
            except RuntimeError:
                continue

            if asset_id != cmds.getAttr(container + ".assetId"):
                confirm = plugins.message_box_warning(
                    "Warning",
                    "Applying animation to different asset, are you sure ?",
                    optional=True,
                )
                if not confirm:
                    raise Exception("Operation canceled.")

            target_ns = ns
            members = nodes
            break

        else:
            raise Exception("No matched asset found.")

        cmds.loadPlugin("animImportExport", quiet=True)

        entry_path = self.file_path(representation).replace("\\", "/")
        sele_path = entry_path.rsplit("anim", 1)[0] + "mel"
        sele_path = os.path.expandvars(sele_path)

        with capsule.maintained_selection():
            # Select nodes with order
            with contextlib.nested(
                capsule.namespaced(target_ns, new=False),
                capsule.relative_namespaced()
            ):
                mel.eval("source \"%s\"" % sele_path)

            targets = cmds.ls(selection=True, long=True)
            nodes = cmds.file(entry_path,
                              force=True,
                              type="animImport",
                              i=True,
                              importTimeRange="keep",
                              ignoreVersion=True,
                              returnNewNodes=True,
                              options=("targetTime=4;"
                                       "option=replace;"
                                       "connect=0")
                              )
            # Apply namespace by ourselves, since animImport does not
            # take -namespace flag
            namespaced_nodes = list()
            for node in nodes:
                node = cmds.rename(node, namespace + ":" + node)
                namespaced_nodes.append(node)

            # Delete not connected
            targets = set(targets)
            connected = list()
            for node in namespaced_nodes:
                future = cmds.listHistory(node, future=True)
                future = set(cmds.ls(future, long=True))
                if targets.intersection(future):
                    connected.append(node)
                else:
                    cmds.delete(node)

            if not connected:
                raise Exception("No animation been applied.")

            self[:] = connected

        # Remove assigned from selection
        unprocessed = list(set(selected) - members)
        cmds.select(unprocessed, replace=True, noExpand=True)

    def update(self, container, representation):
        self.remove(container)
        # Restore to default value by removing reference edit ?
        avalon.api.load(AnimationLoader, representation)

    def switch(self, container, representation):
        self.update(container, representation)
