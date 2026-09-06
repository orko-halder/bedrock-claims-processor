"""
Prompt Template Manager. Templates live as versioned .txt files in
prompts/, not as f-strings inside pipeline code — so you can edit or
version a prompt without touching Python.
"""

import os
from string import Template

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


class PromptTemplateManager:
    def __init__(self, prompts_dir: str = PROMPTS_DIR):
        self.prompts_dir = prompts_dir
        self._cache: dict[str, Template] = {}

    def get(self, name: str, version: str = "v1") -> Template:
        key = f"{name}__{version}"
        if key not in self._cache:
            path = os.path.join(self.prompts_dir, f"{name}.{version}.txt")
            with open(path, encoding="utf-8") as f:
                self._cache[key] = Template(f.read())
        return self._cache[key]

    def render(self, name: str, version: str = "v1", **kwargs) -> str:
        return self.get(name, version).substitute(**kwargs)
