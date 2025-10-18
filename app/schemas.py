# app/schemas.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# --- Compat layer para Pydantic v1/v2 ---
# - En v2 usamos model_validator (after)
# - En v1 caemos a root_validator
try:
    from pydantic import model_validator  # v2
    PVD = 2
except Exception:  # v1
    from pydantic import root_validator   # type: ignore
    PVD = 1


# ---------- Create ----------
class UserCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_company: bool = False
    company_name: Optional[str] = None
    password: str = Field(min_length=8)
    confirm_password: str

    if PVD == 2:
        @model_validator(mode="after")
        def _v2_passwords_match(self):
            if self.password != self.confirm_password:
                raise ValueError("password and confirm_password must match")
            return self

        @model_validator(mode="after")
        def _v2_normalize_company(self):
            if not self.is_company:
                object.__setattr__(self, "company_name", None)
            else:
                if not (self.company_name and self.company_name.strip()):
                    raise ValueError("company_name is required when is_company=True")
            return self
    else:
        @root_validator  # type: ignore
        def _v1_normalize_and_validate(cls, values):
            if values.get("password") != values.get("confirm_password"):
                raise ValueError("password and confirm_password must match")
            if not values.get("is_company"):
                values["company_name"] = None
            else:
                cn = values.get("company_name")
                if not (cn and cn.strip()):
                    raise ValueError("company_name is required when is_company=True")
            return values


# ---------- Update ----------
class UserUpdate(BaseModel):
    # Todos opcionales para partial update
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_company: Optional[bool] = None
    company_name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)
    confirm_password: Optional[str] = None

    if PVD == 2:
        from pydantic import model_validator  # type: ignore

        @model_validator(mode="after")
        def _v2_passwords_match(self):
            # Si cambian la clave, deben venir ambos y ser iguales
            if (self.password is not None or self.confirm_password is not None) and (
                self.password != self.confirm_password
            ):
                raise ValueError("password and confirm_password must match")
            return self

        @model_validator(mode="after")
        def _v2_normalize_company(self):
            if self.is_company is False:
                object.__setattr__(self, "company_name", None)
            if self.is_company is True and self.company_name is not None and not self.company_name.strip():
                raise ValueError("company_name must not be empty when is_company=True")
            return self
    else:
        @root_validator  # type: ignore
        def _v1_normalize_and_validate(cls, values):
            pw, cpw = values.get("password"), values.get("confirm_password")
            if (pw is not None or cpw is not None) and pw != cpw:
                raise ValueError("password and confirm_password must match")
            if values.get("is_company") is False:
                values["company_name"] = None
            if values.get("is_company") is True and values.get("company_name") is not None:
                if not values["company_name"].strip():
                    raise ValueError("company_name must not be empty when is_company=True")
            return values


# ---------- Out ----------
class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_company: bool
    company_name: Optional[str] = None
    active: bool
    created_at: datetime

    class Config:
        # v2 (from_attributes) y v1 (orm_mode) para compatibilidad
        try:
            from_attributes = True  # v2
        except Exception:
            orm_mode = True         # v1
