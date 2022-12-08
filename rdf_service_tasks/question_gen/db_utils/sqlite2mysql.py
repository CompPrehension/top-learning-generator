# sqlite2mysql.py

from urllib.parse import quote_plus  # https://stackoverflow.com/a/1424009/12824563

import sqlite_orm_classes as lt

from sqlalchemy import create_engine

# cnx = create_engine('mysql+pymysql://<username>:<password>@<host>/<dbname>')
# df = pd.read_sql('SELECT * FROM <table_name>', cnx) #read the entire table

# connection_str = ''
if 1:
	# local
	print("sending data to local connection")
else:
	# remote
	print("sending data to remote connection ...")
cnx = create_engine(connection_str)


from sqlalchemy.sql import table, column, select, update, insert

from sqlalchemy import MetaData, Table

from sqlalchemy.orm import sessionmaker

# define meta information
metadata = MetaData(bind=cnx)

# fetch metadata from DB itself ...
ctfl_questions_table = Table('questions_meta', metadata, autoload=True)

Session = sessionmaker(bind=cnx)
session = Session()


# SQLite section >

TARGET_LOWEST_VERSION = 4  # see lt.TOOL_VERSION

q_list = list(lt.Questions.select().where((lt.Questions._stage == 3) & (lt.Questions._version >= TARGET_LOWEST_VERSION)).execute())

print(len(q_list), 'questions selected to add to MySQL')

# < SQLite section


# Добавить в таблицу MySQL данные из SQLite

from time import time

time_begin = time()

succeeded = 0

# q_list[0].__data__
for _i, q in enumerate(q_list):
    fields = q.__data__
    fields['template_id'] = fields['template']
    # del fields['id']  # catch error on duplicate
    del fields['template']
    # insert
    i = insert(ctfl_questions_table)
    i = i.values(fields)
    try:
	    session.execute(i)
	    succeeded += 1
    except Exception as e:
    	print()
    	print(type(e).__name__, str(e))
    	print()
    	continue
    if (_i and not _i % 10): print(end='.')
    if (_i and not _i % 500):
    	print(_i,)
    	print(time() - time_begin, 's elapsed')

print(_i + 1, 'completed,')
print(succeeded, 'successfully.')

session.commit()  # without this run Workbench crashed :) on `select count(*)`, and shown no rows on `select *`

print(time() - time_begin, 's elapsed total.')
