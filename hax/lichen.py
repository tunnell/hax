"""Lichens grows on trees

Extend the Minitree produced DataFrames with derivative values.
"""
from hax import cuts


class Lichen(object):
    pass


class RangeLichen(Lichen):
    allowed_range = None  # tuple of min then max
    variable = None  # variable name in DataFrame

    def get_allowed_range(self):
        if self.allowed_range is None:
            raise NotImplemented()

    def get_min(self):
        if self.variable is None:
            raise NotImplemented()
        return self.allowed_range[0]

    def get_max(self):
        if self.variable is None:
            raise NotImplemented()
        return self.allowed_range[0]

    def pre(self, df):
        return df

    def process(self, df):
        df[self.__class__.__name__] = cuts.range_selection(df,
                                                           self.variable,
                                                           self.allowed_range)

        return df

    def post(self, df):
        return df.drop('temp', 1)


class ManyLichen(Lichen):
    lichen_list = []

    def process(self, df):
        for lichen in self.lichen_list:
            df = lichen.process(df)
        return df
