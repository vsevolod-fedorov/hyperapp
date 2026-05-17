from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceModuleSource:
    name: str


@dataclass(frozen=True)
class TextSource:
    text: str
