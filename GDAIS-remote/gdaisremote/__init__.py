from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from gdaisremote.models import initialize_sql

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    # sql engine
    engine = engine_from_config(settings, 'sqlalchemy.')
    initialize_sql(engine)

    # configuration setup
    config = Configurator(settings=settings)

    # static view setup
    config.add_static_view('static', 'gdaisremote:static')

    # routes setup
    config.add_route('list' , '/')
    config.add_route('start', '/start/{equip}')
    config.add_route('stop' , '/stop/{equip}')

    # scan files for config options
    config.scan()

    return config.make_wsgi_app()

