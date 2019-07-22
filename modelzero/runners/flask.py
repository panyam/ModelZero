
from __future__ import absolute_import
import os, traceback, sys
from modelzero import world
from modelzero import utils as neutils
from modelzero.core import errors as neerrors

def create_app():
    from flask import Flask, render_template, redirect, jsonify
    app = Flask(__name__)
    app.url_map.converters['long'] = neutils.LongConverter
    app.config['SECRET_KEY'] = os.urandom(32)
    app.config['PROJECT_ID'] = "modelzero1"
    app.config['RESTPLUS_JSON'] = { "cls": neutils.NEJsonEncoder }

    # Global error handlers
    def default_error_handler(message, status):
        response = jsonify(neutils.error_json(message))
        response.status_code = status
        return response

    @app.errorhandler(neerrors.NotFound)
    def handle(error):
        return default_error_handler(error.message, 404)

    @app.errorhandler(neerrors.NotAllowed)
    def handle(error):
        return default_error_handler(error.message, 403)

    @app.errorhandler(neerrors.ValidationError)
    def handle(error):
        return default_error_handler(error.message, 400)

    @app.errorhandler(neerrors.Unauthorized)
    def handle(error):
        from google.appengine.api import users
        return "Unauthorized", 302, {'Location': users.create_login_url(request.url)}

    # @app.errorhandler(Exception)
    def unhandled_exception(e):
        import traceback ; traceback.print_exc()
        print(e, sys.stderr)
        app.logger.error('Unhandled Exception: %s', (e))
        return render_template('500.htm'), 500
    return app

def register_blueprints(app, world):
    # Register blueprints and endpoints
    from modelzero.blueprints import api, pages, auth, views
    app.register_blueprint(api.create_blueprint(world))
    app.register_blueprint(views.create_blueprint(world))
    for bp in pages.create_blueprints(world): app.register_blueprint(bp)
    app.register_blueprint(auth.blueprint)
    return app

def run():
    app = create_app()
    datastore = world.create_default_datastore(gae_project_id = app.config['PROJECT_ID'])
    theWorld = world.World(datastore)
    register_blueprints(app, theWorld)
    app.run(host='127.0.0.1', port=8080, debug=True)
