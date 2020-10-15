from avalon import io


def build(file_path, shot_name):
    from pxr import Usd, Sdf, UsdGeom
    from reveries import common

    frame_in, frame_out = common.get_frame_range(shot_name)
    # shot_name = "sh0100"
    stage = Usd.Stage.CreateInMemory()

    stage.SetStartTimeCode(frame_in)
    stage.SetEndTimeCode(frame_out)

    # Create shot prim
    root_define = UsdGeom.Xform.Define(stage, "/ROOT")
    root_prim = stage.GetPrimAtPath('/ROOT')
    stage.SetDefaultPrim(root_prim)
    stage.GetRootLayer().documentation = "Layout usd for {}".format(shot_name)

    # Add "Asset" prim
    _instance_path = "/ROOT/Asset"
    UsdGeom.Xform.Define(stage, _instance_path)

    _usd_paths = []
    env_prim_files = _get_env_prim_files(shot_name)
    if env_prim_files:
        for _path in env_prim_files:
            _usd_paths.append(Sdf.Reference(_path))

        asset_prim = stage.GetPrimAtPath(_instance_path)
        asset_prim.GetReferences().SetReferences(_usd_paths)

    # Add "Camera" prim
    _instance_path = "/ROOT/Camera"
    UsdGeom.Xform.Define(stage, _instance_path)

    _usd_paths = []
    cam_prim_files = _get_camera_prim_files(shot_name)
    if cam_prim_files:
        for _path in cam_prim_files:
            _usd_paths.append(Sdf.Reference(_path))
        camera_prim = stage.GetPrimAtPath(_instance_path)
        camera_prim.GetReferences().SetReferences(_usd_paths)

    stage.GetRootLayer().Export(file_path)
    # print(stage.GetRootLayer().ExportToString())


def _get_camera_prim_files(shot_name):
    return []


def _get_env_prim_files(shot_name):
    from reveries.common import get_publish_files

    _filter = {"type": "asset", "name": shot_name}
    shot_data = io.find_one(_filter)

    _filter = {
        "parent": shot_data["_id"],
        "step_type": "env_prim",
        "type": "subset"
    }
    env_prim_subsets = [s for s in io.find(_filter)]

    env_prim_files = []
    for _subset in env_prim_subsets:
        usd_file = get_publish_files.get_files(_subset["_id"], key='entryFileName').get('USD', '')
        env_prim_files.append(usd_file)

    return env_prim_files
