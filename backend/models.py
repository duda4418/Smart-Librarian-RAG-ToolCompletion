from typing import Optional
from pydantic import BaseModel


class UserQuery(BaseModel):
    id: Optional[str] = None
    user_query: str