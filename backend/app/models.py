from sqlalchemy import Column, Integer, Text

from .db import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(Text, nullable=False, unique=True, index=True)
    title = Column(Text, nullable=False)
    credits = Column(Text, nullable=True)
    description = Column(Text, nullable=False)
    prerequisites = Column(Text, nullable=True)
