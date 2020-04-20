
import os
from . import lib


def on_task_changed(*args):
    print("Running callback on task changed..")


def on_save(*args):
    print("Running callback on save..")

    nodes = lib.get_id_required_nodes()
    for node, new_id in lib.generate_ids(nodes):
        lib.set_id(node, new_id, overwrite=False)

    _set_JOB()


def before_save(*args):
    print("Running callback before save..")
    # (NOTE) Was trying to implement scene lock but since Houdini has
    #        a awesome backup saving mechanism, let's not complicate
    #        things.
    # (NOTE) The hip file that returned from `hou.hipFile.path()` is
    #        already been deleted at this moment.


def on_open(*args):
    print("Running callback on open..")

    _set_JOB()

    # (TODO) Pop scene inventory if any outdated


def _set_JOB():
    import hou
    import avalon

    cache_root = os.environ.get("AVALON_CACHE_ROOT")
    project_root = avalon.Session["AVALON_PROJECTS"]
    hipdir = os.path.dirname(hou.hipFile.path())
    if cache_root and os.path.isdir(hipdir):
        JOB = hipdir.replace(project_root, cache_root, 1)
        os.environ["JOB"] = JOB
        if not os.path.isdir(JOB):
            os.makedirs(JOB)
    else:
        os.environ["JOB"] = ""
