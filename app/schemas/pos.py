from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_serializer


class ShiftReconciliationRequest(BaseModel):
    """Payload for creating or updating a POS shift reconciliation record."""

    session_id: str = Field(..., description="POS session identifier")
    float_given: Decimal = Field(default=Decimal('0'), description="Opening float provided to the cashier")
    cash_collected: Decimal = Field(default=Decimal('0'), description="Cash counted at the end of the shift")
    shift_date: Optional[date] = Field(default=None, description="Business date for the shift")
    notes: Optional[str] = Field(default=None, description="Manager notes or observations")
    verified_by: Optional[str] = Field(default=None, description="User ID of the verifier/manager")

    model_config = ConfigDict()

    @field_serializer('float_given', 'cash_collected', mode='plain')
    def _serialize_decimal(cls, value: Decimal) -> str:
        """Render decimals as strings to avoid binary float artifacts."""
        return str(value)
