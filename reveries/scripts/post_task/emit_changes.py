
import os
import logging

log = logging.getLogger("APTS.emit_changes")


def __main__(*args):
    """Emit file change on task completed even no one cares

    Subscribers would lookup for changes and copy files to local drive if
    any.

    (NOTE) Post task script will not run if task has error.

    Args:
        (DeadlineRepository.Plugins): Plugin object
        (str): Script type name, e.g. "post task"

    """
    # (TODO) Where should I emit to ?
    pass
