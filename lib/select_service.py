from lib.services import LinkedInService, GenericService


class SelectService:

    @classmethod
    def select_service(cls, host):
        known_hosts = {
            'linkedin.com': LinkedInService,
            'www.linkedin.com': LinkedInService,
        }
        return known_hosts.get(host, GenericService)
