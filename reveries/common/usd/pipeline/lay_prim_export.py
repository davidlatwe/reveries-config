from avalon import io
from reveries.common import get_publish_files


def build(output_path, shot_name):
    from pxr import Usd, UsdGeom
    from reveries.common import get_frame_range

    frame_in, frame_out = get_frame_range.get(shot_name)
    # shot_name = "sh0100"
    stage = Usd.Stage.CreateInMemory()

    stage.SetStartTimeCode(frame_in)
    stage.SetEndTimeCode(frame_out)

    # Create shot prim
    root_define = UsdGeom.Xform.Define(stage, "/ROOT")
    root_prim = stage.GetPrimAtPath('/ROOT')
    root_layer = stage.GetRootLayer()

    stage.SetDefaultPrim(root_prim)
    stage.GetRootLayer().documentation = "Layout usd for {}".format(shot_name)

    # Add setdress
    setdress_prim_files = _get_setdress_prim_files(shot_name)
    if setdress_prim_files:
        for _file in setdress_prim_files:
            root_layer.subLayerPaths.append(_file)
    # Add camera
    cam_prim_file = _get_camera_prim_files(shot_name)
    if cam_prim_file:
        root_layer.subLayerPaths.append(cam_prim_file)

    stage.GetRootLayer().Export(output_path)
    # print(stage.GetRootLayer().ExportToString())


def _get_camera_prim_files(shot_name):
    usd_file = ''

    _filter = {"type": "asset", "name": shot_name}
    shot_data = io.find_one(_filter)

    _filter = {
        "parent": shot_data["_id"],
        "name": "camPrim",
        "type": "subset"
    }
    subset_data = io.find_one(_filter)
    if subset_data:
        usd_file = get_publish_files.get_files(
            subset_data["_id"], key='entryFileName').get('USD', '')

    return usd_file


def _get_setdress_prim_files(shot_name):
    _filter = {"type": "asset", "name": shot_name}
    shot_data = io.find_one(_filter)

    _filter = {
        "parent": shot_data["_id"],
        "data.families": "reveries.setdress.usd",
        # "step_type": "setdress_prim",
        "type": "subset"
    }
    setdress_prim_subsets = [s for s in io.find(_filter)]

    setdress_prim_files = []
    for _subset in setdress_prim_subsets:
        usd_file = get_publish_files.get_files(
            _subset["_id"], key='entryFileName').get('USD', '')
        setdress_prim_files.append(usd_file)

    return setdress_prim_files
