import os
import re
import socket
import subprocess

from pyramid.session import UnencryptedCookieSessionFactoryConfig
from pyramid.view import view_config

from gdaisremote.models import DBSession
from gdaisremote.models import EquipmentModel

#def my_view(request):
#    dbsession = DBSession()
#    root = dbsession.query(MyModel).filter(MyModel.name==u'root').first()
#    return {'root':root, 'project':'GDAIS-remote'}

@view_config(route_name='list', renderer='list.mako')
def list_view(request):
    here = os.path.dirname(os.path.abspath(__file__))
    gdais_path = os.path.join(here, '..', '..', '..', 'GDAIS')
    equips_path = os.path.join(gdais_path, 'conf', 'equips')
    test = re.compile("\.json$", re.IGNORECASE)
    filenames = filter(test.search, os.listdir(equips_path))
#    filepaths = [os.path.join(equips_path, f) for f in filenames]
#    equips = [dict(name=Equipment(fp).name, file=dict(name=fn, path=fp))
#                for fn, fp in zip(filenames, filepaths)]
#    equips = [dict(name=os.path.splitext(fn)[0], file=dict(name=fn, path=fp))
#                for fn, fp in zip(filenames, filepaths)]
    equips = [os.path.splitext(fn)[0] for fn in filenames]
    return dict(equips=equips)

@view_config(route_name='start', renderer='start.mako')
def start_view(request):
    here = os.path.dirname(os.path.abspath(__file__))
    gdais_path = os.path.join(here, '..', '..', '..', 'GDAIS')
    equips_path = os.path.join(gdais_path, 'conf', 'equips')
    equips_path = os.path.normpath(equips_path)

    equip = request.matchdict['equip']
    equip_path = os.path.join(equips_path, equip + '.json')
    main = os.path.join(gdais_path, 'run_bg.sh')

    retcode = subprocess.call([main, equip_path])

    return dict(equip=equip, equip_path=equip_path, retcode=retcode)

@view_config(route_name='stop', renderer='stop.mako')
def stop_view(request):
    error = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', 12345))
        s.send(bytes('quit'))
        s.close()
    except socket.error as msg:
      error = msg

    here = os.path.dirname(os.path.abspath(__file__))
    gdais_path = os.path.join(here, '..', '..', '..', 'GDAIS')
    equips_path = os.path.join(gdais_path, 'conf', 'equips')
    equips_path = os.path.normpath(equips_path)

    equip = request.matchdict['equip']
    equip_path = os.path.join(equips_path, equip + '.json')
    return dict(equip=equip, error=error)

def notfound_view(self):
    return dict()
