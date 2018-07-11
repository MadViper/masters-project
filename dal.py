import collections
import logging
from copy import deepcopy
from functools import lru_cache

from neo4j.exceptions import ServiceUnavailable
from neo4j.v1 import GraphDatabase, basic_auth, Driver, Session

logger = logging.getLogger("pywsi.dal")


class DAL(object):

    def __init__(self, driver: Driver):
        self.driver = driver

    @classmethod
    def from_config(cls, config):
        try:
            driver = GraphDatabase.driver(
                config["BOLT_URL"],
                auth=basic_auth(config["DB_USER"], config["DB_PASSWORD"])
            )
        except ServiceUnavailable as e:
            logger.warning("Could not connect to neo4j")
            driver = None

        return cls(driver)

    @property
    def session(self) -> Session:
        return self.driver.session()

    def run_query(self, query, *args, **kwargs):
        logger.debug("Running query <{}>".format(query))
        with self.session as session:
            return session.run(query, *args, **kwargs)

    @property
    @lru_cache(maxsize=32)
    def performers(self):
        q = "MATCH (p:performer) RETURN p.name as name ORDER BY p.name"
        return [record['name'] for record in self.run_query(q)]

    @property
    @lru_cache(maxsize=32)
    def cases(self):
        query = '''
        MATCH n=(c:case)-[i:includes]->()
        WITH c, i.timestamp as timestamps
        WITH c, min(timestamps) as timestamp
        SET c.timestamp = timestamp
        RETURN c as case order by c.timestamp
        '''
        return [record['case'] for record in self.run_query(query)]

    @property
    @lru_cache(maxsize=32)
    def performers_by_case(self):
        performers = collections.defaultdict(list)

        q = "match ()<-[r:performed]-(p:performer) RETURN r.case as case, p.name as performer order by r.timestamp"
        for record in self.run_query(q):
            performers[record["case"]].append(record["performer"])

        return performers

    @property
    def color_case(self):
        # Prototype uses colormap (from matplotlib) to display wsa (and wsa')
        # Note: there are many drawbacks (e.g., at most 10 different performers are displayed)
        # So: another way should be considered (preferably web-based architecture)

        # color_case is the data structure used to generate wsa through the colormap function
        # each color_case is a two indexes list:
        #   the first index is about the number of the case,
        #   the second is about performers involved in that case
        color_case = []

        for case, performers in self.performers_by_case.items():
            color_tmp = [self.performers.index(performer) for performer in performers]
            color_case.append(color_tmp)

        logger.info('original color_case: {}'.format(color_case))

        # One more drawback of using color map is that to generate the correct colormap,
        # all the rows (cases) should have the same length (the same number of activities)
        # so color_case is modified to make all rows the same length (the max_case_length)
        # and a new value is inserted (total number of performers + 1) in color_case  to fill in the blanks
        max_case_length = max(len(case) for case in color_case)
        logger.info('max case length: {}'.format(max_case_length))
        blank_value = len(self.performers) + 1
        color_case = [case + [blank_value] * (max_case_length - len(case)) for case in color_case]
        logger.info('extended color_case: {}'.format(color_case))
        color_case.reverse()

        return color_case

    def color_case_from_pattern(self, patterns_by_case):
        stat_pattern = [len(case_patterns) for case_patterns in patterns_by_case]
        logger.info('pattern stat: {}'.format(stat_pattern))

        # building color_case_pattern from color_case.
        # color_case_pattern is the list containing the number of performers matching the pattern after the query
        # color_case_pattern would be used to build a colormap describing wsa',
        # i.e. the wsa image after the match with the considered pattern
        # we consider to build both wsa and wsa' images, to promote visual comparison to help users to easily recognize
        # the matches found considering a pattern expressed through the query

        # color_case_pattern is built from color_case (the original wsa)
        # and then modified according to the results of the query defined through the query pattern interface
        color_case_pattern = deepcopy(self.color_case)

        # reversing color_case_pattern to have the situation as in the original color_case
        # (before reversing for displaying purposes)
        color_case_pattern.reverse()

        # building matches in color_case_pattern; for any of the match found,
        # the corresponding position in the color_case_pattern list
        # is filled with the value len(performer_dist)+1 (that is
        # the same color used in color_case to fill in the blanks).
        # To verify whether another color for the match would be more appropriated,
        # may be the color complementary to the color of the corresponding performer:
        # e.g., computed by MAX_COLOR - works_with[j][1].index(pattern[j][i][0][1])

        mark = len(self.performers) + 1
        for case_index, case_patterns in enumerate(patterns_by_case):
            case = self.cases[case_index]
            for pattern in case_patterns:
                x = int(pattern[0]['start'] - case['timestamp'])
                y = int(pattern[-1]['finish'] - case['timestamp'])
                color_case_pattern[case_index][x] = mark
                color_case_pattern[case_index][y] = mark

        logger.info("pattern color_case: {}".format(color_case_pattern))

        # reversing color_case_pattern for visualization purposes
        # (i.e., to put first case at the top row of the colormap)
        color_case_pattern.reverse()

        return color_case_pattern


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
        MATCH n=(p1)-[:works_with*{self.length_range} {{case: $case}}]->(p2)
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
