"Test the table API endpoint."

import http.client

import dbshare.schema.db
import dbshare.schema.table
import dbshare.schema.rows

from dbshare.test.base import *


class Table(Base):
    "Test the DbShare API table endpoint."

    def test_db_upload(self):
        "Create a database with table by file upload, check the table JSON."
        response = self.upload_file()
        self.assertEqual(response.status_code, http.client.OK)
        # Check that the db API JSON is valid.
        jsonschema.validate(instance=response.json(),
                            schema=dbshare.schema.db.schema)
        # Check that the table API JSON is valid.
        table_url = f"{CONFIG['root_url']}/table/{CONFIG['dbname']}/{CONFIG['tablename']}"
        response = self.session.get(table_url)
        self.assertEqual(response.status_code, http.client.OK)
        jsonschema.validate(instance=response.json(),
                            schema=dbshare.schema.table.schema)
        # Check that the table rows JSON is valid.
        rows_url = f"{CONFIG['base_url']}/table/{CONFIG['dbname']}/{CONFIG['tablename']}.json"
        response = self.session.get(rows_url)
        self.assertEqual(response.status_code, http.client.OK)
        jsonschema.validate(instance=response.json(),
                            schema=dbshare.schema.rows.schema)


if __name__ == '__main__':
    unittest.main()
