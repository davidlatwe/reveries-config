
import os
import json
import copy
import logging
import pyblish.api
import pyblish.util

from reveries.utils import publish_results_formatting


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


def parse_environment(context):
    assignment = dict()
    os_environ = os.environ

    context_prefix = "AVALON_CONTEXT_"
    instance_prefix = "AVALON_DELEGATED_SUBSET_"
    version_prefix = "AVALON_DELEGATED_VERSION_NUM_"

    for key in os_environ:

        if key.startswith(context_prefix):
            # Read Context data
            #
            entry = key[len(context_prefix):]
            context.data[entry] = os_environ[key]

        if key.startswith(instance_prefix):
            # Read Instances' name and version
            #
            num_key = key.replace(instance_prefix, version_prefix)
            subset_name = os_environ[key]
            version_num = int(os_environ[num_key])

            assignment[subset_name] = version_num
            log.info("Assigned subset {0!r}\n\tVer. Num: {1!r}"
                     "".format(subset_name, version_num))

    log.info("Found {} delegated instances.".format(len(assignment)))

    # set flag
    context.data["contractor_accepted"] = True
    context.data["contractor_assignment"] = assignment


def publish():

    context = pyblish.api.Context()

    log.info("Parsing environment ...")
    parse_environment(context)

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
