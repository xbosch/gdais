import os
import re
import socket
import subprocess
import time

from pyramid.httpexceptions import HTTPFound
from pyramid.session import UnencryptedCookieSessionFactoryConfig
from pyramid.view import view_config

from gdaisremote.models import DBSession
from gdaisremote.models import EquipmentModel

here = os.path.dirname(os.path.abspath(__file__))
gdais_path = os.path.normpath(os.path.join(here, '..', '..', 'GDAIS-core'))
equips_path = os.path.join(gdais_path, 'conf', 'equips')

@view_config(route_name='list', renderer='list.mako')
def list_equips(request):
    dbsession = DBSession()
    equips = dbsession.query(EquipmentModel).all()
    return dict(equips=equips)

@view_config(route_name='view', renderer='view.mako')
def view_equip(request):
    name = request.matchdict['equip']
    equip_path = os.path.join(equips_path, name + '.json')

    dbsession = DBSession()
    equip = dbsession.query(EquipmentModel).filter_by(name=name).one()
    if not equip:
        request.session.flash("Equipment '{0}' not found".format(name))
        return HTTPFound(location=request.route_url('list'))

    if equip.running:
        status = 'running'
    else:
        status = 'stopped'
    return dict(equip=equip, equip_path=equip_path, status=status)

@view_config(route_name='start')
def start_equip(request):
    name = request.matchdict['equip']
    equip_path = os.path.join(equips_path, name + '.json')
    main = os.path.join(gdais_path, 'run.sh')

    dbsession = DBSession()
    equip = dbsession.query(EquipmentModel).filter_by(name=name).one()
    if not equip:
        request.session.flash("Equipment '{0}' not found".format(name))
    elif not equip.running:
        print "[GDAIS-remote] DEBUG: Calling:", main, '-d', equip_path
        retcode = subprocess.call([main, '-d', equip_path])

        if retcode == 0:
            request.session.flash("'{0}' started".format(name))
            time.sleep(1) # wait until GDAIS-core has started # TODO remove?
            return HTTPFound(location=request.route_url('view', equip=name))
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

@view_config(route_name='stop', renderer='stop.mako')
def stop_equip(request):
    name = request.matchdict['equip']

    dbsession = DBSession()
    equip = dbsession.query(EquipmentModel).filter_by(name=name).one()
    if not equip:
        request.session.flash("Equipment {0} not found".format(name))
        return HTTPFound(location=request.route_url('list'))
    elif equip.running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('localhost', 12345))
            s.send(bytes('quit'))
            s.close()
            request.session.flash("Sent quit command to '{0}'".format(name))
            time.sleep(1) # wait until GDAIS-core has stopped # TODO remove?
        except socket.error as msg:
            request.session.flash("Error occurred: {0}".format(msg))
    else:
        request.session.flash("Equipment {0} not running".format(name))

    return HTTPFound(location=request.route_url('view', equip=name))

@view_config(route_name='notify_quit', renderer='json')
def notify_equip_quit(request):
    name = request.matchdict['equip']
    dbsession = DBSession()
    equip = dbsession.query(EquipmentModel).filter_by(name=name).one()
    equip.running = False
    dbsession.add(equip)
    return {'status': 'OK', 'info': name + ' quit notified'}

#@view_config(context='pyramid.exceptions.NotFound', renderer='notfound.mako')
def notfound_view(request):
    return dict()

# vim: et ts=4 sw=4
