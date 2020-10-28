
import pyblish.api
from avalon import io, api


class ExtractCameraUSD(pyblish.api.InstancePlugin):
    """Bake and export camera into mayaAscii, Alembic and FBX format
    """

    order = pyblish.api.ExtractorOrder + 0.494
    hosts = ["maya"]
    label = "Extract Camera USD"
    families = [
        "reveries.camera",
    ]

    def process(self, instance):
        from maya import cmds
        from reveries import utils
        from reveries.maya import utils as maya_utils

        asset_doc = instance.data["assetDoc"]
        self.shot_name = asset_doc["name"]

        camera = cmds.ls(instance, type="camera", long=True)[0]

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])

        context_data = instance.context.data
        start = context_data["startFrame"]
        end = context_data["endFrame"]
        step = instance.data.get("bakeStep", 1.0)

        instance.data["startFrame"] = start
        instance.data["endFrame"] = end
        instance.data["step"] = step
        instance.data["task"] = self._get_task_name()  # layout/animation

        usd_file_name = "%s.usda" % instance.data["subset"]
        usd_outpath = "%s/%s" % (staging_dir, usd_file_name)

        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [usd_file_name]
        instance.data["repr.USD.entryFileName"] = usd_file_name
        instance.data["repr.USD.cameraUUID"] = maya_utils.get_id(camera)

        self._export_usd(camera, usd_outpath)

        self._publish_instance(instance)

        # Update task information
        self._check_task_data_exists(instance)

    def _check_task_data_exists(self, instance):
        _filter = {'type': 'asset', 'name': self.shot_name}
        shot_data = io.find_one(_filter)

        subset_filter = {
            'type': 'subset',
            'name': instance.data["subset"],
            'parent': shot_data['_id']
        }

        subset_data = [s for s in io.find(subset_filter)]

        if subset_data:
            subset_data = subset_data[0]

            if not subset_data["data"].get("task", ""):
                update = {
                    "data.task": self._get_task_name()
                }
                io.update_many(subset_filter, update={"$set": update})

    def _get_task_name(self):
        current_task = api.Session["AVALON_TASK"]  # layout/animation
        if current_task.lower() in ["layout", "lay"]:
            return "layout"

        if current_task.lower() in ["animation", "animating", "ani"]:
            return "animation"

        return current_task

    def _export_usd(self, camera, usd_outpath):
        import maya.cmds as cmds
        from reveries.maya.usd.maya_export import MayaUsdExporter

        # Check ROOT group
        root_created = False

        cam_transform = cmds.listRelatives(
            camera, parent=True, fullPath=True)[0]
        cam_top_group = "|{}".format(cam_transform.split("|")[1])
        if cam_top_group != "|ROOT":
            cmds.select(cl=True)
            if cmds.objExists("|ROOT"):
                cmds.parent(cam_top_group, "|ROOT")
            else:
                root_created = True
                cmds.group(cam_top_group, n="ROOT")
            cmds.select(cl=True)

        # Update shape node name
        camera_shape = cmds.ls(type="camera", long=True)[0]
        cam_transform = cmds.listRelatives(
            camera_shape, parent=True, fullPath=True)[0]

        self._check_film_gata(camera_shape)

        # Start export camera usd
        cmds.select(cam_transform)

        exporter = MayaUsdExporter(
            export_path=usd_outpath,
            export_selected=True)
        exporter.exportUVs = True
        exporter.mergeTransformAndShape = True
        exporter.animation = True
        exporter.exportColorSets = True
        exporter.exportDisplayColor = True
        exporter.export()
        self.log.info(
            "Export usd file for camera \"{}\".".format(cam_transform))

        # Clean unless group
        if root_created:
            cmds.parent("|ROOT{}".format(cam_top_group), w=True)
            cmds.select(cl=True)
            cmds.delete("|ROOT")

        cmds.setAttr(
            "{}.verticalFilmAperture".format(camera),
            self.old_aperture_v
        )

    def _check_film_gata(self, cam_shape):
        import maya.cmds as cmds

        project = io.find_one({"name": api.Session["AVALON_PROJECT"],
                               "type": "project"})

        resolution_h = project["data"]["resolution_width"]  # 5437
        resolution_v = project["data"]["resolution_height"]  # 1080

        old_aperture_h = cmds.getAttr(
            "{}.horizontalFilmAperture".format(cam_shape))  # 1.417
        self.old_aperture_v = cmds.getAttr(
            "{}.verticalFilmAperture".format(cam_shape))  # 0.945

        # aperture_h = 1.417
        aperture_v = resolution_v*old_aperture_h/resolution_h

        cmds.setAttr("{}.verticalFilmAperture".format(cam_shape), aperture_v)

        self.log.info(
            "Set camera verticalFilmAperture to {}".format(aperture_v))

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance)

        instance.data["_preflighted"] = True
