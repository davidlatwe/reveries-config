from avalon import io


def get(shot_name):
    assert shot_name, "Please provide shot name."

    _filter = {"type": "asset", "name": shot_name}
    shot_data = io.find_one(_filter)
    frame_in = shot_data['data'].get('edit_in', None)
    frame_out = shot_data['data'].get('edit_out', None)

    # Get frame range from shotgun
    if not frame_in and not frame_out:
        from reveries.common.shotgun_io import ShotgunIO

        show_data = io.find_one({'type': 'project'}, projection={"name": True})
        shotgun = ShotgunIO(db_show_name=show_data['name'])

        shotgun_shot_name = _mapping_shot_name_to_shotgun(shot_name)
        print("shotgun_shot_name from db: {}\n".format(shotgun_shot_name))
        if shotgun_shot_name:
            _frame_ranges = shotgun.get_frame_range(shotgun_shot_name)
            frame_in = _frame_ranges.get("sg_cut_in", None)
            frame_out = _frame_ranges.get("sg_cut_out", None)

    # Get frame range from project
    if not frame_in and not frame_out:
        print("Get frame range from project data.")

        _filter = {"type": "project"}
        project_data = io.find_one(_filter)
        frame_in = project_data["data"]["edit_in"]
        frame_out = project_data["data"]["edit_out"]

    print("frame range: {}-{}.".format(frame_in, frame_out))
    return [frame_in, frame_out]


def _mapping_shot_name_to_shotgun(shot_name):
    _filter = {"type": "asset", "name": shot_name}
    shot_data = io.find_one(_filter)
    seq_name = shot_data["data"].get("group", None)
    if not seq_name:
        print("Can't get sequence name for shot \"{}\".".format(shot_name))
        return False

    short_shot_name = shot_data["data"]["label"].split("_")[1]
    # Get shotgun shot name template
    _filter = {"type": "project"}
    project_data = io.find_one(_filter)
    shotgun_shot_name_template = project_data["config"]["template"].get("shotgun_shot_name", None)

    if not shotgun_shot_name_template:
        print("Can't get template for shot \"{}\".".format(shot_name))
        return False

    shotgun_shot_name = shotgun_shot_name_template.format(
        seq_name=seq_name,
        shot_name=short_shot_name
    )

    # TODO: Need to find a better way to fix sequence/shot name is different between avalon and shotgun
    if project_data["name"] in ["201912_ChimelongPreshow"]:
        # Fix sequence for ChimelongPreshow
        shotgun_shot_name = shotgun_shot_name.replace("SEQ", "Seq")

    return shotgun_shot_name
