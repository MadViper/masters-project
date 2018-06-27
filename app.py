import json
import logging
import os
import sys

from flask import Flask, render_template, request, make_response
from matplotlib import pyplot
from neo4j.v1 import GraphDatabase, basic_auth

from dal import DAL, QueryBuilder

LOG_FORMAT = "[%(levelname)s]: %(message)s"
LOG_LEVEL = logging.DEBUG

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(LOG_FORMAT))
handler.setLevel(LOG_LEVEL)
logger.addHandler(handler)

logging.getLogger("neo4j.bolt").setLevel(logging.CRITICAL)

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("APP_SECRET", default="dummy_secret")
app.config["DB_USER"] = os.environ.get("DB_USER")
app.config["DB_PASSWORD"] = os.environ.get("DB_PASSWORD")
app.config["BOLT_URL"] = os.environ.get("BOLT_URL")
app.config["DB_CONNECTION_ENCRYPTED"] = os.environ.get("DB_CONNECTION_ENCRYPTED", default="ENCRYPTION_OFF")

dal = DAL(
    GraphDatabase.driver(
        app.config["BOLT_URL"],
        auth=basic_auth(
            app.config["DB_USER"],
            app.config["DB_PASSWORD"]
        )
    )
)


@app.route('/status')
def status():
    return "Hello, World!"


@app.route('/', methods=["GET"])
def main():
    return render_template('common/index.html')


@app.route('/explorer')
def explorer():
    return render_template(
        'public/explorer.html',
        db_config=json.dumps(
            {
                "db_username": app.config["DB_USER"],
                "db_password": app.config["DB_PASSWORD"],
                "db_url": app.config["BOLT_URL"],
                "encrypted": app.config["DB_CONNECTION_ENCRYPTED"]
            }
        )
    )


@app.route('/creator', methods=["GET"])
def creator():
    return render_template(
        'public/creator.html',
        performers=dal.performers
    )


def is_valid_path(ww):
    current_timestamp = ww[0]['start']

    for w in ww:
        if w['start'] != current_timestamp:
            return False
        current_timestamp = w['finish']

    return True


def build_pattern(query_builder: QueryBuilder):
    query, base_params = query_builder.build()
    logger.debug(query)

    patterns = []
    for case in dal.cases:
        params = {'case': case['id'], **base_params}
        result = dal.run_query(query, params)
        patterns.append(
            [record['ww'] for record in result if is_valid_path(record['ww'])]
        )

    return patterns


def build_pattern_image(pattern):
    # Display color_case (the original wsa as determined by the log file)
    pyplot.subplot(2, 1, 1)
    pyplot.pcolor(dal.color_case, cmap='tab20', edgecolors='k', linewidths=1)

    # Display color_case_pattern (the related wsa' image about the matches found)
    pyplot.subplot(2, 1, 2)
    pyplot.pcolor(dal.color_case_from_pattern(pattern), cmap='tab20', edgecolors='k', linewidths=1)

    pyplot.savefig("foo.png")

    return open("foo.png", 'rb').read()


@app.route('/creator', methods=["POST"])
def search():
    query_builder = QueryBuilder()
    query_builder.performer_one = request.form["performer_1"]
    query_builder.performer_two = request.form["performer_2"]
    query_builder.same_activity = "same_activity" in request.form
    query_builder.different_performer = "different_performers" in request.form

    length_option = request.form["pattern_length_type"]

    if length_option == 'exactly':
        query_builder.pattern_length = request.form["exactly"]

    if length_option == 'at_least':
        query_builder.pattern_length_from = request.form["at_least"]

    if length_option == 'at_most':
        query_builder.pattern_length_to = request.form["at_most"]

    if length_option == 'between':
        query_builder.pattern_length_from = request.form["lower_bound"]
        query_builder.pattern_length_to = request.form["upper_bound"]

    pattern = build_pattern(query_builder)
    response = make_response(build_pattern_image(pattern))
    response.headers['Content-Type'] = 'image/png'
    return response


if __name__ == '__main__':
    app.run(debug=True)
