import sqlite3 as sq

con = None
c = None


def start_db_connection(version_str):
    global con
    global c
    con = sq.connect(f'D:/D2_Datamining/Package Unpacker/db/{version_str}.db')
    c = con.cursor()


def get_entries_from_table(pkg_str, column_select='*'):
    global c
    c.execute(f'SELECT {column_select} from {pkg_str}')
    rows = c.fetchall()
    return rows
