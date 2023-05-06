# sparql_wrapper.py

'''
Class that encapsulates access to sparql endpoint
(Apache Jena Fuseki in this case)
'''

import json

from pyfuseki import FusekiQuery, FusekiUpdate
from SPARQLWrapper import SPARQLWrapper, POST, JSON, TURTLE


class Sparql:
	def __init__(self, fuseki_host=None, db_name=None,
		query_url=None, update_url=None, credentials=None,
		post_update_hooks=None):
		self.fuseki_host = fuseki_host
		self.db_name = db_name
		self.query_url = query_url
		self.update_url = update_url
		self.credentials = credentials
		self.post_update_hooks = post_update_hooks or []
		self.fuseki_query  = None
		self.fuseki_update = None
		self.sw_query  = None
		self.sw_update = None

	def query(self, *args, **kw):
		if not self.fuseki_query and not self.sw_query:
			if not self.query_url and self.fuseki_host and self.db_name:
				self.fuseki_query  = FusekiQuery (self.fuseki_host, self.db_name)
				### print("fuseki_query created")
			else:
				self.sw_query = SPARQLWrapper(self.query_url)
				# self.sw_query.setReturnFormat(JSON)

		if self.fuseki_query:
			query_result = self.fuseki_query.run_sparql(*args, **kw)
			if 'return_format' in kw and kw['return_format'] == 'json':
				result = json.loads(b''.join(list(query_result)))
			else:
				result = query_result
			# {'head': {'vars': ['name']},
			#  'results': {'bindings': [
			#    {'name': {'type': 'literal', 'value': '1__memcpy_s'}},
			#    {'name': {'type': 'literal', 'value': '5__strnlen_s'}}]}}
		elif self.sw_query:
			sparql_str = args[0]
			self.sw_query.setQuery(sparql_str)
			ret_format = None
			if 'return_format' in kw:
				if kw['return_format'] == 'json':
					ret_format = JSON
				if kw['return_format'] == 'turtle':
					ret_format = TURTLE
				if ret_format:
					self.sw_query.setReturnFormat(ret_format)

			if self.credentials:
				self.sw_query.setCredentials(*self.credentials)

			result = self.sw_query.queryAndConvert()
			###
			if ret_format == 'json':
				try:
					result['results']['bindings'] = list(result['results']['bindings'])
				except: ## Exception as e:
					raise  # ??
			elif ret_format == 'turtle' and type(result) is bytes:
				result = [result]  # make list of byte chunks
			self.sw_query.resetQuery()
		return result

	# def update(self, sparql_str):
	def update(self, *args, **kw):
		if not self.fuseki_update and not self.sw_update:
			if not self.update_url and self.fuseki_host and self.db_name:
				self.fuseki_update  = FusekiUpdate(self.fuseki_host, self.db_name)
				### print("fuseki_update created")
			else:
				self.sw_update = SPARQLWrapper(self.update_url)

		if self.fuseki_update:
			result = self.fuseki_update.run_sparql(*args, **kw)
		elif self.sw_update:
			sparql_str = args[0]
			self.sw_update.setQuery(sparql_str)
			self.sw_update.setMethod(POST)

			if self.credentials:
				self.sw_update.setCredentials(*self.credentials)

			result = self.sw_update.query()
			self.sw_update.resetQuery()

		if self.post_update_hooks:
			for hook in self.post_update_hooks:
				hook()
		return result
