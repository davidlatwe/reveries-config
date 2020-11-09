import os
import json

import avalon.api
from avalon import io, api
from avalon.vendor import qargparse
from reveries.maya.plugins import ReferenceLoader
from reveries.common import path_resolver
from reveries.common import get_publish_files


class USDLayoutLoader(ReferenceLoader, avalon.api.Loader):
    """Load layout USD"""

    label = "Reference Layout"
    order = -10
    icon = "code-fork"
    color = "orange"

    hosts = ["maya"]

    families = ["reveries.layout.usd"]

    representations = [
        "USD",
    ]

    options = [
        qargparse.Integer("count", default=1, min=1, help="Batch load count."),
        qargparse.Boolean("update_camera",
                          label="Update to latest camera",
                          default=True, help="Update camera to latest version")
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
        namespace = namespace or self._get_namespace(context)

        # === Reference Setdress === #
        self._reference_setdress(context, name, namespace,
                                 options, layPrim_data)

        # === Reference Camera === #
        self._reference_camera(context, name, namespace, options)

        # === Update frame range === #
        frame_in, frame_out = get_frame_range(shot_name)
        cmds.playbackOptions(minTime=frame_in)
        cmds.playbackOptions(maxTime=frame_out)

        cmds.playbackOptions(animationStartTime=frame_in)
        cmds.playbackOptions(animationEndTime=frame_out)

    def _reference_setdress(self, context, name, namespace,
                            options, layPrim_data):
        from maya import cmds

        for subset_name, data in layPrim_data.get("Shot", {}).items():
            if "reveries.setdress.usd" in data.get("families", []):
                subset_id = data["subset_id"]
                version_name = data["version_name"]
                version_num = int(version_name.replace("v", ""))

                files = get_publish_files.get_files(
                    subset_id, version=version_num).get("GPUCache", [])
                ma_file = [s for s in files if s.endswith(".ma")]
                if ma_file:
                    ma_file = ma_file[0]
                    group_name = self.group_name(namespace, subset_name)

                    container = self._load(
                        context,
                        name=name,
                        namespace="{}{}".format(namespace, subset_name),
                        options=options,
                        group_name=group_name,
                        file_path=ma_file)
                    con_node_name = container.get("objectName", None)

                    if con_node_name:
                        resolver_obj = path_resolver.PathResolver(
                            file_path=ma_file)
                        representation_id = resolver_obj.get_representation_id()

                        _new_id_data = {
                            "subsetId": subset_id,
                            "versionId": data["version_id"],
                            "representation": representation_id
                        }
                        for _key, _value in _new_id_data.items():
                            cmds.setAttr("{}.{}".format(con_node_name, _key),
                                         _value,
                                         type="string")
                else:
                    self.log.info("{} no GPU published.".format(subset_name))

    def _reference_camera(self, context, name, namespace, options):
        from maya import cmds

        update_camera = options.get("update_camera", True)
        self.log.info("update_camera: {}".format(update_camera))

        _filter = {
            "type": "subset",
            "data.task": "layout"}
        subset_data = io.find_one(_filter)

        subset_id = subset_data["_id"]

        # TODO: Check camera version from layout.json, don't delete code
        # if update_camera:
        #     version_num = None
        # else:
        #     version_name = camera_data["version_name"]
        #     version_num = int(version_name.replace("v", ""))
        version_num = None

        files = get_publish_files.get_files(
            subset_id,
            version=version_num).get("Alembic", [])
        abc_file = [s for s in files if s.endswith(".abc")]
        if not abc_file:
            self.log.info("Not found camera abc file published.")
            return

        abc_file = abc_file[0]

        group_name = self.group_name(namespace, "camera")
        container = self._load(context, name=name,
                               namespace="{}camera".format(namespace),
                               options=options, group_name=group_name,
                               file_path=abc_file)

        con_node_name = container.get("objectName", None)
        if con_node_name:
            resolver_obj = path_resolver.PathResolver(file_path=abc_file)
            version_id = resolver_obj.get_version_id()
            representation_id = resolver_obj.get_representation_id()

            _new_id_data = {
                "subsetId": subset_id,
                "versionId": version_id,  # camera_data["version_id"],
                "representation": representation_id
            }
            for _key, _value in _new_id_data.items():
                cmds.setAttr("{}.{}".format(con_node_name, _key),
                             _value,
                             type="string")

    def _load(self, context, name=None, namespace=None,
              options=None, group_name=None, file_path=None):
        from maya import cmds

        from reveries.maya.pipeline import subset_containerising
        from reveries.maya.utils import generate_container_id

        options = options or dict()

        count = options.get("count", 1)
        if count > 1:
            options["count"] -= 1
            self.load(context, name, options=options.copy())

        # Get namespace
        namespace = namespace or self._get_namespace(context)

        # group_name = self.group_name(namespace, name)
        self.process_reference(context=context,
                               name=name,
                               namespace=namespace,
                               group=group_name,
                               options=options,
                               file_path=file_path)
        # (TODO) The group node may not be named exactly as `group_name` if
        #   `namespace` already exists. Might need to get the group node from
        #   `process_reference` so we could get the real name in case it's been
        #   renamed by Maya. May reference `ImportLoader.process_import`.

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        nodes = self._get_containerizable_nodes(nodes)

        # Only containerize if any nodes were loaded by the Loader
        if not nodes:
            return

        if "offset" in options and cmds.objExists(group_name):
            offset = [i * (count - 1) for i in options["offset"]]
            cmds.setAttr(group_name + ".t", *offset)

        container_id = options.get("containerId", generate_container_id())

        container = subset_containerising(name=name,
                                          namespace=namespace,
                                          container_id=container_id,
                                          nodes=nodes,
                                          context=context,
                                          cls_name=self.__class__.__name__,
                                          group_name=group_name)
        return container

    def process_reference(self, context, name, namespace,
                          group, options, file_path=None):
        import maya.cmds as cmds
        from avalon import maya

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

    def _get_namespace(self, context):
        from reveries.maya.pipeline import unique_root_namespace

        shot_data = context["asset"]

        shot_name = shot_data["data"].get("shortName", shot_data["name"])
        if context["subset"]["schema"] == "avalon-core:subset-3.0":
            families = context["subset"]["data"]["families"]
        else:
            families = context["version"]["data"]["families"]
        family_name = families[0].split(".")[-1]
        return unique_root_namespace(shot_name, family_name)
