from avalon import io, api


def export(asset_name, output_path):
    from pxr import Usd, UsdGeom
    from reveries.new_utils import get_publish_files

    subsets = ['renderPrim', 'proxyPrim']
    usd_files = {}
    has_proxy = False

    # Get asset id
    _filter = {"type": "asset", "name": asset_name}
    asset_id = io.find_one(_filter)['_id']

    # Get usd file from subset
    for subset_name in subsets:
        _filter = {
            "type": "subset",
            "name": subset_name,
            "parent": asset_id
        }
        # print('subset_name: ', subset_name)
        subset_data = io.find_one(_filter)
        if subset_data:
            subset_id = subset_data['_id']
            usd_files[subset_name] = get_publish_files.get_files(subset_id).get('USD', [])

        if subset_data and subset_name == 'proxyPrim':
            has_proxy = True

    stage = Usd.Stage.CreateInMemory()

    # Create ROOT define
    UsdGeom.Xform.Define(stage, "/ROOT")
    root_prim = stage.GetPrimAtPath('/ROOT')
    stage.SetDefaultPrim(root_prim)

    # Check proxy/render options
    if has_proxy:
        render_define = UsdGeom.Xform.Define(stage, "/ROOT/modelDefault")
        proxy_define = UsdGeom.Xform.Define(stage, "/ROOT/modelDefaultProxy")

        render_define.CreatePurposeAttr('render')
        proxy_define.CreatePurposeAttr('proxy')

    # Create sublayer
    root_layer = stage.GetRootLayer()

    for _, paths in usd_files.items():
        if paths:
            root_layer.subLayerPaths.append(paths[0])

    # print(stage.GetRootLayer().ExportToString())
    stage.GetRootLayer().Export(output_path)
