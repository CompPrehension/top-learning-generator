import os

# peewee must be installed! So `pwiz` is available in Scripts.


sqlite_db_file = 'c:/data/compp/control_flow_work.sqlite3'
orm_classes_file = 'sqlite_orm_classes.py'

cmd = f'python -m pwiz -e sqlite {sqlite_db_file}  > {orm_classes_file}'

ec = os.system(cmd)
if ec != 0:
	print('error executing shell command...')

print('Finished.')
