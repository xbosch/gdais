from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from pyramid.session import UnencryptedCookieSessionFactoryConfig

from gdaisremote.models import initialize_sql

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    # sql engine
    engine = engine_from_config(settings, 'sqlalchemy.')
    initialize_sql(engine)

    # session factory
    session_factory = UnencryptedCookieSessionFactoryConfig('itsaseekret')

    # configuration setup
    config = Configurator(settings=settings, session_factory=session_factory)

    # static view setup
    config.add_static_view('static', 'gdaisremote:static')

    # routes setup
    config.add_route('list' , '/')
    config.add_route('start', '/start/{equip}')
    config.add_route('notify_start', '/notify_start/{equip}')
    config.add_route('stop' , '/stop/{equip}')
    config.add_route('notify_quit', '/notify_quit/{equip}')
    config.add_route('view', '/view/{equip}')
    config.add_route('view_log', '/view_log/{equip}', xhr=True)
    config.add_route('log', '/log/{equip}')
    config.add_route('download', '/download/{equip}/{date}/{time}')
    config.add_route('delete', '/delete/{equip}/{date}/{time}')

    # scan files for config options
    config.scan()

    return config.make_wsgi_app()

