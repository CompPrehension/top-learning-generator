class NamespaceUtil:
    PATH_SEPARATORS = "/#"

    def __init__(self, prefix):
        self.prefix = prefix;
        self.base_cached = None;
    def get(self, name=''):
        return self.prefix + name;
    def base(self):
        if (self.base_cached == None):
            self.base_cached = self.prefix.rstrip(self.PATH_SEPARATORS);
        return self.base_cached
    def localize(self, fullname):
        '''Cut prefix from qualified fullname
         * @param fullname name with prefix, possibly the same as this namespace prefix
         * @return relative part of fullname (or whole fullname is prefixes do not match)
             '''
        if (fullname.startswith(self.prefix)):
            length = len(self.prefix);
            return fullname[length:];
