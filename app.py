import os

from flask import Flask, render_template, request, make_response
from matplotlib import pyplot
from neo4j.v1 import GraphDatabase, basic_auth

from data_access_layer import DAL
from query_builder import QueryBuilder

DEFAULT_USER = "app92124873-nY8mkb"
DEFAULT_PASSWORD = "b.hrxpJRs9BVRq.ZqM9sSBJTMkU2OfR"
DEFAULT_DRIVER_URI = "bolt://hobby-ooiobamoecilgbkepmmbabal.dbs.graphenedb.com:24786"

app = Flask(__name__)
app.config["SECRET_KEY"] = "this should be changed"
db_username = os.environ.get("GRAPHENEDB_BOLT_USER", default=DEFAULT_USER)
db_password = os.environ.get("GRAPHENEDB_BOLT_PASSWORD", default=DEFAULT_PASSWORD)
driver_uri = os.environ.get("GRAPHENEDB_BOLT_URL", default=DEFAULT_DRIVER_URI)
driver = GraphDatabase.driver(driver_uri, auth=basic_auth(db_username, db_password))
dal = DAL(driver)


@app.route('/status')
def status():
    return "Hello, World!"


@app.route('/', methods=["GET"])
def main():
    return render_template('public/public.html', performers=dal.performers)


def query_pattern(query):
    # pattern is a list containing, all of the performers which belong to the pattern
    # found through the query specified from the pattern generator query interface (for each case)
    return [
        [
            [
                [record["name1"], record["id1"]],
                [record["name2"], record["id2"]]
            ]
            for record in dal.run_query(query, {'case': case})
        ]
        for case in dal.cases
    ]


def build_pattern_image(pattern):
    # Display color_case (the original wsa as determined by the log file)
    pyplot.subplot(2, 1, 1)
    pyplot.pcolor(dal.color_case, cmap='tab20', edgecolors='k', linewidths=1)

    # Display color_case_pattern (the related wsa' image about the matches found)
    pyplot.subplot(2, 1, 2)
    pyplot.pcolor(dal.color_case_from_pattern(pattern), cmap='tab20', edgecolors='k', linewidths=1)

    pyplot.savefig("foo.png")

    return open("foo.png", 'rb').read()


@app.route('/', methods=["POST"])
def search():
    query_builder = QueryBuilder()
    query_builder.performer_one = request.form["performer_1"]
    query_builder.performer_two = request.form["performer_2"]
    query_builder.same_activity = "same_activity" in request.form
    query_builder.different_performer = "different_performers" in request.form

    length_option = request.form["pattern_length_type"]
    print(length_option)
    if length_option == 'exactly':
        query_builder.pattern_length = request.form["exactly"]

    if length_option == 'at_least':
        query_builder.pattern_length_from = request.form["at_least"]

    if length_option == 'at_most':
        query_builder.pattern_length_to = request.form["at_most"]

    if length_option == 'between':
        query_builder.pattern_length_from = request.form["lower_bound"]
        query_builder.pattern_length_to = request.form["upper_bound"]

    query = query_builder.build()

    print('-' * 80)
    print(query.replace('    ', ' '))

    pattern = query_pattern(query)

    print('pattern')
    print(pattern)

    # match found in the first case, pattern[0]
    print('pattern[0]')
    print(pattern[0])
    print('len-pattern[0]')
    print(len(pattern[0]))
    # len(pattern[0]), count how many times a match with the considered pattern is found within the first case

    response = make_response(build_pattern_image(pattern))
    response.headers['Content-Type'] = 'image/png'
    return response


if __name__ == '__main__':
    app.run(debug=True)
