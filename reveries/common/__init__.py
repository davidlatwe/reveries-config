from avalon import io


def skip_instance(context, family_name):
    """
    Skip process if instance exists.
    :param context: (obj) Instance context
    :param family_name: (str/list) F
    :return: bool
    """
    if not isinstance(family_name, list):
        family_name = [family_name]

    _exists = False
    for instance in context:
        if instance.data["family"] in family_name:
            _exists = True
            break
    return _exists


def get_frame_range(shot_name):
    assert shot_name, "Please provide shot name."

    _filter = {"type": "asset", "name": shot_name}
    shot_data = io.find_one(_filter)
    frame_in = shot_data['data'].get('edit_in', None)
    frame_out = shot_data['data'].get('edit_out', None)

    # Get frame range from shotgun
    if not frame_in and not frame_out:
        from reveries.common.shotgun_io import ShotgunIO

        show_data = io.find_one({'type': 'project'}, projection={"name": True})
        shotgun_io = ShotgunIO(db_show_name=show_data['name'])

        shotgun_shot_name = mapping_shot_name_to_shotgun(shot_name)
        print("shotgun_shot_name from db: {}\n".format(shotgun_shot_name))
        if shotgun_shot_name:
            _frame_ranges = shotgun_io.get_frame_range(shotgun_shot_name)
            if _frame_ranges.get("sg_cut_in", None) and _frame_ranges.get("sg_cut_out", None):
                frame_in = _frame_ranges["sg_cut_in"]
                frame_out = _frame_ranges["sg_cut_out"]

    # Get frame range from project
    if not frame_in and not frame_out:
        print("Get frame range from project data.")

        _filter = {"type": "project"}
        project_data = io.find_one(_filter)
        frame_in = project_data["data"]["edit_in"]
        frame_out = project_data["data"]["edit_out"]

    print("frame range: {}-{}.".format(frame_in, frame_out))
    return [frame_in, frame_out]


def mapping_shot_name_to_shotgun(shot_name):
    _filter = {"type": "asset", "name": shot_name}
    shot_data = io.find_one(_filter)
    seq_name = shot_data["data"].get("group", None)
    if not seq_name:
        print "Can't get sequence name for shot \"{}\".".format(shot_name)
        return False

    short_shot_name = shot_data["data"]["label"].split("_")[1]
    # Get shotgun shot name template
    _filter = {"type": "project"}
    project_data = io.find_one(_filter)
    shotgun_shot_name_template = project_data["config"]["template"].get("shotgun_shot_name", None)

    if not shotgun_shot_name_template:
        print "Can't get template for shot \"{}\".".format(shot_name)
        return False

    shotgun_shot_name = shotgun_shot_name_template.format(
        seq_name=seq_name,
        shot_name=short_shot_name
    )

    # TODO: Need to find a better way to fix sequence/shot name is different from avalon and shotgun
    if project_data["name"] in ["201912_ChimelongPreshow"]:
        # Fix sequence for ChimelongPreshow
        shotgun_shot_name = shotgun_shot_name.replace("SEQ", "Seq")

    return shotgun_shot_name


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
