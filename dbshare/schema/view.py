"View API JSON schema."

from . import definitions
from . import query
from .. import constants

schema = {
    '$id': '/view',
    '$schema': constants.JSON_SCHEMA_URL,
    'title': 'View API JSON schema.',
    'definitions': {'link': definitions.link},
    'type': 'object',
    'properties': {
        '$id': {'type': 'string', 'format': 'uri'},
        'timestamp': {'type': 'string', 'format': 'date-time'},
        'name': {'type': 'string'},
        'title': {'type': ['string', 'null']},
        'description': {'type': ['string', 'null']},
        'database': {'$ref': '#/definitions/link'},
        'nrows': {
            'oneOf': [
                {'type': 'null'},
                {'type': 'integer', 'minimum': 0}
            ]
        },
        'rows': {'$ref': '#/definitions/link'},
        'data': {'$ref': '#/definitions/link'},
        'charts': definitions.charts,
        'query': query.query,
        'sources': {
            'type': 'array',
            'items': {'type': 'string'}
        },
        'columns': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'type': {'type': 'string'}
                },
                'required': ['name', 'type']
            }
        }
    },
    'required': [
        '$id',
        'timestamp',
        'name', 
        'database',
        'nrows',
        'rows',
        'data',
        'charts',
        'query',
        'sources',
        'columns'
    ],
    'additionalProperties': False
}


create = {
    '$id': '/view/create',
    '$schema': constants.JSON_SCHEMA_URL,
    'title': 'View creation API JSON schema.',
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'title': {'type': ['string', 'null']},
        'description': {'type': ['string', 'null']},
        'query': query.query
    },
    'required': ['name', 'query']
}
