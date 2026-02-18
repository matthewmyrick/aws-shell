"""Shell configuration state."""
import os


class ShellConfig:
    def __init__(self):
        self.profile = os.environ.get("AWS_PROFILE", "default")
        self.region = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
        self.output_format = "table"

    def set_profile(self, profile):
        self.profile = profile

    def set_region(self, region):
        self.region = region

    def set_output(self, fmt):
        if fmt in ("table", "json", "text"):
            self.output_format = fmt
            return True
        return False
