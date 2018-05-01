import csv
import os

from neo4j.v1 import GraphDatabase, basic_auth

DEFAULT_USER = "app92124873-nY8mkb"
DEFAULT_PASSWORD = "b.hrxpJRs9BVRq.ZqM9sSBJTMkU2OfR"
DEFAULT_DRIVER_URI = "bolt://hobby-ooiobamoecilgbkepmmbabal.dbs.graphenedb.com:24786"

db_username = os.environ.get("GRAPHENEDB_BOLT_USER", default=DEFAULT_USER)
db_password = os.environ.get("GRAPHENEDB_BOLT_PASSWORD", default=DEFAULT_PASSWORD)
driver_uri = os.environ.get("GRAPHENEDB_BOLT_URL", default=DEFAULT_DRIVER_URI)

db_driver = GraphDatabase.driver(driver_uri, auth=basic_auth(db_username, db_password))


def run_query(driver, query, *args, **kwargs):
    with driver.session() as session:
        return session.run(query, *args, **kwargs)


def create_works_with_relations(driver):
    query = '''
    MATCH ()<-[i1:includes]-(c:case)-[i2:includes]->()
    WHERE i1.timestamp - i2.timestamp = 1 and i1.performer<>i2.performer
    WITH i1.performer as p1name, i2.performer as p2name, COUNT(*) as count
    MERGE (p1:performer {name: p1name})
    MERGE (p2:performer {name: p2name})
    MeRGE (p1)-[w:works_with {count: count}]->(p2)
    return p1, w, p2
    '''
    run_query(driver, query)


def seed_data(driver):
    with open('./data/log-ws.csv') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=";")
        for row in reader:
            query = '''
            MERGE (c:case {id: {case}})
            MERGE (a:activity {name: {activity}})
            MERGE (p:performer {name: {performer}})
            MERGE (p)-[:performed {case: {case}, timestamp: toFloat({timestamp})} ]->(a)
            MERGE (c)-[:includes {performer: {performer}, timestamp: toFloat({timestamp})}]->(a)
            '''

            run_query(driver, query, row)


def drop_data(driver):
    run_query(driver, 'MATCH (n) DETACH DELETE n')


drop_data(db_driver)
seed_data(db_driver)
create_works_with_relations(db_driver)
