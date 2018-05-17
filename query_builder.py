class QueryBuilder:

    def __init__(self):
        self.pattern_length = None
        self.pattern_length_to = ''
        self.pattern_length_from = ''

        self.performer_one = '.*'
        self.performer_two = '.*'

        self.same_activity = False
        self.different_performer = False

    @property
    def length_range(self):
        if self.pattern_length:
            return self.pattern_length

        return '{}..{}'.format(self.pattern_length_from, self.pattern_length_to)

    def build(self):
        base_params = {"p1": self.performer_one, "p2": self.performer_two}

        query = f'''
        MATCH n=(p1)-[:works_with* {{case: $case}}]->(p2)
        WHERE
            p1.name =~$p1 and p2.name =~$p2
            {"and p1.name<>p2.name" if self.different_performer else ''}
        WITH relationships(n) as ww
        WITH ww[0] as first, ww[-1] as last, ww
        WHERE
            last.finish - first.start > 0
            {"and last.a2=first.a1" if self.same_activity else ''}
        RETURN ww
        '''

        return query, base_params
