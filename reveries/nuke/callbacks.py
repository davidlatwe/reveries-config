
import nuke
import avalon.io
from . import pipeline


def on_task_changed(*args):
    project = avalon.io.find_one({"type": "project"},
                                 projection={"data": True})
    pipeline.set_global_resolution(project)
    pipeline.set_global_timeline(project)
    if project["data"].get("stereo"):
        pipeline.set_stereo()


def on_save():
    _lock_published_script()


def on_load():
    print("Running callback on load..")
    # (TODO) Pop scene inventory if any outdated


def before_render():
    _lock_published_render()


def _lock_published_script():
    message = """
Published script is locked, and can not be overwritten.
Please save the script in new name."""

    if pipeline.is_locked():
        raise Exception(message)


def _lock_published_render():
    message = """
Output file path contains keyword '/publish/' which indicates
that you are rendering directly to published space and this is
forbidden.
Please pick another output path."""

    if pipeline.is_write_locked(nuke.thisNode()):
        raise Exception(message)
