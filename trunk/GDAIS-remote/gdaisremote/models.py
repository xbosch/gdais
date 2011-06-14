import transaction

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import Boolean

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

class EquipmentModel(Base):
    __tablename__ = 'equipments'
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(255), unique=True)
    desc = Column(Unicode)
    running = Boolean()

    def __init__(self, name, desc):
        self.name = name
        self.desc = desc
        self.running = False

def populate():
    session = DBSession()
    e = EquipmentModel(name=u'prova1', desc=u'equip de prova sense res util')
    session.add(e)
    session.flush()
    transaction.commit()
    
def initialize_sql(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    try:
        populate()
    except IntegrityError:
        DBSession.rollback()
