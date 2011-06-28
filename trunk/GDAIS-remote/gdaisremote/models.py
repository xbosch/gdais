import os
import re
import transaction

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Unicode

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
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

class LogModel(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)
    name = Column(Unicode)
    levelno = Column(Integer)
    levelname = Column(Unicode)
    msg = Column(Unicode)
    date = Column(DateTime)
    exc_text = Column(Unicode)
    exc_info = Column(Unicode)
    equip_id = Column(Integer, ForeignKey('equipments.id'))

    equipment = relationship(
                    EquipmentModel,
                    backref=backref('logs', order_by=id),
                    cascade="all, delete, delete-orphan")

    def __init__(self, name, levelno, levelname, msg, date, exc_text, exc_info, equip_id):
        self.name = name
        self.levelno = levelno
        self.levelname = levelname
        self.msg = msg
        self.date = date
        self.exc_text = exc_text
        self.exc_info = exc_info
        self.equip_id = equip_id

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
