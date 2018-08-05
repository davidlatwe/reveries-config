
import os
import bson
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


def publish():
    # Collect instance name
    #
    assignment = dict()

    os_environ = os.environ
    for key in os_environ:
        if not key.startswith("AVALON_DELEGATED_SUBSET_"):
            continue
        oid_key = key.replace("AVALON_DELEGATED_SUBSET_",
                              "AVALON_DELEGATED_VERSION_ID_")
        num_key = key.replace("AVALON_DELEGATED_SUBSET_",
                              "AVALON_DELEGATED_VERSION_NUM_")
        subset_name = os_environ[key]
        oid = os_environ[oid_key]
        num = int(os_environ[num_key])
        assignment[subset_name] = (bson.ObjectId(oid), num)
        log.info("Assigned subset {0!r}\n\tVer. Num: {1!r}\n\tVer. OID: {2}"
                 "".format(subset_name, num, oid))

    assignment_count = len(assignment)
    log.info("Found {} delegated instances.".format(assignment_count))

    # Continue publish
    #
    log.info("Continuing publish.")
    context = pyblish.util.collect()
    # set flag
    context.data["contractor_accepted"] = True

    log.info("Collecting instances ...")
    instances = context[:]
    for i, instance in enumerate(instances):
        name = instance.data["name"]
        if name in assignment:
            # version lock
            instance.data["version_id"] = assignment[name][0]
            instance.data["version_next"] = assignment[name][1]
            log.info("{} collected.")
        else:
            # Remove not assigned subset instance
            context.pop(i)

    collected_count = len(context)
    log.info("Collected {} instances.".format(collected_count))

    if not collected_count == assignment_count:
        log.warning("Subset count did not match, this is a bug.")

    if len(context) == 0:
        raise ValueError("No instance to publish, this is a bug.")

    pyblish.util.validate(context)
    check_success(context)

    pyblish.util.extract(context)
    check_success(context)

    pyblish.util.integrate(context)
    check_success(context)

    log.info("Completed.")


if __name__ == "__main__":
    publish()
