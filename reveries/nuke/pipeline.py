
import logging
import nuke

from .. import utils


log = logging.getLogger("reveries.nuke")


def eval_deferred(func, *args, **kwargs):
    def _deferred():
        func(*args, **kwargs)
        nuke.callbacks.removeUpdateUI(_deferred)
    nuke.callbacks.addUpdateUI(_deferred)


def set_global_timeline():
    start, end, fps = utils.compose_timeline_data()
    log.info("Setup project timeline: %d-%d @%f FPS"
             "" % (start, end, fps))

    root = nuke.Root()
    root["first_frame"].setValue(start)
    root["last_frame"].setValue(end)
    root["fps"].setValue(fps)


def set_global_resolution():
    width, height = utils.get_resolution_data()
    log.info("Setup project resolution: %dx%d"
             "" % (width, height))

    root = nuke.Root()
    for format in nuke.formats():
        if format.width() == width and format.height() == height:
            root["format"].setValue(format.name())
            break
