import sqlite3 as sq

con = None
c = None


def start_db_connection(version_str):
    global con
    global c
    con = sq.connect(f'D:/D2_Datamining/Package Unpacker/{version_str}/{version_str}_pkg_data.db')
    c = con.cursor()


def get_entries_from_table(pkg_str, column_select='*'):
    global c
    c.execute("SELECT " + column_select + " from " + pkg_str + "_DecodedData")
    rows = c.fetchall()
    return rows

