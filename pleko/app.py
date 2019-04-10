"Pleko web app."

import json
import os.path
import sqlite3

import flask
import jinja2.utils

import pleko
import pleko.db
import pleko.index
import pleko.master
import pleko.query
import pleko.table
import pleko.user
import pleko.vega_lite
import pleko.view
import pleko.visual
from pleko import constants
from pleko import utils

ROOT_DIR = os.path.dirname(__file__)

CONFIG = dict(
    VERSION = pleko.__version__,
    SERVER_NAME = '127.0.0.1:5000',
    SITE_NAME = 'Pleko',
    DATABASES_DIRPATH = 'data',
    SECRET_KEY = None,
    SALT_LENGTH = 12,
    JSONIFY_AS_ASCII = False,
    JSON_SORT_KEYS = False,
    MIN_PASSWORD_LENGTH = 6,
    PERMANENT_SESSION_LIFETIME = 7 * 24 * 60 * 60, # seconds; 1 week
    USER_ENABLE_IMMEDIATELY = False,
    USER_ENABLE_EMAIL_WHITELIST = [], # Regexp's
    USER_DEFAULT_QUOTA = 2**22,       # 4 megabyte
    MAX_NROWS_DISPLAY = 2000,
    TABLE_INITIAL_COLUMNS = 8,
    QUERY_DEFAULT_LIMIT = 100,
    CSV_FILE_DELIMITERS = {'comma': {'label': "comma ','", 'char': ','},
                           'tab': {'label': "tab '\\t'", 'char': '\t'},
                           'vertical-bar': {'label': "vertical-bar '|'", 
                                            'char': '|'},
                           'semicolon': {'label': "semicolon ';'", 'char': ';'}},
    PLEKO_URL = 'https://github.com/pekrau/Pleko',
    FLASK_URL = 'http://flask.pocoo.org/',
    SQLITE_URL = 'https://www.sqlite.org/',
    # Bootstrap 4.3.1
    BOOTSTRAP_SITE_URL = 'https://getbootstrap.com/docs/4.3/getting-started/introduction/',
    BOOTSTRAP_CSS_ATTRS = 'href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous"',
    JQUERY_JS_ATTRS = 'src="https://code.jquery.com/jquery-3.3.1.slim.min.js" integrity="sha384-q8i/X+965DzO0rT7abK41JStQIAqVgRVzpbzo5smXKp4YfRvH+8abtTE1Pi6jizo" crossorigin="anonymous"',
    POPPER_JS_ATTRS = 'src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js" integrity="sha384-UO2eT0CpHqdSJQ6hJty5KVphtPhzWj9WO1clHTMGa3JDZwrnQq4sF86dIHNDz0W1" crossorigin="anonymous"',
    BOOTSTRAP_JS_ATTRS = 'src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js" integrity="sha384-JjSmVgyd0p3pXB1rRibZUAYoIIy6OrQ6VrjIEaFf/nJGzIxFDsf4x0xIM+B07jRM" crossorigin="anonymous"',
    # DataTables 1.10.18 for bootstrap 4
    DATATABLES_CSS_URL = 'https://cdn.datatables.net/1.10.18/css/dataTables.bootstrap4.min.css',
    DATATABLES_JS_URL = 'https://cdn.datatables.net/1.10.18/js/jquery.dataTables.min.js',
    DATATABLES_BOOTSTRAP_JS_URL = 'https://cdn.datatables.net/1.10.18/js/dataTables.bootstrap4.min.js',
    # D3, Vega and Vega-Lite
    D3_JS_URL = 'https://cdn.jsdelivr.net/npm/d3@5',
    TOPOJSON_JS_URL = 'https://cdn.jsdelivr.net/npm/topojson-client@3',
    VEGA_CORE_JS_URL = 'https://cdn.jsdelivr.net/npm/vega@5/build/vega-core.min.js',
    VEGA_EMBED_JS_URL = 'https://cdn.jsdelivr.net/npm/vega-embed@4',
    VEGA_LITE_SITE_URL = 'https://vega.github.io/vega-lite/',
    VEGA_LITE_JS_URL = 'https://cdn.jsdelivr.net/npm/vega-lite@3',
    VEGA_LITE_SCHEMA = os.path.join(ROOT_DIR, 'static/vega-lite-v3.json'),
)

def create_app():
    "Return the configured app object. Initialize the master, if not done."
    app = flask.Flask(__name__)
    app.config.from_mapping(CONFIG)
    app.config.from_json('config.json')
    app.config['SQLITE_VERSION'] = sqlite3.sqlite_version
    with open(app.config['VEGA_LITE_SCHEMA']) as infile:
        app.config['VEGA_LITE_SCHEMA'] = json.load(infile)
    app.url_map.converters['name'] = utils.NameConverter
    app.url_map.converters['nameext'] = utils.NameExtConverter
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    pleko.master.init(app)
    utils.mail.init_app(app)
    return app

app = create_app()
app.register_blueprint(pleko.user.blueprint, url_prefix='/user')
app.register_blueprint(pleko.db.blueprint, url_prefix='/db')
app.register_blueprint(pleko.table.blueprint, url_prefix='/table')
app.register_blueprint(pleko.query.blueprint, url_prefix='/query')
app.register_blueprint(pleko.view.blueprint, url_prefix='/view')
app.register_blueprint(pleko.index.blueprint, url_prefix='/index')
app.register_blueprint(pleko.visual.blueprint, url_prefix='/visual')
app.register_blueprint(pleko.vega_lite.blueprint, url_prefix='/vega-lite')

@app.template_filter('or_null_safe')
def or_null_safe(value):
    "Output None as HTML '<NULL>' in safe mode."
    if value is None:
        return jinja2.utils.Markup('<i>&lt;NULL&gt;</i>')
    else:
        return value

@app.before_request
def prepare():
    "Connect to the master database (read-only); get the current user."
    flask.g.cnx = pleko.master.get_cnx()
    flask.g.current_user = pleko.user.get_current_user()
    flask.g.is_admin = flask.g.current_user and \
                       flask.g.current_user.get('role') == constants.ADMIN

@app.context_processor
def setup_template_context():
    "Add useful stuff to the global context for templates."
    return dict(constants=constants,
                csrf_token=utils.csrf_token,
                utils=utils,
                len=len,
                enumerate=enumerate)

@app.route('/')
def home():
    "Home page. List public databases."
    return flask.render_template('home.html', dbs=pleko.db.get_dbs(public=True))

@app.route('/owner/<name:username>')
@pleko.user.login_required
def owner(username):
    "List of databases owned by the given user."
    if not (flask.g.is_admin or flask.g.current_user['username'] == username):
        flask.flash("you may not access the list of user's databases")
        return flask.redirect(flask.url_for('home'))
    return flask.render_template('owner.html',
                                 dbs=pleko.db.get_dbs(owner=username),
                                 username=username)

@app.route('/all')
@pleko.user.login_required
@pleko.user.admin_required
def all():
    "List of all databases."
    dbs = pleko.db.get_dbs()
    usage = sum([db['size'] for db in dbs])
    return flask.render_template('all.html', dbs=dbs, usage=usage)

@app.route('/upload', methods=['GET', 'POST'])
@pleko.user.login_required
def upload():
    "Upload a Pleko Sqlite3 database file."
    if utils.is_method_GET():
        return flask.render_template('upload.html')

    elif utils.is_method_POST():
        try:
            db = pleko.db.add_database(flask.request.form.get('dbname'),
                                       flask.request.form.get('description'),
                                       flask.request.files.get('dbfile'))
        except ValueError as error:
            flask.flash(str(error), 'error')
            return flask.redirect(flask.url_for('upload'))
        return flask.redirect(flask.url_for('db.home', dbname=db['name']))

@app.after_request
def finalize(response):
    try:
        flask.g.cnx.close()
    except AttributeError:
        pass
    try:
        flask.g.dbcnx.close()
    except AttributeError:
        pass
    return response


# This code is used only during testing.
if __name__ == '__main__':
    app.run(debug=True)
