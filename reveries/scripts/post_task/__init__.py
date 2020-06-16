
import os
import logging
import avalon.lib
import pyblish.lib

log = logging.getLogger("APTS")
log.setLevel(logging.INFO)

formatter = logging.Formatter("%(name)-24s: %(levelname)-8s %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.addHandler(handler)


def __main__(*args):
    """An entry script for multiple post task scripts

    This script will lookup script names from job property's environment key
    `AVALON_POST_TASK_SCRIPTS`.

    The script must be in `reveries.scripts.post_task` and must have function
    `__main__` defined.

    (NOTE) Post task script will not run if task has error.

    Args:
        (DeadlineRepository.Plugins): Plugin object
        (str): Script type name, e.g. "post task"

    """
    deadlinePlugin = args[0]
    job = deadlinePlugin.GetJob()

    script_names = job.GetJobEnvironmentKeyValue("AVALON_POST_TASK_SCRIPTS")
    if not script_names:
        log.warning("No Avalon post task script found.")
        return

    # Collect and exec plugins (scripts)
    #
    script_dir = os.path.dirname(__file__)
    modules = {
        module.__name__: module
        for module in avalon.lib.modules_from_path(script_dir)
    }

    for name in script_names.split(";"):

        script = modules.get(name)
        if script:

            log.info("Run Avalon post task script: %s" % name)

            try:
                script.__main__(*args)

            except Exception as error:
                # Deadline will requeue the task if error raised in
                # post task script.

                pyblish.lib.extract_traceback(error, script.__file__)
                message = "{p.__name__} Error: {e} -- {e.traceback}"

                log.error(message.format(p=script, e=error))

                # (TODO) Fail the task if error raised ?
