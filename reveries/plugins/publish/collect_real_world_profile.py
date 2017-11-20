import pyblish.api


class CollectRealWorldProfile(pyblish.api.ContextPlugin):
    """Inject the real world profile into context

    ```
    context.data {
            time:       data time,
            site_host:  working machine's HOSTNAME
            site_ipv4:  working machine's IPv4 address
            site_loca:  working location
            user_name:  user name
            user_dept:  user department
    }
    ```

    """
    label = "Real World Profile"
    order = pyblish.api.CollectorOrder - 0.499

    def process(self, context):
        context.data.update(
            {
                "time": self._get_time(),
                "site_host": self._get_host(),
                "site_ipv4": self._get_ipv4(),
                "site_loca": self._get_location(),
                "user_name": self._get_user_name(),
                "user_dept": self._get_user_department()
            }
        )

    @staticmethod
    def _get_time():
        import avalon.api
        return avalon.api.time()

    @staticmethod
    def _get_host():
        import os
        return os.environ.get('AVALON_SITE_HOSTNAME', 'Unknow')

    @staticmethod
    def _get_ipv4():
        import os
        return os.environ.get('AVALON_SITE_IPV4', 'Unknow')

    @staticmethod
    def _get_location():
        import os
        return os.environ.get('AVALON_SITE_LOCATION', 'Unknow')

    @staticmethod
    def _get_user_name():
        import os
        return os.environ.get('AVALON_USER_NAME', 'Unknow')

    @staticmethod
    def _get_user_department():
        import os
        return os.environ.get('AVALON_USER_DEPT', 'Unknow')
