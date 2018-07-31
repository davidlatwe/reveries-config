
import os
import shutil
import errno
import pyblish.api

from avalon.vendor.six import string_types
from reveries.contractors import find_contractor


class PublishDelegator(pyblish.api.ContextPlugin):
    """Delegate publish integration
    """

    label = "Publish Delegator"
    order = pyblish.api.IntegratorOrder + 0.499

    active_contractors = dict()

    def process(self, context):

        if context.data.get("contractor_accepted"):
            # Already in contractors hand.
            return

        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        for instance in context:
            if instance.data.get("publish") is False:
                continue

            contractor_name = instance.data.get("publish_contractor")
            if contractor_name is None:
                continue

            if not isinstance(contractor_name, string_types):
                raise TypeError("`publish_contractor` should be a string, "
                                "not {}.".format(type(contractor_name)))

            # Find contractor
            if contractor_name not in self.active_contractors:
                contractor = find_contractor(contractor_name)
                if contractor is None:
                    msg = "Undefined contractor: {!r}".format(contractor_name)
                    raise NotImplementedError(msg)

                self.active_contractors[contractor_name] = contractor()

            self.log.info("Delegating {0!r} publishment to {1!r} ..."
                          "".format(instance, contractor_name))

        if len(self.active_contractors) == 0:
            self.log.info("No instance require delegation.")
            return

        # Copy current file for version lock
        self.backup(context)

        # Delegate!
        for contractor in self.active_contractors.values():
            contractor.fulfill(context)

    def backup(self, context):
        current_file = context.data["currentFile"]
        backup_dir = os.path.join(os.path.dirname(current_file),
                                  "_publish_backup_")

        # append time to file name
        backup_file = list(os.path.splitext(os.path.basename(current_file)))
        backup_file.insert(1, "-" + context.data["time"])
        backup_file = "".join(backup_file)

        backup_path = os.path.join(backup_dir, backup_file)

        self.log.info("Backup current file from {}\n\tto -> {}"
                      "".format(current_file, backup_path))

        try:
            os.makedirs(backup_dir)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                self.log.critical("An unexpected error occurred.")
                raise

        shutil.copyfile(current_file, backup_path)
        context.data["currentFile"] = backup_path
