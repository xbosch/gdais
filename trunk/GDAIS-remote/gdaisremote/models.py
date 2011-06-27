import os
import re
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
    running = Column(Boolean)

    def __init__(self, name, desc):
        self.name = name
        self.desc = desc
        self.running = False

def populate():
    here = os.path.dirname(os.path.abspath(__file__))
    gdais_path = os.path.normpath(os.path.join(here, '..', '..', 'GDAIS-core'))
    equips_path = os.path.join(gdais_path, 'conf', 'equips')

    test = re.compile("\.json$", re.IGNORECASE)
    filenames = filter(test.search, os.listdir(equips_path))

    session = DBSession()
    for fn in filenames:
        e = EquipmentModel(name=os.path.splitext(fn)[0], desc=fn)
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

# vim: et ts=4 sw=4
