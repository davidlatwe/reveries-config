
import json
import copy
import logging
import pyblish.api
import pyblish.util

from reveries.utils import publish_results_formatting
from reveries.plugins import parse_contract_environment


log = logging.getLogger("Contractor")


def show_data(context):
    data = copy.deepcopy(context.data)
    data["results"] = publish_results_formatting(context)
    log.info(json.dumps(data, indent=4, sort_keys=True))


def check_success(context):
    for result in publish_results_formatting(context):
        if not result["success"]:
            show_data(context)
            log.error(result["plugin"]["name"])
            log.error(json.dumps(result["error"],
                                 indent=4, sort_keys=True))
            raise RuntimeError(result["error"]["message"])


def publish():

    context = pyblish.api.Context()

    log.info("Parsing environment ...")
    parse_contract_environment(context)

    log.info("Collecting instances ...")
    pyblish.util.collect(context)
    check_success(context)

    log.info("Validating ...")
    pyblish.util.validate(context)
    check_success(context)

    log.info("Extracting ...")
    pyblish.util.extract(context)
    check_success(context)

    log.info("Integrating ...")
    pyblish.util.integrate(context)
    check_success(context)

    log.info("Completed.")


if __name__ == "__main__":
    publish()
