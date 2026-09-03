"""
Shared domain type aliases.
"""
from typing import Any, TypeAlias
from uuid import UUID

JSONDict: TypeAlias = dict[str, Any]
UUIDStr: TypeAlias = str
IDType: TypeAlias = UUID | str
