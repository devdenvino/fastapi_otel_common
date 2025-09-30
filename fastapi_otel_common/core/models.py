from pydantic import BaseModel

class UserBase(BaseModel):
    id: str
    email: str
    given_name: str
    family_name: str | None = None
    is_admin: bool = False