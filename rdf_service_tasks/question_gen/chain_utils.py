# chain_utils.py


# # Вариант 1, с дополнительными атрибутами chain, result, chain_result

# class chain_proxy:
#     def __init__(self, wrapper, returner):
#         self.__wrapper = wrapper
#         self.__returner = returner

#     def __getattr__(self, attr):
#         def proxy(*args, **kw):
#             res = getattr(self.__wrapper._wrappee, attr).__call__(*args, **kw)
#             return self.__returner(res)
#         return proxy
    

# class chained:
#     '''Simply: if `obj.foo()` called as `obj.chain.foo()`, then is returns `foo` (ignoring actual return value).
#     Just wrap `obj` first: `obj = chained(obj)`
#     That enables chaining when base object does not support it.'''
#     def __init__(self, wrappee, guard=None):
#         self._wrappee = wrappee
#         self._guard = guard
#         self.chain = chain_proxy(self, self.__return_self)
#         self.result = wrappee
#         self.chain_result = chain_proxy(self, self.__return_wrappee)
        
#     def __getattr__(self, attr):
#         return getattr(self._wrappee, attr)
        
#     def __return_self(self, res):
#         if self._guard: self.__check_result(res)
#         return self
        
#     def __return_wrappee(self, res):
#         if self._guard: self.__check_result(res)
#         return self._wrappee
        
#     def __check_result(self, res):
#         if self._guard and not self._guard(res):
#             self.__warn(attr, res)
        
#     def __warn(self, attr, res):
#         ### raise RuntimeWarning
#         print('Warning: Call to .%s(...) returned %s' % (attr, str(res)))


# def example1():
# 	d = chained({1:2, 3:4})

# 	d.get(1)  # 2

# 	(d
# 	 .chain.get(1)
# 	 .chain_result.get(1)
# 	 .get(3)
# 	)  # 4




# Вариант 2, с дополнительными атрибутами builder, result, но без промежуточных вызовов.

class builder:
    '''chained builder. Wrap an unchainable object and chain it as long as you need.
    Then get last returned value via `.result` or wrapped object via `.builder`.
    `guard` is intended to notify you when a returned result indicates something bad.
    '''
    def __init__(self, wrappee, guard=None):
        self.builder = wrappee
        self.result = None
        self._guard = guard

    def __getattr__(self, attr):
        def proxy(*args, **kw):
            self.result = getattr(self.builder, attr).__call__(*args, **kw)
            if self._guard: self.__check_result(attr)
            return self
        return proxy

    # methods for `guard` feature:
    def __check_result(self, attr):
        if not self._guard(self.result):
            self.__warn(attr)

    def __warn(self, attr):
        ### raise RuntimeWarning
        print('Warning: Call to .%s() returned %s' % (attr, str(self.result)))


def example2():
	d = builder({1:2, 3:4})

	d.get(1).get(3).result  # 4

	d.get(1).get(3).builder  # {1: 2, 3: 4}

	d.get(1).get(3).builder.get(1)  # 2

	builder({1:2, 3:0}, bool).get(3).get(3).result
	# Warning: Call to .get() returned 0
	# Warning: Call to .get() returned 0
	# >>> 0


if __name__ == '__main__':
	# example1()
	example2()


