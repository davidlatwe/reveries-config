import re
from pxr import Usd, Sdf, UsdGeom

from avalon import io


def _get_variant_data(asset_name, prim_type='default'):
    """
    Get variant data from asset name
    :param asset_name: str. Asset name. eg.'HanMaleA'
    :return:
    variant_data = {
        'lookDefault': [
            r'\...\publish\modelDefault\v003\geom.usda',
            r'\...\publish\lookDefault\v002\assign.usda',
            r'\...\publish\lookDefault\v002\look.usda'
        ],
        'lookClothesB': [
            r'\...\publish\modelDefault\v003\geom.usda',
            r'\...\publish\lookClothesB\v002\assign.usda',
            r'\...\publish\lookClothesB\v002\look.usda'
        ]
    }
    variant_key = ['lookDefault', 'lookClothesB']
    """
    from reveries.common import get_publish_files

    _filter = {"type": "asset", "name": asset_name}
    asset_data = io.find_one(_filter)
    asset_id = asset_data['_id']

    # Get lookdev subset without lookProxy subset
    variant_key = []  # ['lookDefault', 'lookClothesB']
    _filter = {
        "type": "subset",
        "parent": io.ObjectId(str(asset_id)),
        "name": re.compile("look*")
    }
    # subset_data = []
    lookdev_data = [subset for subset in io.find(_filter)]
    for subset in io.find(_filter):
        regex = re.compile("^.*?(?<!Proxy)$")
        _subset_name = subset['name']
        if regex.search(_subset_name):
            # subset_data.append(subset)
            variant_key.append(_subset_name)  #

    # Get assign/look usd file
    lookfiles_data = {}
    for _subset in lookdev_data:
        subset_name = _subset['name']
        subset_id = _subset['_id']
        files = get_publish_files.get_files(subset_id)
        lookfiles_data[subset_name] = []

        # Get model subset's usd file
        model_id = _subset["data"].get("model_subset_id")
        if model_id:
            model_file = get_publish_files.get_files(
                model_id,
                key="entryFileName").get("USD", "")
            if model_file:
                lookfiles_data[subset_name].append(model_file)

        # Take modelDefault usd
        if not lookfiles_data[subset_name]:
            lookfiles_data[subset_name].append(_get_geom_usd(asset_name))

        lookfiles_data[subset_name] += files.get('USD', [])

    if not lookfiles_data or not variant_key:
        model_file = _get_geom_usd(asset_name)
        if model_file:
            look_key = model_file.split("/")[-4].replace("model", "look")  # lookDefault
            lookfiles_data = {look_key: [model_file]}
            variant_key = [look_key]
        else:
            lookfiles_data = {"lookDefault": []}
            variant_key = ["lookDefault"]

    return lookfiles_data, variant_key


def _get_geom_usd(asset_name):
    from reveries.common import get_publish_files

    _filter = {"type": "asset", "name": asset_name}
    asset_data = io.find_one(_filter)
    asset_id = asset_data['_id']

    _filter = {
        "type": "subset",
        "parent": io.ObjectId(str(asset_id)),
        "name": 'modelDefault'
    }
    model_data = io.find_one(_filter)

    # If subset name without "Default"
    if not model_data:
        _filter = {
            "type": "subset",
            "parent": io.ObjectId(str(asset_id)),
            "data.families": "reveries.model"
        }
        model_data = io.find_one(_filter)
    if not model_data:
        raise RuntimeError(
            "Asset \"{}\" : Get modelDefault failed.".format(asset_name))

    files = get_publish_files.get_files(model_data['_id']).get('USD', [])

    return files[0] if files else ''


def prim_export(asset_name, output_path, prim_type='default'):
    # Get variant data
    variant_data, variant_key = _get_variant_data(
        asset_name, prim_type=prim_type
    )

    # Check prim name
    if prim_type == 'proxy':
        prim_name = 'modelDefaultProxy'
    else:
        prim_name = 'modelDefault'

    # Get model usd file
    # geom_file_path = _get_geom_usd(asset_name)

    # Create USD file
    stage = Usd.Stage.CreateInMemory()
    root_define = UsdGeom.Xform.Define(stage, "/ROOT")

    variants = root_define.GetPrim().\
        GetVariantSets().AddVariantSet("appearance")

    # Get default look option name
    default_key = ''
    for _key in variant_data.keys():
        match = re.findall('(\S+default)', _key.lower())
        if match:
            default_key = _key
    default_key = default_key or variant_data.keys()[0]

    for _key in variant_key:
        if prim_type == 'proxy':
            usd_file_paths = variant_data.get('{}Proxy'.format(_key), [])
            if not usd_file_paths:
                usd_file_paths = variant_data.get('lookDefaultProxy', [])
        else:
            usd_file_paths = variant_data.get(_key, [])
        variants.AddVariant(_key)
        variants.SetVariantSelection(_key)

        #
        with variants.GetVariantEditContext():
            # Add step variants
            UsdGeom.Xform.Define(stage, "/ROOT/{}".format(prim_name))
            _prim = stage.GetPrimAtPath("/ROOT/{}".format(prim_name))
            # _usd_paths = [
            #     Sdf.Reference(geom_file_path)
            # ]
            _usd_paths = []
            for ref_path in usd_file_paths:
                _usd_paths.append(Sdf.Reference(ref_path))

            _prim.GetReferences().SetReferences(_usd_paths)

    variants.SetVariantSelection(default_key)

    # Set default prim
    root_prim = stage.GetPrimAtPath('/ROOT')
    stage.SetDefaultPrim(root_prim)

    # print(stage.GetRootLayer().ExportToString())
    stage.GetRootLayer().Export(output_path)
