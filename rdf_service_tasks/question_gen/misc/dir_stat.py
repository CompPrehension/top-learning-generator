# misc.dir_stat.py

import fs


def dir_size(directory: 'str or path-like'):
	'Calculate total size of a directory in bytes as sum of all files in it, including subdirectories.'
	my_fs = fs.open_fs(directory)
	try:
		return sum(
		    info.size
		    for _path, info in my_fs.walk.info(namespaces=['details'])
		    if not info.is_dir
		)
	except Exception as e:
		print(e)
	return -1



def _try():  # try & debug it
	import sys
	sys.path.append('../../../../c_owl')
	from common_helpers import Checkpointer

	watch_dir = r'c:\D\Work\YDev\CompPr\fuseki\apache-jena-fuseki-4.2.0\control_flow' "\\"

	ch = Checkpointer()

	my_fs = fs.open_fs(watch_dir)
	ch.hit('open fs')

	summ = 0

	for match in my_fs.glob("**/*.*", namespaces=['details']):
	    # print(f"{match.path} is {match.info.size} bytes long")
	    summ += match.info.size

	ch.hit('glob')

	print('summ :', summ)

	bytes_in_dir = sum(
	    info.size
	    for _path, info in my_fs.walk.info(namespaces=['details'])
	    if not info.is_dir
	)
	ch.hit('walk')  # 1..3 times faster than glob

	print('total:', bytes_in_dir)

if __name__ == '__main__':
	_try()
	_try()
