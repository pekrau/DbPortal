"JSON schema component for the column specification."

spec = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'primarykey': {'type': 'boolean'},
        'notnull': {'type': 'boolean'},
        'unique': {'type': 'boolean'},
        'type': {'type': 'string',
                 'enum': ['INTEGER', 'REAL', 'TEXT', 'BLOB']},
    },
    'required': [
        'name',
        'type'
    ]
}
