from avalon import io


def get_fps():
    _filter = {"type": "project"}
    project_data = io.find_one(_filter) or {}

    _fps = project_data.get("data", {}).get("fps", 24.0)
    return _fps
