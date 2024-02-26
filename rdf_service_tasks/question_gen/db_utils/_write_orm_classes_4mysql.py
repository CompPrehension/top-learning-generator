"""
_write_orm_classes_4mysql.py

Documentation online: https://docs.peewee-orm.com/en/latest/peewee/playhouse.html#pwiz
"""

import os

# peewee must be installed! So `pwiz` is available in Scripts.


db_name = 'test_db'
db_user = 'remote'
db_pass = '!E3f5c712'  # !E3f5c712
orm_classes_file = 'mysql_orm_classes.py'

tables = ','.join(['questions_meta'])


# with open('p.bin', 'w') as f:
# 	f.write(db_pass + '\n')

cmd = f'python -m pwiz -e mysql -u {db_user} -P -o -t {tables} {db_name}  > {orm_classes_file}'  ## < p.bin
cmd = f"echo {db_pass}\n | {cmd}"

	# -o	table column order is preserved

ec = os.system(cmd)
if ec != 0:
	print('error executing shell command...')

print('Finished.')
