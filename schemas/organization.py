from .base import BaseSchema
from pydantic import Field


class ClinicBase(BaseSchema):
    name: str = Field(..., description="诊所名称")
    contact_person: str = Field(..., description="联系人")
    phone: str = Field(..., description="联系电话")
    address: str = Field(..., description="地址")
    remark: str | None = Field(default=None, description="备注")


class ClinicCreate(ClinicBase):
    pass


class Clinic(ClinicBase):
    id: int
