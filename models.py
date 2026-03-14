# used ChatGPT to help write this code; added comments where appropriate.
from sqlalchemy import Column, Integer, String
from database import Base

class Application(Base):
    __tablename__ = "applications"

    # these are all the parameters the user could enter, with some being optional
    #these are extensively used in routes.py file
    id = Column(Integer, primary_key=True, index=True) # specify value types for all data the user can enter for a specific job application
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    status = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    recruitmentinfo = Column(String, nullable=True) #if nullable=true the parameter is optional
    resume_path = Column(String, nullable=True) 
    jobpostinglink = Column(String, nullable=True) 