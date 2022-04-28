# import os.path
from glob import glob
from pathlib import Path

import rdflib  # pip install rdflib
# from rdflib import RDF

from fix_alg_names import fix_names_for_leaf_types
from ns4guestions import PREFIXES
from rdflib_utils import graph_lookup

# SEARCH_PATTERN = '*.ttl'
SEARCH_PATTERN = '**/*.ttl'
# SEARCH_PATTERN = '*.txt'

START_DIRS = [
	# "c:/Temp2/cntrflowoutput_v6/",
	# "c:/Temp2/cntrflowoutput_v7/",
	"c:/Temp2/compp/control_flow/qt/",
	# "c:/Temp2/compp/control_flow/qt_s/",
]
OUT_DIR = "c:/Temp2/cntrflowoutput_v7_str/"


FORMAT_IN = "turtle"
# FORMAT_OUT = "xml"
EXT_OUT = ".txt"
# # EXT_OUT = ".full.rdf"

# OVERWRITE_ANYWAY = True
# # OVERWRITE_ANYWAY = False

# INJECT_RDF = [
# 	# r'c:/D/Work/YDev/CompPr/c_owl/jena/control-flow-statements-domain-schema.rdf',
# ]

# # !! keep list of actions up to date!
# RDF_CLASSES = 'action sequence expr stmt alternative if else-if else func func_call loop while_loop do_while_loop do_until_loop for_loop foreach_loop'.split()


# NS_CODE = 'http://vstu.ru/poas/code#'
# LENGTH_TRESHOLD = 125


# def extract_strings(g):
# 	strings = []
# 	for prop_name in ("stmt_name", "name"):
# 		prop = rdflib.term.URIRef(NS_CODE + prop_name)
# 		for literal in g.objects(None, prop):
# 			s = literal.toPython()
# 			if len(s) > LENGTH_TRESHOLD:
# 				strings.append(s)

# 	return strings


def replace_strings(g, template_name):
	gl = graph_lookup(g, PREFIXES)
	changed, new_types_assigned = fix_names_for_leaf_types(g, gl, quiet=True)

	if changed and template_name and new_types_assigned:
		# append to file
		with open('new_types_assigned.txt', 'a') as f:
			f.write('%s\t%s\n' % (template_name, " ".join(sorted(new_types_assigned))))

	return changed



# def convert(file_in, file_out):
# 	g = rdflib.Graph()

# 	# g.bind("my", "http://vstu.ru/poas/ctrl_structs_2020-05_v1#")
# 	# g.bind("owl", "http://www.w3.org/2002/07/owl#")

# 	# print("reading ... ", end='')
# 	g.parse(location=file_in, format=FORMAT_IN)
# 	# print("done")
# 	# print("saving ... ", end='')
# 	g.serialize(file_out, format=FORMAT_OUT)


def read_rdf(*files, rdf_format=None):
	g = rdflib.Graph()
	for file_in in files:
		g.parse(location=file_in, format=rdf_format)
	return g


# KNOWN_STRING_HASHES = set()  # { (hash, size), (hash, size), ... }


# def dump_strings(strings):
# 	for s in strings:
# 		hash_, size = hash(s), len(s)
# 		hash_size = (hash_, size)
# 		if hash_size not in KNOWN_STRING_HASHES:
# 			KNOWN_STRING_HASHES.add(hash_size)
# 			filename = '%04x_%d' % (hash_ & 0xffff, size) + EXT_OUT
# 			filename = os.path.join(OUT_DIR, filename)
# 			if os.path.exists(filename):
# 				continue
# 			print(' writing string of length', size, '...')
# 			with open(filename, 'w') as f:
# 				f.write(s)


# def change_ext(filepath):
# 	return os.path.splitext(filepath)[0] + EXT_OUT


if __name__ == '__main__':
	for di, start_dir in enumerate(START_DIRS):
		for i, fp in enumerate(glob(start_dir + SEARCH_PATTERN, recursive=True)):

			print('%d/%-5d' % (di + 1, i + 1), fp, '...')
			try:
				# convert(fp, target_filepath)
				g = read_rdf(fp, rdf_format=FORMAT_IN)
				# strings = extract_strings(g)
				# dump_strings(strings)

				if replace_strings(g, Path(fp).stem):
					# write back to file ...
					# print("\t\twriting back")
					g.serialize(fp, format=FORMAT_IN)

			except Exception as e:
				print("#################")
				print("Error:", e)
				print("^^^^^^^^^^^^^^^^^")
				raise e

	print("done.")
	# print(len(KNOWN_STRING_HASHES), 'strings found')
	# sizes = [t[1] for t in KNOWN_STRING_HASHES]
	# print('Max  size:', max(sizes) if sizes else 0)
	# print('Mean size:', sum(sizes) / len(sizes) if sizes else 0)
