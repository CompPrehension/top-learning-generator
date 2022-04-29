# misc.watch_rdf_db.py

from datetime import datetime
import json


class StateWatcher:
	'saves stats provided by providers to file as json'
	def __init__(self, data_providers: list, log_filepath='stats_shot.log', add_params:dict = None):
		assert data_providers, 'data_providers must contain at least one function'
		self.data_providers = data_providers
		self.log_filepath = log_filepath
		self.add_params = add_params or {}

	def take_snapshot(self):
		# remember the moment in time
		dt = datetime.now()
		dt_str = dt.strftime('%Y.%m.%d, %H:%M:%S')
		result = dict(time=dt_str)
		# add special (watcher-specific, constant) params
		result.update(self.add_params)
		# gather data
		for provider in self.data_providers:
			data = provider()
			if not isinstance(data, dict):
				data = {provider.name: data}
			result.update(data)

		# save to file (append mode)
		with open(self.log_filepath, 'a') as f:
			json.dump(result, f, ensure_ascii=False)
			f.write('\n')  # separate records
