import pathlib
import os
import tempfile

from dotenv import load_dotenv


class build_env_local:
    def __init__(self, config_dir: pathlib.Path | None = None):
        self.config_dir = config_dir or pathlib.Path.home() / ".deeptracer"
        self.config_path = self.config_dir / ".env.local"

    def _ensure_writable_path(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.config_dir.chmod(0o700)
        except OSError:
            pass

    def _read_entries(self) -> dict[str, str]:
        if not self.config_path.exists():
            return {}

        try:
            entries: dict[str, str] = {}
            for raw_line in self.config_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                entries[key.strip()] = _unquote(value.strip())
            return entries
        except OSError:
            return {}

    def _write_entries(self, entries: dict[str, str]) -> None:
        self._ensure_writable_path()
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.config_dir,
                prefix=".env.local.",
                delete=False,
            ) as handle:
                temp_path = pathlib.Path(handle.name)
                try:
                    temp_path.chmod(0o600)
                except OSError:
                    pass
                for key, value in entries.items():
                    handle.write(f"{key}={value}\n")
            temp_path.replace(self.config_path)
            try:
                self.config_path.chmod(0o600)
            except OSError:
                pass
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

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
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        provider: str | None = None,
        temperature: str | None = None,
    ) -> pathlib.Path:
        entries = self._read_entries()
        updates = {
            "OPENAI_API_KEY": api_key,
            "OPENAI_BASE_URL": base_url,
            "OPENAI_MODEL": model_name,
            "DEEPTRACER_MODEL_NAME": model_name,
            "DEEPTRACER_MODEL_PROVIDER": provider,
            "DEEPTRACER_MODEL_TEMPERATURE": temperature,
        }
        entries.update({key: value for key, value in updates.items() if value is not None})
        self._write_entries(entries)
        return self.config_path

    def set_agents_enabled(self, enabled: bool) -> pathlib.Path:
        entries = self._read_entries()
        entries["DEEPTRACER_AGENTS_ENABLED"] = "true" if enabled else "false"
        self._write_entries(entries)
        return self.config_path

    def load(self, override: bool = False) -> pathlib.Path:
        if self.config_path.exists():
            try:
                load_dotenv(self.config_path, override=override)
            except OSError:
                pass
        return self.config_path

    def get_config_path(self):
        return self.config_path


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
