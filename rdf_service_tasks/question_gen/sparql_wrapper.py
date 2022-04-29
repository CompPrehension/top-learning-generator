# sparql_wrapper.py

'''
Class that incapsulates acees to sparql endpoint
(Apache Jena Fuseki in this case)
'''

from pyfuseki import FusekiQuery, FusekiUpdate

# from SPARQLWrapper import SPARQLWrapper, POST


class Sparql:
	def __init__(self, endpoint_host, db_name, post_update_hooks=None):
		self.endpoint_host = endpoint_host
		self.db_name = db_name
		self.post_update_hooks = post_update_hooks or []
		self.fuseki_query  = None
		self.fuseki_update = None
		# self.sw_update = None

	def query(self, *args, **kw):
		if not self.fuseki_query:
			self.fuseki_query  = FusekiQuery (self.endpoint_host, self.db_name)
			### print("fuseki_query created")
		result = self.fuseki_query.run_sparql(*args, **kw)
		return result

	# def update(self, sparql_str):
	def update(self, *args, **kw):
		if not self.fuseki_update:
			self.fuseki_update  = FusekiUpdate(self.endpoint_host, self.db_name)
			# self.sw_update = SPARQLWrapper(self.endpoint_host.rstrip('/') + '/' + self.db_name + '/update')
			### print("fuseki_update created")
		result = self.fuseki_update.run_sparql(*args, **kw)
		# self.sw_update.resetQuery()
		# # self.sw_update.setMethod(POST)
		# self.sw_update.setQuery(sparql_str)
		# result = self.sw_update.query()
		if self.post_update_hooks:
			for hook in self.post_update_hooks:
				hook()
		return result
