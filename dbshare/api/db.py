"Database API endpoints."

import http.client
import io

import flask

import dbshare.db

import dbshare.api.table
import dbshare.api.user
import dbshare.api.view

from dbshare import utils

blueprint = flask.Blueprint('api_db', __name__)

@blueprint.route('/<name:dbname>', methods=['GET', 'PUT', 'POST', 'DELETE'])
def database(dbname):
    """GET: List the database tables, views and metadata.
    PUT: Create a database.
    POST: Edit the database.
    DELETE: Delete the database.
    """
    if utils.http_GET():
        try:
            db = dbshare.db.get_check_read(dbname, nrows=True)
        except ValueError:
            flask.abort(http.client.UNAUTHORIZED)
        except KeyError:
            flask.abort(http.client.NOT_FOUND)
        return flask.jsonify(utils.get_api(**get_api(db, complete=True)))
 
    elif utils.http_PUT():
        try:
            dbshare.db.get_check_read(dbname)
        except ValueError:
            flask.abort(http.client.FORBIDDEN)
        except KeyError:
            pass
        else:
            flask.abort(http.client.FORBIDDEN)
        try:
            if flask.request.content_length:
                db = dbshare.db.add_database(
                    dbname,
                    infile=io.BytesIO(flask.request.get_data()),
                    size=flask.request.content_length)
            else:
                with dbshare.db.DbContext() as ctx:
                    ctx.set_name(dbname)
                    ctx.initialize()
                db = ctx.db
        except ValueError as error:
            flask.abort(http.client.BAD_REQUEST)
        return flask.redirect(flask.url_for('api_db.database', dbname=dbname))

    elif utils.http_POST(csrf=False):
        try:
            db = dbshare.db.get_check_write(dbname)
        except ValueError:
            flask.abort(http.client.UNAUTHORIZED)
        except KeyError:
            flask.abort(http.client.NOT_FOUND)
        try:
            data = flask.request.get_json()
            if data is None: raise ValueError
            with dbshare.db.DbContext(db) as ctx:
                try:
                    ctx.set_name(data['name'])
                except KeyError:
                    pass
                try:
                    ctx.set_title(data['title'])
                except KeyError:
                    pass
                try:
                    ctx.set_description(data['description'])
                except KeyError:
                    pass
                try:
                    ctx.set_public(data['public'])
                except KeyError:
                    pass
        except ValueError:
            flask.abort(http.client.BAD_REQUEST)
        return flask.redirect(
            flask.url_for('api_db.database', dbname=db['name']))

    elif utils.http_DELETE(csrf=False):
        try:
            dbshare.db.get_check_write(dbname)
        except ValueError:
            flask.abort(http.client.UNAUTHORIZED)
        except KeyError:
            flask.abort(http.client.NOT_FOUND)
        dbshare.db.delete_database(dbname)
        return ('', http.client.NO_CONTENT)

@blueprint.route('/<name:dbname>/readonly', methods=['PUT'])
def readonly(dbname):
    "PUT: Set the database to read-only."
    try:
        db = dbshare.db.get_check_write(dbname, check_mode=False)
        if not db['readonly']:
            with dbshare.db.DbContext(db) as ctx:
                ctx.set_readonly(True)
    except ValueError:
        flask.abort(http.client.UNAUTHORIZED)
    except KeyError:
        flask.abort(http.client.NOT_FOUND)
    return flask.redirect(flask.url_for('api_db.database', dbname=dbname))

@blueprint.route('/<name:dbname>/readwrite', methods=['PUT'])
def readwrite(dbname):
    "PUT: Set the database to read-write."
    try:
        db = dbshare.db.get_check_write(dbname, check_mode=False)
        if db['readonly']:
            with dbshare.db.DbContext(db) as ctx:
                ctx.set_readonly(False)
    except ValueError:
        flask.abort(http.client.UNAUTHORIZED)
    except KeyError:
        flask.abort(http.client.NOT_FOUND)
    return flask.redirect(flask.url_for('api_db.database', dbname=dbname))

def get_api(db, complete=False):
    "Return the API for the database."
    result = {'name': db['name'],
              'title': db.get('title'),
              'description': db.get('description'),
              'owner': dbshare.api.user.get_api(db['owner']),
              'public': db['public'],
              'readonly': db['readonly'],
              'size': db['size'],
              'modified': db['modified'],
              'created': db['created'],
              'hashes': db['hashes']
    }
    if complete:
        result['tables'] = [dbshare.api.table.get_api(db, table)
                            for table in db['tables'].values()]
        result['views'] = [dbshare.api.view.get_api(db, view)
                           for view in db['views'].values()]
    return result
