
from . import pipeline


def on_task_changed(*args):
    pipeline.set_global_resolution()
    pipeline.set_global_timeline()


def on_save():
    _lock_published_script()


def on_load():
    pass


def _lock_published_script():
    message = """
Published script is locked, and can not be overwritten.
Please save the script in new name."""

    if pipeline.is_locked():
        raise Exception(message)
