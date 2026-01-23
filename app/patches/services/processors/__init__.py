from abc import ABC, abstractmethod


class BasePatchProcessor(ABC):
    """Base interface for applying stored patch text.

    Processors must interpret the patch format and apply it to the active project.
    """

    @abstractmethod
    async def apply_patch(self, diff: str) -> None:
        raise NotImplementedError
