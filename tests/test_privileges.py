import MySQLdb
import pytest


def test_application_user_cannot_create_tables():
    connection = MySQLdb.connect(
        host="127.0.0.1",
        user="oes_app",
        passwd="oes_app_pass",
        db="oes",
    )
    cursor = connection.cursor()
    try:
        with pytest.raises(MySQLdb.OperationalError) as caught:
            cursor.execute("CREATE TABLE privilege_probe (id INT)")
        assert caught.value.args[0] == 1142
    finally:
        cursor.close()
        connection.close()
