
from . import lib


def on_task_changed(*args):
    print("Running callback on task changed..")


def on_save(*args):
    print("Running callback on save..")

    nodes = lib.get_id_required_nodes()
    for node, new_id in lib.generate_ids(nodes):
        lib.set_id(node, new_id, overwrite=False)


def before_save(*args):
    print("Running callback before save..")
    # (NOTE) Was trying to implement scene lock but since Houdini has
    #        a awesome backup saving mechanism, let's not complicate
    #        things.
    # (NOTE) The hip file that returned from `hou.hipFile.path()` is
    #        already been deleted at this moment.


def on_open(*args):
    print("Running callback on open..")
    # (TODO) Pop scene inventory if any outdated
