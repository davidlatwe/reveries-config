
import os
import avalon.api
from avalon.vendor import qargparse
from reveries.maya.plugins import ImportLoader


class RedshiftProxyLoader(ImportLoader, avalon.api.Loader):

    label = "Load Redshift Proxy"
    order = -10
    icon = "coffee"
    color = "orange"

    hosts = ["maya"]

    families = [
        "reveries.rsproxy",
    ]

    representations = [
        "RsProxy",
    ]

    options = [
        qargparse.Boolean(
            "placeholderFromSelection",
            help="Duplicate selected mesh as proxy's placeholder."),
        qargparse.Integer("count", default=1, min=1, help="Batch load count."),
        qargparse.Double3("offset", help="Offset loaded subsets."),
    ]

    def check_placeholder_selection(self):
        from maya import cmds
        from reveries.plugins import message_box_error

        selection = cmds.ls(sl=True)
        if not (len(selection) == 1
                and len(cmds.listRelatives(selection, type="mesh")) == 1):
            message = ("Please select one and only one mesh for "
                       "proxy placeholder.")
            message_box_error("Invalid Selection", message)
            raise RuntimeError(message)

    def process_import(self, context, name, namespace, group, options):
        from maya import cmds, mel
        from reveries.maya import capsule
        import contextlib

        representation = context["representation"]
        entry_path, use_sequence = self.retrive(representation)

        with contextlib.nested(
                capsule.maintained_selection(),
                capsule.namespaced(namespace),
        ):
            if options.get("placeholderFromSelection"):
                self.check_placeholder_selection()
                cmds.duplicate()
            else:
                cmds.select(clear=True)

            proxy, placeholder, transform = mel.eval("redshiftCreateProxy")
            cmds.setAttr(proxy + ".fileName", entry_path, type="string")
            group = cmds.group(transform, name=group, world=True)

        if use_sequence:
            cmds.setAttr(proxy + ".useFrameExtension", True)

        self[:] = [group] + cmds.listRelatives(group,
                                               allDescendents=True,
                                               path=True) or []

        return group

    def retrive(self, representation):
        entry_path = self.file_path(representation)
        use_sequence = representation["data"]["useSequence"]
        return entry_path, use_sequence

    def update(self, container, representation):
        import maya.cmds as cmds
        from avalon import io
        from reveries.maya import pipeline
        from reveries.utils import get_representation_path_

        members = cmds.sets(container["objectName"], query=True)
        proxies = cmds.ls(members, type="RedshiftProxyMesh", long=True)

        if not proxies:
            raise Exception("No Redshift Proxy node, this is a bug.")

        parents = io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)

        entry_path, use_sequence = self.retrive(representation)

        if not entry_path.endswith(".rs"):
            raise Exception("Not a Redshift Proxy file, this is a bug: "
                            "%s" % entry_path)

        for proxy in proxies:
            # This would allow all copies getting updated together
            cmds.setAttr(proxy + ".fileName", entry_path, type="string")
            cmds.setAttr(proxy + ".useFrameExtension", use_sequence)

        # Update container
        version, subset, asset, _ = parents
        pipeline.update_container(container,
                                  asset,
                                  subset,
                                  version,
                                  representation)

    def switch(self, container, representation):
        self.update(container, representation)
