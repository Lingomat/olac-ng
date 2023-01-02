from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Archive(Base):
    __tablename__ = 'archives'
    id = Column(String, primary_key=True)
    baseURL = Column(String)
    dateApproved = Column(String)
    def __repr__(self):
            return f'Archive {self.id, self.baseURL}'

class OLAC_ARCHIVE(Base):
    __tablename__ = 'OLAC_ARCHIVE'
    Archive_ID = Column(String, primary_key=True)
    ArchiveURL = Column(String)
    AdminEmail = Column(String)
    Curator = Column(String)
    CuratorTitle = Column(String)
    CuratorEmail = Column(String)
    Institution = Column(String)
    InstitutionURL = Column(String)
    ShortLocation = Column(String)
    Location = Column(String)
    Synopsis = Column(String)
    Access = Column(String)
    ArchivalSubmissionPolicy = Column(String)
    Copyright = Column(String)
    RepositoryName = Column(String)
    RepositoryIdentifier = Column(String)
    SampleIdentifier = Column(String)
    BaseURL	= Column(String)
    OaiVersion = Column(String)
    FirstHarvested = Column(Date)
    LastHarvested = Column(Date)
    LastFullHarvest = Column(Date)
    ArchiveType = Column(String)
    CurrentAsOf = Column(Date)
    ts = Column(Date)
