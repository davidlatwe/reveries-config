
import os
import tempfile
import hashlib
import base64
import shutil

import pyblish.api
import avalon
from pyblish_qml.ipc import formatting


def temp_dir(prefix=""):
    """Provide a temporary directory
    This temporary directory is generated through `tempfile.mkdtemp()`
    """
    return tempfile.mkdtemp(prefix=prefix)


def clear_stage(prefix="tmp"):
    tempdir = tempfile.gettempdir()
    cwd_backup = os.getcwd()

    os.chdir(tempdir)
    for item in os.listdir(tempdir):
        if not (os.path.isdir(item) and item.startswith(prefix)):
            continue

        # Remove
        full_path = os.path.join(tempdir, item)
        print("Removing {!r}".format(full_path))
        shutil.rmtree(full_path)
        print("Removed.")

    os.chdir(cwd_backup)


def get_timeline_data():
    project = avalon.io.find_one({"type": "project"})
    asset = avalon.Session["AVALON_ASSET"]
    asset = avalon.io.find_one({"name": asset, "type": "asset"})

    def get_time(key):
        try:
            value = asset["data"][key]
        except KeyError:
            value = project["data"][key]
        return value

    edit_in = get_time("edit_in")
    edit_out = get_time("edit_out")
    handles = get_time("handles")
    fps = get_time("fps")

    if handles < 1:
        # (TODO) davidlatwe
        # Should not validate at here, need `project.data` schema to do that.
        raise ValueError("Incorrect value `Handles`: {}".format(handles))

    return edit_in, edit_out, handles, fps


def compose_timeline_data():
    edit_in, edit_out, handles, fps = get_timeline_data()
    start_frame = edit_in - handles
    end_frame = edit_out + handles

    return start_frame, end_frame, fps


def get_resolution_data():
    project = avalon.io.find_one({"type": "project"})
    resolution_width = project["data"].get("resolution_width", 1920)
    resolution_height = project["data"].get("resolution_height", 1080)
    return resolution_width, resolution_height


def publish_results_formatting(context):
    formatted = []
    for result in context.data["results"]:
        formatted.append(formatting.format_result(result))
    return formatted


def hash_file(file_path):
    hash_obj = hashlib.sha512()

    chunk_size = 40960  # magic number

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            hash_obj.update(chunk)

    digested = hash_obj.digest()
    hash_val = base64.urlsafe_b64encode(digested)

    return hash_val[:-2]  # length is fixed, remove padding "=="


def plugins_by_range(base=1.5, extend=2, paths=None):
    """Find plugins by thier order which fits in range

    Default param will return order from -0.5 ~ 3.5, which is standard
    range of Pyblish CVEI order.

    C = 0 +-0.5
    V = 1 +-0.5
    E = 2 +-0.5
    I = 3 +-0.5

    """
    order_min = base - extend
    order_max = base + extend

    plugins = list()

    for plugin in pyblish.api.discover(paths=paths):
        if ("order" in plugin.__dict__ and
                order_min <= plugin.order and
                order_max >= plugin.order):

            plugins.append(plugin)

    return plugins
