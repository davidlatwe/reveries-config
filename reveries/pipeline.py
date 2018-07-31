
import tempfile
import pyblish.api
import avalon

from pyblish_qml.ipc import formatting


PENDING_SUFFIX = "__pending"


def temp_dir():
    """Provide a temporary directory
    This temporary directory is generated through `tempfile.mkdtemp()`
    """
    return tempfile.mkdtemp()


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


class ExtractionDelegator(pyblish.api.InstancePlugin):

    delegating = False

    def delegation_check(self, instance):
        use_contractor = instance.data.get("use_contractor")
        accepted = instance.context.data.get("contractor_accepted")
        if use_contractor and not accepted:
            self.delegating = True
        else:
            self.delegating = False

    def process(self, instance):
        self.delegation_check(instance)

        if "files" not in instance.data:
            instance.data["files"] = list()

        if self.delegating:
            self.delegate(instance)
        else:
            self.extract(instance)

    def delegate(self, instance):
        raise NotImplementedError

    def extract(self, instance):
        raise NotImplementedError


def with_pending_ext(ext_list):
    return ext_list[:] + [ext + PENDING_SUFFIX for ext in ext_list]


def publish_results_formatting(context):
    formatted = []
    for result in context.data["results"]:
        formatted.append(formatting.format_result(result))
    return formatted
