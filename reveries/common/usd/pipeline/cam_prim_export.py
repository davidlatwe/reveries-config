import re

from pxr import Usd, Sdf, UsdGeom

from avalon import io


def get_camera_subsets(shot_name):
    """
    Get camera subset information.
    :param shot_name: (str) Shot name
    :return: (dict) Camera usd file information
        variant_data = {
            'cameraDefault':
                r'/.../v004/USD/cameraDefault.usda'
            ,
            'cameraAnimation':
                r'/.../v004/USD/cameraDefault.usda'

        }
    """
    from reveries.common import get_publish_files

    # Get shot id
    _filter = {"type": "asset", "name": shot_name}
    asset_data = io.find_one(_filter)
    shot_id = asset_data['_id']

    # Get camera subset data
    _filter = {
        "type": "subset",
        "parent": shot_id,
        "data.families": "reveries.camera"
    }
    cam_subset_data = [s for s in io.find(_filter)]

    variant_data = {}
    for _subset_data in cam_subset_data:
        subset_name = _subset_data['name']
        subset_id = _subset_data['_id']
        file_list = get_publish_files.get_files(subset_id).get("USD", [])

        variant_data[subset_name] = file_list[0] if file_list else ""
    return variant_data


def export(shot_name, output_path):
    from reveries.common import get_frame_range
    variant_data = get_camera_subsets(shot_name)
    variant_key = variant_data.keys()

    stage = Usd.Stage.CreateInMemory()
    root_define = UsdGeom.Xform.Define(stage, "/ROOT")

    cam_define = UsdGeom.Xform.Define(stage, "/ROOT/Camera")
    cam_prim = stage.GetPrimAtPath("/ROOT/Camera")

    variants = cam_define.GetPrim().\
        GetVariantSets().AddVariantSet("camera_subset")

    for _key in variant_key:
        usd_file_path = variant_data.get(_key, "")

        variants.AddVariant(_key)
        variants.SetVariantSelection(_key)

        with variants.GetVariantEditContext():
            cam_prim.GetReferences().SetReferences(
                [Sdf.Reference(usd_file_path)])

    # Set default key to cameraDefault
    default_key = ''
    for _key in variant_data.keys():
        match = re.findall('(\S+default)', _key.lower())
        if match:
            default_key = _key
    default_key = default_key or variant_data.keys()[0]
    variants.SetVariantSelection(default_key)

    # Set default prim
    root_prim = stage.GetPrimAtPath('/ROOT')
    stage.SetDefaultPrim(root_prim)

    # Set frame range
    frame_in, frame_out = get_frame_range(shot_name)
    stage.SetStartTimeCode(frame_in)
    stage.SetEndTimeCode(frame_out)

    # print(stage.GetRootLayer().ExportToString())
    stage.GetRootLayer().Export(output_path)
