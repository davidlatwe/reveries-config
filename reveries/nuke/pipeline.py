
import os
import logging
import nuke

from .. import utils


log = logging.getLogger("reveries.nuke")


def eval_deferred(func, *args, **kwargs):
    def _deferred():
        func(*args, **kwargs)
        nuke.callbacks.removeUpdateUI(_deferred)
    nuke.callbacks.addUpdateUI(_deferred)


def is_locked():
    if _ignore_lock["_"]:
        return False

    def is_publish_source(filename):
        return os.path.dirname(filename).endswith("_published")

    def is_published_script(filename):
        return "/publish/" in filename

    root = nuke.Root()
    filename = root.name()
    if os.path.isfile(filename):
        if is_publish_source(filename) or is_published_script(filename):
            return True
    return False


def is_write_locked(write):
    if _ignore_lock["_"]:
        return False

    output = write["file"].value()
    return "/publish/" in output


_ignore_lock = {"_": False}


def unlock():
    _ignore_lock["_"] = True


def lock():
    _ignore_lock["_"] = False


def set_global_timeline(project):
    start, end, fps = utils.compose_timeline_data(project)
    log.info("Setup project timeline: %d-%d @%f FPS"
             "" % (start, end, fps))

    root = nuke.Root()
    root["first_frame"].setValue(start)
    root["last_frame"].setValue(end)
    root["fps"].setValue(fps)


def set_global_resolution(project):
    width, height = utils.get_resolution_data(project)
    log.info("Setup project resolution: %dx%d"
             "" % (width, height))

    root = nuke.Root()
    for format in nuke.formats():
        if format.width() == width and format.height() == height:
            root["format"].setValue(format.name())
            break


def set_stereo():
    stereo = """
left #ff0000
right #00ff00
"""
    log.info("Setup stereo views")

    root = nuke.Root()
    root.knob("views").fromScript(stereo)
    root.knob("views_colours").setValue(True)
