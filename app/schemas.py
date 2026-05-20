import uuid

from pydantic import BaseModel


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str

    model_config = {"from_attributes": True}
