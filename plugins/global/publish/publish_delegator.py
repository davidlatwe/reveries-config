
import pyblish.api

from reveries.vendor.six import string_types
from reveries.plugins import find_contractor


class PublishDelegator(pyblish.api.ContextPlugin):
    """Delegate publish integration
    """

    label = "Publish Delegator"
    order = pyblish.api.IntegratorOrder + 0.499

    active_contractors = dict()

    def process(self, context):

        if context.data.get("contractor_accepted"):
            # Already in contractor's hand.
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
                Contractor = find_contractor(contractor_name)
                if Contractor is None:
                    msg = "Undefined Contractor: {!r}".format(contractor_name)
                    raise NotImplementedError(msg)

                self.active_contractors[contractor_name] = Contractor()

            self.log.info("Delegating {0!r} publishment to {1!r} ..."
                          "".format(instance, contractor_name))

        if len(self.active_contractors) == 0:
            self.log.info("No instance require delegation.")
            return

        # Delegate!
        for contractor in self.active_contractors.values():
            contractor.fulfill(context)
