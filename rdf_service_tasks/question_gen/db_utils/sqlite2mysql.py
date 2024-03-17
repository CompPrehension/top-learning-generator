# sqlite2mysql.py

from time import time
from urllib.parse import quote_plus  # https://stackoverflow.com/a/1424009/12824563

from sqlalchemy import create_engine


if __name__ != '__main__':
    exit(5)  # guard: fail if someone's trying to import this module to another


# TARGET_DOMAIN = 'expression'
TARGET_DOMAIN = 'ctrl_flow'

# Load conditionally:
if TARGET_DOMAIN == 'expression':
    import sqlite_orm_classes as lt
elif TARGET_DOMAIN == 'ctrl_flow':
    import sqlite_orm_classes_cf as lt
else:
    raise ValueError(TARGET_DOMAIN)


# MODE = 'INSERT'
MODE = 'UPDATE'
IGNORE_IDS = True  # ids may be not aligned

# connection_str = ''
if 1:
    # local
    print("sending data to local connection")
    connection_str = 'mysql+pymysql://remote:!E3f5c712@localhost:3306/test_db'
else:
    # remote
    print("sending data to remote connection ...")
cnx = create_engine(connection_str)

from sqlalchemy.sql import table, column, select, update, insert
from sqlalchemy import bindparam
from sqlalchemy import MetaData, Table
from sqlalchemy.orm import sessionmaker

# define meta information
#### metadata = MetaData(bind=cnx)
# @see: https://docs.sqlalchemy.org/en/20/core/metadata.html#sqlalchemy.schema.MetaData.reflect.params.bind
metadata = MetaData()
metadata.reflect(bind=cnx)

# fetch metadata from DB itself ...
ctfl_questions_table = Table('questions_meta', metadata, autoload=True)

connection = cnx.connect()

Session = sessionmaker(bind=cnx)
session = Session()

# SQLite section >

TARGET_LOWEST_VERSION = 9  # see lt.TOOL_VERSION

q_list = list(lt.Questions.select().where(
    (lt.Questions._stage == 3) & (lt.Questions._version >= TARGET_LOWEST_VERSION)).execute())

print(len(q_list), 'questions selected to add to/update in MySQL')

# < SQLite section


# Добавить в таблицу MySQL данные из SQLite


time_begin = time()

succeeded = 0

if MODE == 'UPDATE':
    update_stmt = None
    update_values = []

# q_list[0].__data__
for _i, q in enumerate(q_list):

    ###
    if q.integral_complexity > .9:
        continue
    ###

    fields = dict(q.__data__)
    fields['domain_shortname'] = TARGET_DOMAIN
    fields['q_graph'] = None
    fields['template_id'] = fields['template']
    del fields['template']
    del fields['formulation']
    # round long floats
    fields['solution_structural_complexity'] = round(fields['solution_structural_complexity'], 5)
    fields['integral_complexity'] = round(fields['integral_complexity'], 5)
    if IGNORE_IDS:
        del fields['id']  # catch error on duplicate
    # insert
    try:
        if MODE == 'INSERT':
            i = insert(ctfl_questions_table)
            i = i.values(fields)
            session.execute(i)
        elif MODE == 'UPDATE':
            if update_stmt is None:
                update_stmt = ctfl_questions_table.update(). \
                    where(ctfl_questions_table.c.name == bindparam('name')). \
                    values({
                    k: bindparam(k)
                    for k in fields.keys()
                })
            update_values.append(fields)
        succeeded += 1
    except Exception as e:
        print()
        print(type(e).__name__, str(e))
        print()
        if 1:  ###
            session.commit()
            raise
        ###
        continue
    if (update_values and not _i % 10):
        if MODE == 'UPDATE':
            trans = connection.begin()
            connection.execute(update_stmt, update_values)
            trans.commit()
            update_values.clear()

        print(end='.')
    if (_i and not _i % 500):
        print(_i, )
        print(time() - time_begin, 's elapsed')

print(_i + 1, 'completed,')
print(succeeded, 'successfully.')

session.commit()  # without this run, Workbench crashed :) on `select count(*)`, and shown no rows on `select *`

print(time() - time_begin, 's elapsed total.')
