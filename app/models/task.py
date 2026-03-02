from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Column(Integer, primary_key=True, index=True)
    title: Column(String, nullable=False)
    description: Column(String, nullable=True)
    user_id: Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    user: relationship("User", back_populates="tasks")
