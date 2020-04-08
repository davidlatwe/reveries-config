
import contextlib
import pyblish.api
import avalon
from reveries import utils
from reveries.maya import io, lib, capsule, utils as maya_utils
from maya import cmds


class ExtractCamera(pyblish.api.InstancePlugin):
    """Bake and export camera into mayaAscii, Alembic and FBX format
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Camera"
    families = [
        "reveries.camera",
    ]

    def process(self, instance):

        staging_dir = utils.stage_dir()

        context_data = instance.context.data
        start = context_data["startFrame"]
        end = context_data["endFrame"]
        step = instance.data.get("bakeStep", 1.0)

        instance.data["startFrame"] = start
        instance.data["endFrame"] = end
        instance.data["step"] = step

        ma_filename = "%s.ma" % instance.data["subset"]
        ma_outpath = "%s/%s" % (staging_dir, ma_filename)

        abc_filename = "%s.abc" % instance.data["subset"]
        abc_outpath = "%s/%s" % (staging_dir, abc_filename)

        fbx_filename = "%s.fbx" % instance.data["subset"]
        fbx_outpath = "%s/%s" % (staging_dir, fbx_filename)

        DO_NOT_BAKE_THESE = [
            "motionBlurOverride",
            "aiUseGlobalShutter",
            "aiShutterStart",
            "aiShutterEnd",
            "aiShutterType",
            "aiEnableDOF",
            "aiFov",
            "aiHorizontalFov",
            "aiVerticalFov",
        ]

        DO_BAKE_THESE = [
            "focalLength",
        ]
        DO_BAKE_THESE += lib.TRANSFORM_ATTRS

        camera = cmds.ls(instance, type="camera", long=True)[0]

        cam_uuid = maya_utils.get_id(camera)
        cam_transform = cmds.listRelatives(camera,
                                           parent=True,
                                           fullPath=True)[0]

        donot_bake = [cam_transform + "." + attr for attr in DO_NOT_BAKE_THESE]
        do_bake = [cam_transform + "." + attr for attr in DO_BAKE_THESE]

        euler_filter = instance.data.get("eulerFilter", False)

        instance.data["repr.mayaAscii._stage"] = staging_dir
        instance.data["repr.mayaAscii._files"] = [ma_filename]
        instance.data["repr.mayaAscii.entryFileName"] = ma_filename
        instance.data["repr.mayaAscii.cameraUUID"] = cam_uuid

        instance.data["repr.Alembic._stage"] = staging_dir
        instance.data["repr.Alembic._files"] = [abc_filename]
        instance.data["repr.Alembic.entryFileName"] = abc_filename
        instance.data["repr.Alembic.cameraUUID"] = cam_uuid

        instance.data["repr.FBX._stage"] = staging_dir
        instance.data["repr.FBX._files"] = [fbx_filename]
        instance.data["repr.FBX.entryFileName"] = fbx_filename
        instance.data["repr.FBX.cameraUUID"] = cam_uuid

        # Delay one for all
        instance.data["repr._all_repr_._stage"] = staging_dir
        instance.data["repr._all_repr_._delayRun"] = {
            "func": self.extract_all,
            "args": [
                cam_transform,
                ma_outpath,
                abc_outpath,
                fbx_outpath,
                start,
                end,
                step,
                euler_filter,
                do_bake,
                donot_bake
            ],
        }

    def extract_all(self,
                    cam_transform,
                    ma_outpath,
                    abc_outpath,
                    fbx_outpath,
                    start,
                    end,
                    step,
                    euler_filter,
                    do_bake,
                    donot_bake):

        with contextlib.nested(
            capsule.no_refresh(),
            capsule.no_undo(),
            capsule.attribute_states(donot_bake, lock=False, keyable=False),
            capsule.attribute_states(do_bake, lock=False, keyable=True),
            capsule.evaluation("off"),
        ):
            with capsule.delete_after() as delete_bin:

                # bake to worldspace
                frame_range = (start, end)
                baked_camera = lib.bake_to_world_space(cam_transform,
                                                       frame_range,
                                                       step=step)[0]
                delete_bin.append(baked_camera)

                cmds.select(baked_camera,
                            hierarchy=True,  # With shape
                            replace=True,
                            noExpand=True)

                with avalon.maya.maintained_selection():
                    io.export_alembic(abc_outpath,
                                      start,
                                      end,
                                      eulerFilter=euler_filter)

                with capsule.undo_chunk_when_no_undo():
                    if euler_filter:
                        cmds.filterCurve(cmds.ls(sl=True))

                    with avalon.maya.maintained_selection():
                        cmds.file(ma_outpath,
                                  force=True,
                                  typ="mayaAscii",
                                  exportSelected=True,
                                  preserveReferences=False,
                                  constructionHistory=False,
                                  channels=True,  # allow animation
                                  constraints=False,
                                  shader=False,
                                  expressions=False)

                    with avalon.maya.maintained_selection():
                        io.export_fbx_set_camera()
                        io.export_fbx(fbx_outpath)
