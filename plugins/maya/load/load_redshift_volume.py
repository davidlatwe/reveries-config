
import avalon.api
from reveries.maya.plugins import ImportLoader


class RedshiftVolumeLoader(ImportLoader, avalon.api.Loader):

    label = "Load Redshift Volume"
    order = -10
    icon = "cloud"
    color = "orange"

    hosts = ["maya"]

    families = [
        "reveries.vdbcache",
    ]

    representations = [
        "VDB",
    ]

    def process_import(self, context, name, namespace, group, options):
        from maya import cmds, mel
        from reveries.maya import capsule

        representation = context["representation"]
        entry_path = self.file_path(representation)
        use_sequence = self.is_sequence(entry_path)

        with capsule.namespaced(namespace):
            # create volume with shader assigned
            volume = cmds.createNode("RedshiftVolumeShape")
            shader = mel.eval('rsCreateShadingNode'
                              ' "rendernode/redshift/shader/volume"'
                              ' "-asShader" "" "RedshiftVolume"')
            shading_group = cmds.listConnections(shader + ".outColor",
                                                 destination=True,
                                                 source=False)[0]
            mel.eval("assignSG %s %s" % (shading_group, volume))

            cmds.setAttr(volume + ".fileName", entry_path, type="string")
            transform = cmds.listRelatives(volume, parent=True)[0]
            group = cmds.group(transform, name=group, world=True)

        if use_sequence:
            cmds.setAttr(volume + ".useFrameExtension", True)

        self[:] = [volume, transform, group]

    def file_path(self, representation):
        import os
        _e_path = super(RedshiftVolumeLoader, self).file_path(representation)
        # looks like redshift volume doesn't support in-path-env-var
        return os.path.expandvars(_e_path)

    def is_sequence(self, path):
        """single vdb or vdb sequence"""
        import os
        expanded_dir = os.path.dirname(os.path.expandvars(path))
        vdbs = [f for f in os.listdir(expanded_dir) if f.endswith(".vdb")]
        return len(vdbs) > 1

    def update(self, container, representation):
        import maya.cmds as cmds
        from reveries.maya import pipeline
        from reveries.utils import get_representation_path_

        members = cmds.sets(container["objectName"], query=True)
        volumes = cmds.ls(members, type="RedshiftVolumeShape", long=True)

        if not volumes:
            raise Exception("No Redshift Volume node, this is a bug.")

        parents = avalon.io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)

        entry_path = self.file_path(representation)
        use_sequence = self.is_sequence(entry_path)

        if not entry_path.endswith(".vdb"):
            raise Exception("Not a VDB file, this is a bug: "
                            "%s" % entry_path)

        for volume in volumes:
            # This would allow all copies getting updated together
            cmds.setAttr(volume + ".fileName", entry_path, type="string")
            cmds.setAttr(volume + ".useFrameExtension", use_sequence)

        # Update container
        version, subset, asset, _ = parents
        pipeline.update_container(container,
                                  asset,
                                  subset,
                                  version,
                                  representation)

    def switch(self, container, representation):
        self.update(container, representation)
