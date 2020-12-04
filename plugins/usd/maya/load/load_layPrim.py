import os
import json

import avalon.api
from avalon import io
from avalon.vendor import qargparse

from reveries.common import path_resolver
from reveries.common import get_publish_files

from reveries.maya.plugins import ReferenceLoader
from reveries.maya.plugins import USDLoader


class _ReferenceLoader(ReferenceLoader, avalon.api.Loader):
    def __init__(self, context=None):
        if context:
            super(_ReferenceLoader, self).__init__(context)

    def update(self, container, representation):
        super(_ReferenceLoader, self).update(container, representation)

    def remove(self, container):
        super(_ReferenceLoader, self).remove(container)

    def load(self,
             context, name=None, namespace=None, options=None, ref_path=None):
        self.ref_path = ref_path
        container = super(_ReferenceLoader, self).load(
            context, name=name, namespace=namespace, options=options
        )
        return container

    def process_reference(self, context, name, namespace, group, options):
        import maya.cmds as cmds
        from avalon import maya

        with maya.maintained_selection():
            nodes = cmds.file(self.ref_path,
                              namespace=namespace,
                              ignoreVersion=True,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName=group)
        self[:] = nodes


class USDLayoutLoader(USDLoader, avalon.api.Loader):
    """Load layout USD"""

    label = "Build Layout Scene"
    order = -10
    icon = "institution"
    color = "#eb605e"

    hosts = ["maya"]

    families = ["reveries.layout.usd"]

    representations = ["USD"]

    options = [
        qargparse.Boolean(
            "update_camera",
            label="Update to latest camera",
            default=True, help="Update camera to latest version"
        )
    ]

    def load(self, context, name=None, namespace=None, options=None):
        import maya.cmds as cmds
        from reveries.common import get_frame_range

        self._load_maya_plugin()

        shot_data = context["asset"]
        shot_name = shot_data["name"]
        # shot_short_name = shot_data["data"].get("label", shot_data["name"])

        # Read json file
        representation = context["representation"]
        entry_path = self.file_path(representation)
        entry_path = entry_path.replace(
            "$AVALON_PROJECTS",
            os.environ["AVALON_PROJECTS"])
        entry_path = entry_path.replace(
            "$AVALON_PROJECT",
            os.environ["AVALON_PROJECT"])

        json_path = os.path.join(os.path.dirname(entry_path), "layout.json")

        with open(json_path) as json_path:
            layPrim_data = json.load(json_path)

        # Get namespace
        namespace = namespace or self._get_namespace(context, shot_name)

        # === Reference Setdress === #
        self._reference_setdress(
            context, name, namespace, options, layPrim_data
        )

        # === Reference Camera === #
        self._reference_camera(
            context, "camera", namespace, options, shot_name
        )

        # === Update frame range === #
        frame_in, frame_out = get_frame_range(shot_name)
        cmds.playbackOptions(minTime=frame_in)
        cmds.playbackOptions(maxTime=frame_out)

        cmds.playbackOptions(animationStartTime=frame_in)
        cmds.playbackOptions(animationEndTime=frame_out)

    def _reference_setdress(
            self, context, name, namespace, options, layPrim_data):
        for subset_name, data in layPrim_data.get("Shot", {}).items():
            if "reveries.setdress.usd" in data.get("families", []):
                subset_id = data["subset_id"]
                version_name = data["version_name"]
                version_num = int(version_name.replace("v", ""))

                files = get_publish_files.get_files(
                    subset_id, version=version_num).get("USD", [])
                usd_file = [s for s in files if s.endswith(".usda")]
                if usd_file:
                    usd_file = usd_file[0]
                    group_name = "{}{}".format(namespace, name)
                    container = self._load(
                        context,
                        name=name,
                        namespace="{}{}".format(namespace, subset_name),
                        options=options,
                        group_name=group_name,
                        file_path=usd_file)
                    con_node_name = container.get("objectName", None)

                    if con_node_name:
                        self._update_container_node(usd_file, con_node_name)
                else:
                    self.log.info(
                        "Error: {}({}) no USD published.".format(
                            subset_name, version_name
                        )
                    )

    def _reference_camera(self, context, name, namespace, options, shot_name):
        update_camera = options.get("update_camera", True)
        self.log.info("update_camera: {}".format(update_camera))

        _filter = {"type": "asset", "name": shot_name}
        shot_data = io.find_one(_filter)

        _filter = {
            "type": "subset",
            "data.task": "layout",
            "parent": shot_data['_id']
        }
        subset_data = io.find_one(_filter)
        if not subset_data:
            self.log.error("Get camera failed.")
            return

        subset_id = subset_data["_id"]

        # TODO: Check camera version from layout.json, don't delete code
        # if update_camera:
        #     version_num = None
        # else:
        #     version_name = camera_data["version_name"]
        #     version_num = int(version_name.replace("v", ""))
        version_num = None

        # Get camera.abc file
        files = get_publish_files.get_files(
            subset_id,
            version=version_num).get("Alembic", [])
        abc_file = [s for s in files if s.endswith(".abc")]
        if not abc_file:
            self.log.error("Not found camera abc file published.")
            return
        abc_file = abc_file[0]

        # Reference camera
        # group_name = self.group_name(namespace, name)
        # container = self._load(context, name=name,
        #                        namespace=namespace,
        #                        options=options, group_name=group_name,
        #                        file_path=abc_file)
        loader = _ReferenceLoader(context=context)
        container = loader.load(
            context, name="camera", namespace=namespace, options=options,
            ref_path=abc_file
        )

        con_node_name = container.get("objectName", None)
        if con_node_name:
            self._update_container_node(abc_file, con_node_name)

    def _update_container_node(self, file_path, con_node_name):
        from maya import cmds

        resolver_obj = path_resolver.PathResolver(file_path=file_path)
        version_id = resolver_obj.get_version_id()
        representation_id = resolver_obj.get_representation_id()
        subset_id = resolver_obj.get_subset_id()

        _new_id_data = {
            "subsetId": subset_id,
            "versionId": version_id,  # camera_data["version_id"],
            "representation": representation_id,
            "loader": "USDLayoutLoader"
        }
        for _key, _value in _new_id_data.items():
            cmds.setAttr("{}.{}".format(con_node_name, _key), _value,
                         type="string")

    def _load(self, context, name=None, namespace=None,
              options=None, group_name=None, file_path=None):

        from reveries.maya.pipeline import subset_containerising
        from reveries.maya.utils import generate_container_id

        options = options or dict()

        self.process_reference(context=context,
                               name=name,
                               namespace=namespace,
                               group=group_name,
                               options=options,
                               file_path=file_path)

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        print("nodes: ", nodes)
        # nodes = self._get_containerizable_nodes(nodes)

        # Only containerize if any nodes were loaded by the Loader
        if not nodes:
            return

        container_id = options.get("containerId", generate_container_id())

        container = subset_containerising(name=name,
                                          namespace=namespace,
                                          container_id=container_id,
                                          nodes=nodes,
                                          context=context,
                                          cls_name=self.__class__.__name__,
                                          group_name=group_name)
        return container

    def process_reference(self, context, name, namespace, group, options,
                          file_path=None):
        import maya.cmds as cmds
        from avalon import maya

        if file_path.endswith("usda"):
            with maya.maintained_selection():
                node = cmds.createNode(
                    # "mayaUsdProxyShape",  # unselectable not working
                    "pxrUsdProxyShape",
                    name="{}Shape".format(namespace)
                )
                cmds.setAttr("{}.drawProxyPurpose".format(node), 0)
                cmds.setAttr("{}.drawRenderPurpose".format(node), 1)

                translate_grp = cmds.listRelatives(node, parent=True)[0]
                cmds.rename(translate_grp, namespace)

                cmds.setAttr(
                    "{}.filePath".format(node), file_path, type="string"
                )

                cmds.setAttr("{}.overrideEnabled".format(namespace), 1)
                cmds.setAttr("{}.overrideDisplayType".format(namespace), 2)

                cmds.select(cl=True)
                cmds.group(translate_grp, name=group)
            self[:] = [node]

        elif file_path.endswith(".abc"):
            with maya.maintained_selection():
                nodes = cmds.file(file_path,
                                  namespace=namespace,
                                  ignoreVersion=True,
                                  reference=True,
                                  returnNewNodes=True,
                                  groupReference=True,
                                  groupName=group)
            self[:] = nodes

    def _load_maya_plugin(self):
        """
        Load usd plugin in current session
        """
        import maya.cmds as cmds

        try:
            PLUGIN_NAMES = [
                "pxrUsd",
                "pxrUsdPreviewSurface",
                "gpuCache",
                "AbcExport"
            ]
            for plugin_name in PLUGIN_NAMES:
                cmds.loadPlugin(plugin_name, quiet=True)
        except Exception as e:
            self.log.info("Load plugin failed: {}".format(e))

    def _get_namespace(self, context, shot_name):
        from reveries.maya.pipeline import unique_root_namespace

        if context["subset"]["schema"] == "avalon-core:subset-3.0":
            families = context["subset"]["data"]["families"]
        else:
            families = context["version"]["data"]["families"]
        family_name = families[0].split(".")[-1]

        return unique_root_namespace(shot_name, family_name)

    def update(self, container, representation):
        entry_path = self.file_path(representation).replace("\\", "/")

        if entry_path.endswith(".usda"):
            super(USDLayoutLoader, self).update(container, representation)
        else:
            loader = _ReferenceLoader()
            loader.update(container, representation)

        return True

    def remove(self, container):
        _filter = {"_id": io.ObjectId(container.get("representation", ""))}
        representation_data = io.find_one(_filter)

        if not representation_data:
            self.log.error(
                "No representation found for {}".format(container["objectName"])
            )
            return False

        if str(representation_data["name"]) == "USD":
            super(USDLayoutLoader, self).remove(container)
        else:
            loader = _ReferenceLoader()
            loader.remove(container)

        return True
