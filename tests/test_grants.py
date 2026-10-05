import MySQLdb
import pytest


def test_application_user_cannot_change_schema():
    connection = MySQLdb.connect(
        host="127.0.0.1",
        user="oes_app",
        passwd="oes_app_pass",
        db="oes",
    )
    cursor = connection.cursor()
    with pytest.raises(MySQLdb.OperationalError):
        cursor.execute("CREATE TABLE ddl_should_fail (id INT)")
    connection.close()
