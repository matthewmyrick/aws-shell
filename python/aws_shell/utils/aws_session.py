"""boto3 session management."""
import boto3
from rich.console import Console

console = Console()


class AWSSessionManager:
    def __init__(self, config):
        self.config = config
        self._session = None
        self._clients = {}
        self._account_id_cache = None
        self._rebuild_session()

    def _rebuild_session(self):
        self._clients.clear()
        self._account_id_cache = None
        try:
            self._session = boto3.Session(
                profile_name=self.config.profile,
                region_name=self.config.region,
            )
        except Exception as e:
            console.print(f"[bold red]Session error:[/bold red] {e}")
            self._session = boto3.Session(region_name=self.config.region)

    def client(self, service_name):
        key = f"{service_name}:{self.config.region}:{self.config.profile}"
        if key not in self._clients:
            self._clients[key] = self._session.client(
                service_name, region_name=self.config.region
            )
        return self._clients[key]

    def switch_profile(self, profile):
        self.config.set_profile(profile)
        self._rebuild_session()

    def switch_region(self, region):
        self.config.set_region(region)
        self._rebuild_session()

    def get_caller_identity(self):
        sts = self.client("sts")
        return sts.get_caller_identity()

    def get_account_id_cached(self):
        if self._account_id_cache is None:
            try:
                identity = self.get_caller_identity()
                self._account_id_cache = identity["Account"]
            except Exception:
                self._account_id_cache = "N/A"
        return self._account_id_cache

    def get_available_services(self):
        return self._session.get_available_services()
