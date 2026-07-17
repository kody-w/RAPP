"""Typed failures for the target-owned RAPP/1 structural core."""

from __future__ import annotations


class RappError(ValueError):
    """Base class carrying a stable machine-readable failure code."""

    def __init__(self, code: str, message: str, *, step: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.step = step


class CanonicalizationError(RappError):
    """The input is outside the RAPP I-JSON/JCS domain."""


class IdentityError(RappError):
    """An identity, stream, or kind does not match the RAPP/1 grammar."""


class SignatureStructureError(RappError):
    """A detached JWS is not structurally conformant."""


class FrameError(RappError):
    """A frame failed one ordered verification-checklist step."""


class EggError(RappError):
    """An egg failed integrity or viability validation."""
