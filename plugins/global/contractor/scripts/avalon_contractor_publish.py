"""For remote publish in contractor environment

Currently used for publishing in Deadline machines.

(NOTE) This script is located by avalon-config module relative path, so if
module was loaded from local environment, the script path sent to Deadline
will be local path which highly possible not be able to access by Deadline
slaves.

"""
import logging
import pyblish.api
import pyblish.util

from reveries.utils import publish_results_formatting
from reveries.plugins import parse_contract_environment


log = logging.getLogger("Contractor")

error_raiser = None


def check_success(context):
    for result in publish_results_formatting(context):
        if not result["success"]:
            error_raiser("Publish failed.")


def publish():

    context = pyblish.api.Context()

    log.info("Parsing environment ...")
    try:
        parse_contract_environment(context)
    except Exception as e:
        error_raiser(str(e))

    log.info("Collecting instances ...")
    pyblish.util.collect(context)

    log.info("Validating ...")
    pyblish.util.validate(context)
    check_success(context)

    log.info("Extracting ...")
    pyblish.util.extract(context)

    log.info("Integrating ...")
    pyblish.util.integrate(context)
    check_success(context)

    log.info("Completed.")


def maya_error_raiser():
    """Return a Deadline Maya faild job trigger"""
    from maya import cmds

    def _maya_error_raiser(msg):
        """Trigger Deadline Maya Plugin to faild job
        """
        # "Render failed:" is one of the magic string to trigger faild job.
        # Those magic string were listed in Deadline plugin `MayaBatch.py`
        cmds.error("Render failed: " + msg)

    return _maya_error_raiser


if __name__ == "__main__":
    # Pick a job error raiser before publish
    RAISERS = [
        maya_error_raiser,
    ]
    for raiser in RAISERS:
        try:
            error_raiser = raiser()
        except ImportError:
            pass
        else:
            break
    else:
        error_raiser = log.error

    publish()
