from lib.services import LinkedInService, GenericService

from urllib.parse import urlparse

KNOWN_HOSTS = {
    "linkedin.com": LinkedInService,
}


class SelectService:
    def __init__(self, host):
        self.host = host
        self.service = self.select_service(host)

    def select_service(self, host):
        trimmed_host = self.get_hostname(host)
        return KNOWN_HOSTS.get(trimmed_host, GenericService)

    def get_creds(self, secrets) -> dict:
        """Shove in the secrets yml and get specific creds for the derived service."""
        trimmed_host = self.get_hostname(self.host)
        return secrets.get(trimmed_host)

    def get_hostname(self, url):
        # Parse the URL
        parsed_url = urlparse(url)

        # Extract the hostname
        hostname = parsed_url.hostname

        if not hostname:
            return None

        # Split the hostname into subdomains
        parts = hostname.split(".")

        # Check if the first part is 'www'
        if parts[0].lower() == "www":
            # Remove 'www' and rebuild the hostname
            return ".".join(parts[1:])
        else:
            return hostname
