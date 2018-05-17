import csv
import os
import sys

from neo4j.v1 import GraphDatabase, basic_auth

DEFAULT_CSV_FILE = './data/log-ws.csv'

db_driver = GraphDatabase.driver(
    os.environ.get("BOLT_URL"),
    auth=basic_auth(os.environ.get("DB_USER"),
                    os.environ.get("DB_PASSWORD"))
)


def get_csv_file():
    try:
        return sys.argv[1]
    except IndexError:
        return DEFAULT_CSV_FILE


def run_query(query, *args, **kwargs):
    with db_driver.session() as session:
        return session.run(query, *args, **kwargs)


def create_works_with_relations():
    query = '''
    MATCH (a1)<-[i1:includes]-(c:case)-[i2:includes]->(a2)
    WHERE i1.timestamp - i2.timestamp = 1
    WITH
        c.id as case,
        i1.performer as p1name, i2.performer as p2name,
        a1.name as a1name, a2.name as a2name,
        i1.timestamp as finish, i2.timestamp as start
    MERGE (p1:performer {name: p1name})
    MERGE (p2:performer {name: p2name})
    MERGE (p2)-[w:works_with {case: case, a1: a1name, start: start, a2: a2name, finish: finish}]->(p1)
    RETURN p1, w, p2
    '''
    run_query(query)


def seed_data(records):
    for record in records:
        create_query = '''
        MERGE (c:case {id: {case}})
        MERGE (a:activity {name: {activity}})
        MERGE (p:performer {name: {performer}})
        MERGE (p)-[:performed {case: {case}, timestamp: toFloat({timestamp})} ]->(a)
        MERGE (c)-[:includes {performer: {performer}, timestamp: toFloat({timestamp})}]->(a)
        '''

        run_query(create_query, record)


def drop_data():
    run_query('MATCH (n) DETACH DELETE n')


def main():
    drop_data()
    with open(get_csv_file()) as csv_file:
        reader = csv.DictReader(csv_file, delimiter=";")
        seed_data(reader)
    create_works_with_relations()


if __name__ == '__main__':
    main()
