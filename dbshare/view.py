"View HTML endpoints."

import copy
import http.client
import sqlite3

import flask

import dbshare.db
import dbshare.table

from . import constants
from . import utils


blueprint = flask.Blueprint('view', __name__)

@blueprint.route('/<name:dbname>', methods=['GET', 'POST'])
@utils.login_required
def create(dbname):
    "Create a view of the data in the database."
    try:
        db = dbshare.db.get_check_write(dbname)
    except (KeyError, ValueError) as error:
        utils.flash_error(error)
        return flask.redirect(flask.url_for('home'))
    viewname = flask.request.values.get('name')
    title = flask.request.values.get('title')
    description = flask.request.values.get('description')
    # Do not check validity here.
    query = dbshare.query.get_query_from_request()

    if utils.http_GET():
        return flask.render_template('view/create.html',
                                     db=db,
                                     name=viewname,
                                     description=description,
                                     query=query)

    elif utils.http_POST():
        try:
            # Get again, with checking this time.
            query = dbshare.query.get_query_from_request(check=True)
            schema = {'name': viewname,
                      'title': title or None,
                      'description': description or None,
                      'query': query}
            with dbshare.db.DbContext(db) as ctx:
                ctx.add_view(schema)
        except (ValueError, sqlite3.Error) as error:
            utils.flash_error(error)
            return flask.redirect(flask.url_for('.create',
                                                dbname=dbname,
                                                name=viewname,
                                                description=description,
                                                **schema['query']))
        return flask.redirect(
            flask.url_for('.rows', dbname=dbname, viewname=viewname))

@blueprint.route('/<name:dbname>/<name:viewname>/edit',
                 methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(dbname, viewname):
    "Edit the metadata of the view. Or delete the view."
    try:
        db = dbshare.db.get_check_write(dbname)
    except (KeyError, ValueError) as error:
        utils.flash_error(error)
        return flask.redirect(flask.url_for('db.display', dbname=dbname))
    try:
        schema = db['views'][viewname]
    except KeyError:
        utils.flash_error('no such view')
        return flask.redirect(flask.url_for('db.display', dbname=dbname))

    if utils.http_GET():
        return flask.render_template('view/edit.html', db=db, schema=schema)

    elif utils.http_POST():
        try:
            with dbshare.db.DbContext(db) as ctx:
                schema['title'] = flask.request.form.get('title') or None
                schema['description'] = flask.request.form.get('description') or None
                ctx.update_view(schema)
        except ValueError as error:
            utils.flash_error(error)
            return flask.redirect(
                flask.url_for('.edit', dbname=dbname, viewname=viewname))
        return flask.redirect(
            flask.url_for('.rows', dbname=dbname, viewname=viewname))

    elif utils.http_DELETE():
        try:
            db = dbshare.db.get_check_write(dbname)
        except (KeyError, ValueError) as error:
            utils.flash_error(error)
            return flask.redirect(flask.url_for('home'))
        try:
            with dbshare.db.DbContext(db) as ctx:
                ctx.delete_view(str(viewname))
        except (ValueError, sqlite3.Error) as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for('db.display', dbname=dbname))

@blueprint.route('/<name:dbname>/<nameext:viewname>')
def rows(dbname, viewname):     # NOTE: viewname is a NameExt instance!
    "Display rows in the view."
    try:
        db = dbshare.db.get_check_read(dbname, nrows=[str(viewname)])
    except (KeyError, ValueError) as error:
        utils.flash_error(error)
        return flask.redirect(flask.url_for('home'))
    has_write_access = dbshare.db.has_write_access(db)
    try:
        schema = db['views'][str(viewname)]
    except KeyError:
        utils.flash_error('no such view')
        return flask.redirect(flask.url_for('db.display', dbname=dbname))
    try:
        title = schema.get('title') or "View {}".format(viewname)
        dbcnx = dbshare.db.get_cnx(dbname)
        columns = [c['name'] for c in schema['columns']]
        quoted_columns = [f'"{c}"' for c in columns]
        sql = 'SELECT %s FROM "%s"' % (','.join(quoted_columns), viewname)

        if viewname.ext == 'json' or utils.accept_json():
            try:
                cursor = utils.execute_timeout(dbcnx, sql)
            except SystemError:
                flask.abort(http.client.REQUEST_TIMEOUT)
            result = {
                'name': str(viewname),
                'title': title,
                'source': {'type': 'view',
                           'href': utils.url_for('api_view.view',
                                                 dbname=db['name'],
                                                 viewname=schema['name'])},
                'nrows': schema['nrows'],
                'data': [dict(zip(columns, row)) for row in cursor]
            }
            return utils.jsonify(utils.get_json(**result), schema='/rows')

        elif viewname.ext == 'csv':
            writer = utils.CsvWriter(header=columns)
            try:
                cursor = utils.execute_timeout(dbcnx, sql)
            except SystemError:
                flask.abort(http.client.REQUEST_TIMEOUT)
            writer.write_rows(cursor)
            return flask.Response(writer.getvalue(),
                                  mimetype=constants.CSV_MIMETYPE)

        elif viewname.ext in (None, 'html'):
            limit = flask.current_app.config['MAX_NROWS_DISPLAY']
            if schema['nrows'] is None:
                utils.flash_error('too many rows to fetch; interrupted')
                cursor = []     # Fake cursor
            elif schema['nrows'] > limit:
                utils.flash_message_limit(limit)
                sql += f" LIMIT {limit}"
                cursor = utils.execute_timeout(dbcnx, sql) # Maybe LIMIT
            else:
                cursor = utils.execute_timeout(dbcnx, sql)
            query = schema['query']
            sql = dbshare.query.get_sql_statement(query) # No imposed LIMIT
            charts = [c for c in db['charts'].values()
                      if c['source'] == str(viewname)]
            return flask.render_template('view/rows.html', 
                                         db=db,
                                         schema=schema,
                                         query=query,
                                         sql=sql,
                                         title=title,
                                         rows=cursor,
                                         charts=charts,
                                         has_write_access=has_write_access)

        else:
            flask.abort(http.client.NOT_ACCEPTABLE)

    except (SystemError, sqlite3.Error) as error:
        utils.flash_error(error)
        return flask.redirect(
            flask.url_for('.schema', viewname=str(viewname)))

@blueprint.route('/<name:dbname>/<name:viewname>/schema')
def schema(dbname, viewname):
    "Display the schema for a view."
    try:
        db = dbshare.db.get_check_read(dbname, nrows=[viewname])
    except (KeyError, ValueError) as error:
        utils.flash_error(error)
        return flask.redirect(flask.url_for('home'))
    try:
        schema = db['views'][viewname]
    except KeyError:
        utils.flash_error('no such view')
        return flask.redirect(flask.url_for('db.display', dbname=dbname))
    has_write_access = dbshare.db.has_write_access(db)
    sources = [dbshare.db.get_schema(db, name) for name in schema['sources']]
    # Special case: Create HTML links for sources, leave "AS" parts be.
    html_from = schema['query']['from']
    for source in sources:
        if source['type'] == constants.TABLE:
            url = flask.url_for('table.rows',
                                dbname=dbname,
                                tablename=source['name'])
        else:
            url = flask.url_for('view.rows',
                                dbname=dbname,
                                viewname=source['name'])
        html = '<a href="%s">%s</a>' % (url, source['name'])
        html_from = html_from.replace(source['name'], html)
    return flask.render_template('view/schema.html',
                                 db=db,
                                 schema=schema,
                                 has_write_access=has_write_access,
                                 sources=sources,
                                 html_from=html_from)

@blueprint.route('/<name:dbname>/<name:viewname>/clone', 
                 methods=['GET', 'POST'])
@utils.login_required
def clone(dbname, viewname):
    "Create a clone of the view."
    try:
        db = dbshare.db.get_check_write(dbname)
    except (KeyError, ValueError) as error:
        utils.flash_error(error)
        return flask.redirect(flask.url_for('home'))
    try:
        schema = db['views'][viewname]
    except KeyError:
        utils.flash_error('no such view')
        return flask.redirect(flask.url_for('db.display', dbname=dbname))

    if utils.http_GET():
        return flask.render_template('view/clone.html', db=db, schema=schema)

    elif utils.http_POST():
        try:
            schema = copy.deepcopy(schema)
            schema['name'] = flask.request.form['name']
            if schema.get('title'):
                schema['title'] = 'Clone of ' + schema['title']
            with dbshare.db.DbContext(db) as ctx:
                ctx.add_view(schema)
        except (ValueError, sqlite3.Error) as error:
            utils.flash_error(error)
            return flask.redirect(
                flask.url_for('.clone', dbname=dbname, viewname=viewname))
        return flask.redirect(
            flask.url_for('.rows', dbname=dbname, viewname=schema['name']))

@blueprint.route('/<name:dbname>/<name:viewname>/download')
def download(dbname, viewname):
    "Download the rows in the view to a file."
    try:
        db = dbshare.db.get_check_read(dbname)
    except (KeyError, ValueError) as error:
        utils.flash_error(error)
        return flask.redirect(flask.url_for('home'))
    try:
        schema = db['views'][viewname]
    except KeyError:
        utils.flash_error('no such view')
        return flask.redirect(flask.url_for('db.display', dbname=dbname))
    return flask.render_template('view/download.html', db=db,schema=schema)

@blueprint.route('/<name:dbname>/<name:viewname>/csv')
def download_csv(dbname, viewname):
    "Output a CSV file of the rows in the view."
    try:
        db = dbshare.db.get_check_read(dbname)
    except (KeyError, ValueError) as error:
        utils.flash_error(error)
        return flask.redirect(flask.url_for('home'))
    try:
        schema = db['views'][viewname]
    except KeyError:
        utils.flash_error('no such view')
        return flask.redirect(flask.url_for('db.display', dbname=dbname))
    try:
        delimiter = flask.request.form.get('delimiter') or 'comma'
        try:
            delimiter = flask.current_app.config['CSV_FILE_DELIMITERS'][delimiter]['char']
        except KeyError:
            raise ValueError('invalid delimiter')
        if utils.to_bool(flask.request.args.get('header')):
            header = schema['query']['columns']
        else:
            header = None
        writer = utils.CsvWriter(header, delimiter=delimiter)
        dbcnx = dbshare.db.get_cnx(dbname)
        colnames = ['"%s"' % c for c in schema['query']['columns']]
        sql = 'SELECT %s FROM "%s"' % (','.join(colnames), viewname)
        writer.write_rows(utils.execute_timeout(dbcnx, sql))
    except (ValueError, SystemError, sqlite3.Error) as error:
        utils.flash_error(error)
        return flask.redirect(
            flask.url_for('.download', dbname=dbname, viewname=viewname))
    response = flask.make_response(writer.getvalue())
    response.headers.set('Content-Type', constants.CSV_MIMETYPE)
    response.headers.set('Content-Disposition', 'attachment', 
                         filename="%s.csv" % viewname)
    return response
