import os
from uuid import UUID

admins_id = os.getenv("ADMINS_ID")
list_admins_id = admins_id.split(",") if admins_id else []

class Settings:
    admins_id: list[UUID] = [UUID(id) for id in list_admins_id]

settings = Settings()