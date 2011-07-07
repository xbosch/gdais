from collections import namedtuple
from datetime import datetime
import logging
import mimetypes
import os
import re
import socket
import subprocess
import time

from pyramid.exceptions import NotFound
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.session import UnencryptedCookieSessionFactoryConfig
from pyramid.view import view_config

from sqlalchemy.orm.exc import NoResultFound

from gdaisremote.models import DBSession
from gdaisremote.models import EquipmentModel
from gdaisremote.models import LogModel


here = os.path.dirname(os.path.abspath(__file__))
gdais_path = os.path.normpath(os.path.join(here, '..', '..', 'GDAIS-core'))
equips_path = os.path.join(gdais_path, 'conf', 'equips')
data_path = os.path.join(gdais_path, 'data')


@view_config(route_name='list', renderer='list.mako')
def list_equips(request):
    dbsession = DBSession()
    equips = dbsession.query(EquipmentModel).all()
    return dict(equips=equips, reload=True)


@view_config(route_name='view', renderer='view.mako')
def view_equip(request):
    name = request.matchdict['equip']
    equip_path = os.path.join(equips_path, name + '.json')

    dbsession = DBSession()
    try:
        equip = dbsession.query(EquipmentModel).filter_by(name=name).one()
    except NoResultFound:
        request.session.flash("Equipment '{0}' not found".format(name))
        return HTTPFound(location=request.route_url('list'))

    status = 'running' if equip.running else 'stopped'

    Level = namedtuple('Level', 'num name default')
    log_levels = [Level(l, logging.getLevelName(l), l==equip.log_lvl)
                    for l in range(10, 60, 10)]

    files_path = os.path.join(data_path, equip.name)
    try:
        files = sorted(os.listdir(files_path), reverse=True)
    except OSError:
        # there is no instrument folder, no data has been acquired
        files = []
    else:
        test = re.compile("\.h5$", re.IGNORECASE)
        filenames = filter(test.search, files)

        # list of 'sidamon_20110628_152029.h5' -> datetime(2011, 6, 28, 15, 20, 29)
        dates = [datetime.strptime(
                    ''.join(os.path.splitext(f)[0].split(name+'_')[1:]),
                    '%Y%m%d_%H%M%S')
                 for f in filenames]

        sizes = [_sizeof_fmt(os.path.getsize(os.path.join(files_path, f)))
                    for f in filenames]

        files = [dict(name=f, date=d, size=s)
                    for f, d, s in zip(filenames, dates, sizes)]

    return dict(equip=equip, equip_path=equip_path, status=status,
                log_levels=log_levels, files=files)

# http://blogmag.net/blog/read/38/Print_human_readable_file_size
def _sizeof_fmt(num):
    for x in ['bytes', 'kB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0


@view_config(route_name='view_log', renderer='json')
def view_log_equip(request):
    name = request.matchdict['equip']
    dbsession = DBSession()
    equip = dbsession.query(EquipmentModel).filter_by(name=name).one()
    return {'aaData': [
            [l.date.strftime('%Y-%m-%d'), l.date.strftime('%H:%M:%S,%f')[:-3],
                l.name, l.levelname, l.msg]
            for l in equip.logs]}

@view_config(route_name='set_log_level', renderer='json')
def set_log_level(request):
    try:
        level = int(request.matchdict['level'])
    except ValueError:
        return {'status': 'KO', 'error': "Level should be an integer value"}

    if not level in range(10, 60, 10):
        return {'status': 'KO', 'error': "Level should be 10, 20, 30, 40 or 50"}

    name = request.matchdict['equip']
    dbsession = DBSession()
    try:
        equip = dbsession.query(EquipmentModel).filter_by(name=name).one()
    except NoResultFound:
        return {'status': 'KO', 'error': "Equipment '{0}' not found".format(name)}

    if equip.running:
        try:
            # notify GDAIS-core
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('localhost', 12345))
            s.send(bytes('set_log_level {0}'.format(level)))
            s.shutdown(socket.SHUT_WR)
            s.close()

            # save new log level to database
            equip.log_lvl = level
            dbsession.add(equip)

            txt = "'set_log_level {0}' command sent to '{1}'"
            return {'status': 'OK', 'info': txt.format(level, name)}

        except socket.error as msg:
            return {'status': 'KO', 'error': msg}
    else:
        return {'status': 'KO', 'error': "Equipment {0} not running".format(name)}


@view_config(route_name='log')
def log_equip(request):
    name = request.matchdict['equip']

    dbsession = DBSession()
    equip = dbsession.query(EquipmentModel).filter_by(name=name).one()

    if request.method == 'POST':
        timestamp = int(float(request.params['created']))
        timestamp += float(request.params['msecs'])/1000
        exc_text = request.params['exc_text']
        exc_info = request.params['exc_info']

        log = LogModel(
            name = request.params['name'],
            levelno = int(request.params['levelno']),
            levelname = request.params['levelname'],
            msg = request.params['msg'],
            date = datetime.utcfromtimestamp(timestamp),
            exc_text = exc_text if exc_text != 'None' else None,
            exc_info = exc_info if exc_info != 'None' else None,
            equip_id = equip.id)
        dbsession.add(log)

    return Response('OK')


@view_config(route_name='start')
def start_equip(request):
    name = request.matchdict['equip']
    equip_path = os.path.join(equips_path, name + '.json')
    main = os.path.join(gdais_path, 'run.sh')

    dbsession = DBSession()
    try:
        equip = dbsession.query(EquipmentModel).filter_by(name=name).one()
    except NoResultFound:
        request.session.flash("Equipment '{0}' not found".format(name))
        return HTTPFound(location=request.route_url('list'))

    if not equip.running:
        #print "[GDAIS-remote] DEBUG: Calling:", main, '-d', equip_path
        retcode = subprocess.call([main, '-d', equip_path])

        if retcode == 0:
            # delete old log entries
            dbsession.query(LogModel).filter_by(equip_id=equip.id).delete()

            # reset log_lvl to DEBUG
            equip.log_lvl = 10
            dbsession.add(equip)
            
            request.session.flash("Equipment '{0}' process started".format(name))

        elif retcode == 1:
            request.session.flash("Error in equipment start script parameters")

        elif retcode == 2:
            request.session.flash("An equipment already running, only one allowed")

        else:
            txt = "Unknown error starting '{0}' (retcode: {1})".format(name, retcode)
            request.session.flash(txt)
    else:
        request.session.flash("Equipment '{0}' already running".format(name))
        return HTTPFound(location=request.route_url('view', equip=name))

    return HTTPFound(location=request.route_url('list'))


@view_config(route_name='notify_start', renderer='json')
def notify_equip_start(request):
    name = request.matchdict['equip']

    dbsession = DBSession()
    equip = dbsession.query(EquipmentModel).filter_by(name=name).one()
    equip.running = True
    dbsession.add(equip)

    return {'status': 'OK', 'info': name + ' start notified'}


@view_config(route_name='stop')
def stop_equip(request):
    name = request.matchdict['equip']

    dbsession = DBSession()
    try:
        equip = dbsession.query(EquipmentModel).filter_by(name=name).one()
    except NoResultFound:
        request.session.flash("Equipment {0} not found".format(name))
        return HTTPFound(location=request.route_url('list'))

    if equip.running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('localhost', 12345))
            s.send(bytes('quit'))
            s.shutdown(socket.SHUT_WR)
            s.close()
            request.session.flash("Quit command sent to '{0}'".format(name))
            time.sleep(2) # wait until GDAIS-core has stopped
        except socket.error as msg:
            request.session.flash("Error occurred: {0}".format(msg))
    else:
        request.session.flash("Equipment {0} not running".format(name))

    return HTTPFound(location=request.route_url('view', equip=name))


@view_config(route_name='notify_quit', renderer='json')
def notify_equip_quit(request):
    name = request.matchdict['equip']

    # wait to prevent that start arrives later in case of initialization error
    time.sleep(1)

    dbsession = DBSession()
    equip = dbsession.query(EquipmentModel).filter_by(name=name).one()
    equip.running = False
    dbsession.add(equip)
    return {'status': 'OK', 'info': name + ' quit notified'}


#@view_config(context='pyramid.exceptions.NotFound', renderer='notfound.mako')
def notfound_view(request):
    return dict()


@view_config(route_name='delete')
def delete_datafile(request):
    name = request.matchdict['equip']
    date = request.matchdict['date']
    time = request.matchdict['time']

    dbsession = DBSession()
    try:
        dbsession.query(EquipmentModel).filter_by(name=name).one()
    except NoResultFound:
        return NotFound("Unknown equipment name")

    filename = '{0}_{1}_{2}.h5'.format(name, date, time)
    file_path = os.path.join(data_path, name, filename)

    if not os.path.exists(file_path):
        return NotFound("No file for this equipment on the given date")

    os.remove(file_path)

    txt = "Data file from {0} equipment captured on {1} has been deleted"
    date_time = datetime.strptime(date+time, '%Y%m%d%H%M%S')
    request.session.flash(txt.format(name, date_time))

    return HTTPFound(location=request.route_url('view', equip=name))


# see: http://pythonpaste.org/webob/file-example.html
@view_config(route_name='download')
def download_datafile(request):
    name = request.matchdict['equip']
    date = request.matchdict['date']
    time = request.matchdict['time']

    dbsession = DBSession()
    try:
        dbsession.query(EquipmentModel).filter_by(name=name).one()
    except NoResultFound:
        return NotFound("Unknown equipment name")

    filename = '{0}_{1}_{2}.h5'.format(name, date, time)
    file_path = os.path.join(data_path, name, filename)

    if not os.path.exists(file_path):
        return NotFound("No file for this equipment on the given date")

    return _make_response(file_path)

# Auxiliary functions and classes for 'download' view
def _get_mimetype(file_path):
    type, encoding = mimetypes.guess_type(file_path)
    return type or 'application/octet-stream'

class FileIterable(object):
    def __init__(self, file_path):
        self.file_path = file_path
    def __iter__(self):
        return FileIterator(self.file_path)

class FileIterator(object):
    chunk_size = 4096
    def __init__(self, file_path):
        self.file_path = file_path
        self.fileobj = open(self.file_path, 'rb')
    def __iter__(self):
        return self
    def next(self):
        chunk = self.fileobj.read(self.chunk_size)
        if not chunk:
            raise StopIteration
        return chunk

def _make_response(file_path):
    res = Response(content_type=_get_mimetype(file_path),
                   conditional_response=True)
    res.app_iter = FileIterable(file_path)
    res.content_length = os.path.getsize(file_path)
    res.last_modified = os.path.getmtime(file_path)
    res.etag = '{0}-{1}-{2}'.format(os.path.getmtime(file_path),
                os.path.getsize(file_path), hash(file_path))
    filename = os.path.basename(file_path)
    res.content_disposition = 'attachment; filename={0}'.format(filename)
    return res

# vim: et ts=4 sw=4
