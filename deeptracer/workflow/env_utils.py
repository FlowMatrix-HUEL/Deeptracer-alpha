import pathlib

from dotenv import load_dotenv


class build_env_local:
    def __init__(self):
        self.config_dir = pathlib.Path.home() / ".deeptracer"
        self.config_path = self.config_dir / ".env.local"

    def _ensure_writable_path(self):
        try:
            self.config_dir.mkdir(exist_ok=True)
            with open(self.config_path, "a", encoding="utf-8"):
                pass
        except PermissionError:
            self.config_dir = pathlib.Path.cwd() / ".deeptracer"
            self.config_dir.mkdir(exist_ok=True)
            self.config_path = self.config_dir / ".env.local"

    def _read_entries(self) -> dict[str, str]:
        self._ensure_writable_path()
        if not self.config_path.exists():
            return {}

        entries: dict[str, str] = {}
        for raw_line in self.config_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            entries[key.strip()] = value.strip()
        return entries

    def _write_entries(self, entries: dict[str, str]) -> None:
        self._ensure_writable_path()
        with open(self.config_path, "w", encoding="utf-8") as f:
            for key, value in entries.items():
                f.write(f"{key}={value}\n")

    def creator(self, key):
        self._ensure_writable_path()
        entries = self._read_entries()
        entries.update(
            {
                "COZE_API_TOKEN": key,
                "COZE_BOT_ID": "7583697542664814611",
                "COZE_WORKFLOW_ID": "7582881054093230122",
                "COZE_API_BASE": "https://api.coze.cn",
                "COZE_USER_ID": "Deeptracer_main_application",
                "PORT": "8000",
            }
        )
        print(self.config_path)
        self._write_entries(entries)

    def save_model_config(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        provider: str = "openai",
        temperature: str = "0.2",
    ) -> pathlib.Path:
        entries = self._read_entries()
        entries.update(
            {
                "OPENAI_API_KEY": api_key,
                "OPENAI_BASE_URL": base_url,
                "DEEPTRACER_MODEL_NAME": model_name,
                "DEEPTRACER_MODEL_PROVIDER": provider,
                "DEEPTRACER_MODEL_TEMPERATURE": temperature,
            }
        )
        self._write_entries(entries)
        return self.config_path

    def load(self, override: bool = False) -> pathlib.Path:
        self._ensure_writable_path()
        if self.config_path.exists():
            load_dotenv(self.config_path, override=override)
        return self.config_path

    def get_config_path(self):
        return self.config_path
