
import os
import avalon.api

from reveries.maya import lib, pipeline
from reveries.utils import get_representation_path_
from reveries.maya.plugins import ReferenceLoader, ImportLoader


class ArnoldStandInLoader(ReferenceLoader, avalon.api.Loader):
    """(Deprecated)"""

    label = "Reference Arnold Stand-In"
    order = 90
    icon = "coffee"
    color = "gray"

    hosts = ["maya"]

    families = [
        "reveries.standin",
    ]

    representations = [
        "Ass",
    ]

    def process_reference(self, context, name, namespace, group, options):
        raise DeprecationWarning("This loader has been deprecated.")


class ArnoldAssLoader(ImportLoader, avalon.api.Loader):

    label = "Load Arnold .ASS"
    order = -10
    icon = "coffee"
    color = "orange"

    hosts = ["maya"]

    families = [
        "reveries.standin",
    ]

    representations = [
        "Ass",
    ]

    def process_import(self, context, name, namespace, group, options):
        from maya import cmds
        from reveries.maya import capsule, arnold

        representation = context["representation"]
        entry_path, use_sequence = self.retrive(representation)

        with capsule.namespaced(namespace):
            standin = arnold.create_standin(entry_path)
            transform = cmds.listRelatives(standin, parent=True)[0]
            group = cmds.group(transform, name=group, world=True)

        if use_sequence:
            cmds.setAttr(standin + ".useFrameExtension", True)
            cmds.connectAttr("time1.outTime", standin + ".frameNumber")

        lib.lock_transform(group)
        self[:] = [standin, transform, group]

    def retrive(self, representation):
        if "useSequence" not in representation["data"]:
            entry_path, use_sequence = self._compat(representation)
        else:
            entry_path = self.file_path(representation)
            use_sequence = representation["data"]["useSequence"]

        return entry_path, use_sequence

    def _compat(self, representation):
        """For backwards compatibility"""
        entry_path = self.file_path(representation)
        entry_dir = os.path.dirname(entry_path)
        asses = [f for f in os.listdir(os.path.expandvars(entry_dir))
                 if f.endswith(".ass")]

        entry_path = os.path.join(entry_dir, asses[0])
        use_sequence = len(asses) > 1

        return entry_path, use_sequence

    def update(self, container, representation):
        import maya.cmds as cmds

        members = cmds.sets(container["objectName"], query=True)
        standin = next(iter(cmds.ls(members, type="aiStandIn")), None)

        if not standin:
            raise Exception("No Arnold Stand-In node, this is a bug.")

        parents = avalon.io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)

        entry_path, use_sequence = self.retrive(representation)

        cmds.setAttr(standin + ".dso", entry_path, type="string")
        cmds.setAttr(standin + ".useFrameExtension", use_sequence)

        # Update container
        version, subset, asset, _ = parents
        pipeline.update_container(container,
                                  asset,
                                  subset,
                                  version,
                                  representation)
