from avalon import io


def get_frame_range(shot_name):
    assert shot_name, "Please provide shot name."

    filter = {"type": "asset", "name": shot_name}
    shot_data = io.find_one(filter)
    frame_in = shot_data['data'].get('edit_in', 101)
    frame_out = shot_data['data'].get('edit_out', 120)

    return [frame_in, frame_out]


def asset_type_mapping(asset_type):

    patterns = ["chr", "char", "prp", "prop"]
    lower = asset_type.lower()
    if any(pattern in lower for pattern in patterns):
        return asset_type

    return False


def check_asset_type_from_ns(ns):
    # Get asset type casting
    asset_casting = {}
    if not asset_casting:
        _filter = {"type": "asset"}

        asset_datas = io.find(_filter)
        for asset_data in asset_datas:
            silo = asset_data.get('silo')
            if asset_type_mapping(silo):
                asset_type = asset_type_mapping(silo)
                asset_casting.setdefault(asset_type, list()).append(asset_data['name'])

    for asset_type in asset_casting.keys():
        for _as in asset_casting[asset_type]:
            if _as in ns:
                return asset_type
