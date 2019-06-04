"DbShare web app."

import json
import time

import flask
import flask_mail
import jinja2.utils
import markdown

import dbshare
import dbshare.about
import dbshare.config
import dbshare.db
import dbshare.dbs
import dbshare.index
import dbshare.query
import dbshare.site
import dbshare.system
import dbshare.table
import dbshare.template
import dbshare.templates
import dbshare.user
import dbshare.vega
import dbshare.vega_lite
import dbshare.view
import dbshare.visual

import dbshare.api.db
import dbshare.api.dbs
import dbshare.api.query
import dbshare.api.schema
import dbshare.api.table
import dbshare.api.template
import dbshare.api.templates
import dbshare.api.user
import dbshare.api.view

from dbshare import constants
from dbshare import utils

app = flask.Flask(__name__, template_folder='html')
app.url_map.converters['name'] = utils.NameConverter
app.url_map.converters['nameext'] = utils.NameExtConverter
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# Get and sanity check the configuration.
dbshare.config.init(app)
assert app.config['SECRET_KEY']
assert app.config['SALT_LENGTH'] > 6
assert app.config['MIN_PASSWORD_LENGTH'] > 4
assert app.config['EXECUTE_TIMEOUT'] > 0.0
assert app.config['EXECUTE_TIMEOUT_INCREMENT'] > 0.0
assert app.config['EXECUTE_TIMEOUT_BACKOFF'] > 1.0

# Read the JSON Schema files; must be present.
with open(app.config['VEGA_SCHEMA']) as infile:
    app.config['VEGA_SCHEMA'] = json.load(infile)
with open(app.config['VEGA_LITE_SCHEMA']) as infile:
    app.config['VEGA_LITE_SCHEMA'] = json.load(infile)

# Init the system database.
dbshare.system.init(app)

# Init the mail handler.
utils.mail.init_app(app)

# Set the URL map.
app.register_blueprint(dbshare.db.blueprint, url_prefix='/db')
app.register_blueprint(dbshare.dbs.blueprint, url_prefix='/dbs')
app.register_blueprint(dbshare.table.blueprint, url_prefix='/table')
app.register_blueprint(dbshare.query.blueprint, url_prefix='/query')
app.register_blueprint(dbshare.view.blueprint, url_prefix='/view')
app.register_blueprint(dbshare.index.blueprint, url_prefix='/index')
app.register_blueprint(dbshare.visual.blueprint, url_prefix='/visual')
app.register_blueprint(dbshare.template.blueprint, url_prefix='/template')
app.register_blueprint(dbshare.templates.blueprint, url_prefix='/templates')
app.register_blueprint(dbshare.vega.blueprint, url_prefix='/vega')
app.register_blueprint(dbshare.vega_lite.blueprint, url_prefix='/vega-lite')
app.register_blueprint(dbshare.user.blueprint, url_prefix='/user')
app.register_blueprint(dbshare.about.blueprint, url_prefix='/about')
app.register_blueprint(dbshare.site.blueprint, url_prefix='/site')

app.register_blueprint(dbshare.api.db.blueprint, url_prefix='/api/db')
app.register_blueprint(dbshare.api.dbs.blueprint, url_prefix='/api/dbs')
app.register_blueprint(dbshare.api.table.blueprint, url_prefix='/api/table')
app.register_blueprint(dbshare.api.query.blueprint, url_prefix='/api/query')
app.register_blueprint(dbshare.api.view.blueprint, url_prefix='/api/view')
app.register_blueprint(dbshare.api.template.blueprint,
                       url_prefix='/api/template')
app.register_blueprint(dbshare.api.templates.blueprint,
                       url_prefix='/api/templates')
app.register_blueprint(dbshare.api.user.blueprint, url_prefix='/api/user')
app.register_blueprint(dbshare.api.schema.blueprint, url_prefix='/api/schema')

@app.context_processor
def setup_template_context():
    "Add useful stuff to the global context for Jinja2 templates."
    return dict(constants=constants,
                csrf_token=utils.csrf_token,
                utils=utils,
                enumerate=enumerate,
                len=len,
                range=range,
                round=round,
                is_none=lambda v: v is None)

@app.template_filter('thousands')
def thousands(value):
    "Output integer with thousands delimiters."
    if isinstance(value, int):
        return '{:,}'.format(value)
    else:
        return value

@app.template_filter('none_as_question_mark')
def none_as_question_mark(value):
    "Output None as '?'."
    if value is None:
        return '?'
    else:
        return value

@app.template_filter('none_as_literal_null')
def none_as_literal_null(value):
    "Output None as HTML '<NULL>' in safe mode."
    if value is None:
        return jinja2.utils.Markup('<i>&lt;NULL&gt;</i>')
    else:
        return value

@app.template_filter('none_as_empty_string')
def none_as_empty_string(value):
    "Output the value if not None, else an empty string."
    if value is None:
        return ''
    else:
        return value

@app.template_filter('markdown')
def markdown_process(value):
    "Use Markdown to process the value."
    value = value or ''
    return jinja2.utils.Markup(markdown.markdown(value, output_format='html5'))

@app.template_filter('access')
def access(value):
    "Output public or private according to the value."
    if value:
        return jinja2.utils.Markup('<span class="badge badge-info">public</span>')
    else:
        return jinja2.utils.Markup('<span class="badge badge-secondary">private</span>')

@app.template_filter('mode')
def mode(value):
    "Output readonly or read-write according to the value."
    if value:
        return jinja2.utils.Markup('<span class="badge badge-success">read-only</span>')
    else:
        return jinja2.utils.Markup('<span class="badge badge-warning">read/write</span>')

@app.before_request
def prepare():
    "Connect to the system database (read-only); get the current user."
    flask.g.cnx = dbshare.system.get_cnx()
    flask.g.current_user = dbshare.user.get_current_user()
    flask.g.is_admin = flask.g.current_user and \
                       flask.g.current_user.get('role') == constants.ADMIN
    flask.g.timer = utils.Timer()

@app.route('/')
def home():
    "Home page; display the list of public databases."
    if utils.accept_json():
        return flask.redirect(flask.url_for('api'))
    return flask.render_template('home.html',
                                 dbs=dbshare.dbs.get_dbs(public=True))

@app.route('/api')
def api():
    "API home resource; links to other resources."
    data = {'title': 'DbShare', 
             'version': flask.current_app.config['VERSION'],
             'databases': {
                 'public': {'href': utils.url_for('api_dbs.public')}
             },
             'templates': {
                 'public': {'href': utils.url_for('api_templates.public')}
             }
    }
    if flask.g.current_user:
        data['databases']['owner'] = {
            'href': utils.url_for('api_dbs.owner',
                                  username=flask.g.current_user['username'])
        }
        data['templates']['owner'] = {
            'href': utils.url_for('api_templates.owner',
                                  username=flask.g.current_user['username'])
        }
    if flask.g.is_admin:
        data['databases']['all'] = {
            'href': utils.url_for('api_dbs.all')
        }
        data['templates']['all'] = {
            'href': utils.url_for('api_templates.all')
        }
    if flask.g.current_user:
        data['user'] = dbshare.api.user.get_api(flask.g.current_user['username'])
    data['schema'] = {'href': constants.SCHEMA_BASE_URL.rstrip('/')}
    return flask.jsonify(utils.get_api(**data))


# This code is used only during testing.
if __name__ == '__main__':
    app.run(debug=True)
