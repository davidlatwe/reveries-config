
import os
import logging
import avalon.lib
import pyblish.lib

from Deadline.Scripting import RepositoryUtils

log = logging.getLogger("APTS")
log.setLevel(logging.INFO)

if not log.handlers:
    formatter = logging.Formatter("%(name)-24s: %(levelname)-8s %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)


def __main__(*args):
    """An entry script for multiple post task scripts (chained)

    This script will lookup script names from job property's environment key
    `AVALON_POST_TASK_SCRIPTS`.

    The script must be in `reveries.scripts.post_task` and must have function
    `__main__` defined.

    The process will NOT continue if any error raised in scripts. (chained)

    (NOTE) Post task script will not run if task has error.

    Args:
        (DeadlineRepository.Plugins): Plugin object
        (str): Script type name, e.g. "post task"

    """
    deadline_plugin = args[0]
    job = deadline_plugin.GetJob()
    task = deadline_plugin.GetCurrentTask()

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

                pyblish.lib.extract_traceback(error, script.__file__)
                message = "{p.__name__} Error: {e} -- {e.traceback}"

                log.error(message.format(p=script, e=error))

                # Fail the task if error raised and stop running the rest of
                # of the scripts.
                RepositoryUtils.FailTasks(job, [task])
                break

                # (NOTE) Change to Failed state so Deadline won't requeue the
                #   task, since the error being raised here most likely not
                #   able to be resolved by re-run the task again.
                #   If it could, define and raise a custom type of error and
                #   handling it in another except statement.
