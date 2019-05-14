"Table API endpoints."

import http.client

import flask

import dbshare.db

from dbshare import utils


blueprint = flask.Blueprint('api_table', __name__)

@blueprint.route('/<name:dbname>/<name:tablename>')
def table(dbname, tablename):
    "The schema for the table."
    try:
        db = dbshare.db.get_check_read(dbname)
    except ValueError:
        flask.abort(http.client.UNAUTHORIZED)
    except KeyError:
        flask.abort(http.client.NOT_FOUND)
    try:
        schema = db['tables'][tablename]
    except KeyError:
        flask.abort(http.client.NOT_FOUND)
    result = schema.copy()
    result['indexes'] = [i for i in db['indexes'].values() 
                         if i['table'] == tablename]
    result.update(get_api(db, schema))
    return flask.jsonify(**result)

def get_api(db, table):
    "Return the API JSON for the table."
    result = {'name': table['name'],
              'title': table.get('title'),
              'api': {'href': utils.url_for('api_table.table',
                                                dbname=db['name'],
                                                tablename=table['name'])},
              'database': {'href': utils.url_for('api_db.database',
                                                 dbname=db['name'])}
    }
    visuals = []
    for visual in db['visuals'].get(table['name'], []):
        url = utils.url_for('visual.display',
                            dbname=db['name'],
                            visualname=visual['name'])
        visuals.append({
            'name': visual['name'],
            'title': visual.get('title'),
            'specification': {'href': url + '.json'},
            'display': {'href': url, 'format': 'html'}})
    url = utils.url_for('table.rows',
                        dbname=db['name'],
                        tablename=table['name'])
    result.update({
        'nrows': table['nrows'],
        'rows': {'href': url + '.json'},
        'data': {'href': url + '.csv', 'format': 'csv'},
        'display': {'href': url, 'format': 'html'},
        'visualizations': visuals})
    return result