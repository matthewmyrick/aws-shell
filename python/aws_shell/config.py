"""Shell configuration state with YAML persistence."""
import os


class ShellConfig:
    def __init__(self, config_path=None):
        self._config_path = config_path or os.path.expanduser("~/.aws-shell/config.yaml")
        self._data = {}
        self._load()

        self.profile = os.environ.get("AWS_PROFILE") or self._data.get("profile", "default")
        self.region = os.environ.get("AWS_DEFAULT_REGION") or self._data.get("region", "us-east-2")
        self.output_format = self._data.get("output_format", "table")

        # LLM settings — env vars override config file
        llm = self._data.get("llm", {})
        self.llm_provider = llm.get("provider", "anthropic")
        self.llm_api_key = os.environ.get("ANTHROPIC_API_KEY") or llm.get("api_key", "")
        self.llm_model = os.environ.get("AWS_SHELL_LLM_MODEL") or llm.get("model", "claude-sonnet-4-20250514")

    def _load(self):
        """Load YAML config from disk if it exists."""
        if not os.path.exists(self._config_path):
            return
        try:
            import yaml
            with open(self._config_path, "r") as f:
                loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                self._data = loaded
        except Exception:
            pass

    def _save(self):
        """Write config to YAML, creating directory if needed. File mode 0600."""
        import yaml
        config_dir = os.path.dirname(self._config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, mode=0o700, exist_ok=True)

        # Sync current runtime values back to _data
        self._data["profile"] = self.profile
        self._data["region"] = self.region
        self._data["output_format"] = self.output_format
        self._data.setdefault("llm", {})
        self._data["llm"]["provider"] = self.llm_provider
        self._data["llm"]["api_key"] = self.llm_api_key
        self._data["llm"]["model"] = self.llm_model

        fd = os.open(self._config_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            yaml.dump(self._data, f, default_flow_style=False, sort_keys=False)

    def set_config(self, key, value):
        """Set a config value using dot notation (e.g. 'llm.api_key')."""
        parts = key.split(".")
        if len(parts) == 1:
            setattr(self, parts[0], value)
            self._data[parts[0]] = value
        elif len(parts) == 2:
            section, field = parts
            # Update the nested _data dict
            if section not in self._data:
                self._data[section] = {}
            self._data[section][field] = value
            # Update the flat runtime attribute
            attr_name = f"{section}_{field}"
            if hasattr(self, attr_name):
                setattr(self, attr_name, value)
        self._save()

    def set_profile(self, profile):
        self.profile = profile

    def set_region(self, region):
        self.region = region

    def set_output(self, fmt):
        if fmt in ("table", "json", "text"):
            self.output_format = fmt
            return True
        return False
