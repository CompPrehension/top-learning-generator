class NamespaceUtil:
    PATH_SEPARATORS = "/#"

    def __init__(self, prefix):
        self.prefix = prefix;
        self.base_cached = None;
    def get(self, name=''):
        return self.prefix + name;
    def base(self):
        if (self.base_cached == None):
            self.base_cached = NamespaceUtil.make_base(self.prefix);
        return self.base_cached
    @classmethod
    def make_base(cls, s: str):
    	return s.rstrip(cls.PATH_SEPARATORS);
    def localize(self, fullname):
        '''Cut prefix from qualified fullname
         * @param fullname name with prefix, possibly the same as this namespace prefix
         * @return relative part of fullname (or whole fullname is prefixes do not match)
             '''
        if (fullname.startswith(self.prefix)):
            length = len(self.prefix);
            return fullname[length:];
