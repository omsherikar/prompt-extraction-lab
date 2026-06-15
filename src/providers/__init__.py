"""Pluggable model backends. The Provider interface is intentionally one method wide."""

from src.providers.base import Provider

__all__ = ["Provider"]
