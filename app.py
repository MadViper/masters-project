import json
import os
import threading

from flask import Flask, flash, request, redirect
from flask import render_template, make_response
from werkzeug.utils import secure_filename

import dbms
from dal import DAL, QueryBuilder
from logger import logger

app = Flask(__name__)
app.config.from_object('config.DevelopmentConfig')

dal = DAL.from_config(app.config)


@app.route('/status')
def status():
    return "Hello, World!"


@app.route('/', methods=["GET"])
def main():
    return render_template('common/index.html')


def allowed_file(filename):
    extension = filename.rsplit('.', 1)[1].lower()
    return '.' in filename and extension in {'csv'}


@app.route('/uploader', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':

        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part in the request')
            return redirect(request.url)

        file = request.files['file']

        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('File not selected')
            return redirect(request.url)

        if allowed_file(file.filename):
            file_name = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
            file.save(file_path)
            flash("File uploaded successfully")
            # Start worker to initialize database
            threading.Thread(
                name="neo4j-init",
                target=dbms.load_file,
                args=(file_path,)
            ).start()
        else:
            flash('File should have .csv extension')

    return render_template("public/uploader.html")


@app.route('/explorer', methods=["GET", "POST"])
def explorer():
    case_id = ".*"
    performer = ".*"
    activity = ".*"
    works_with = False
    performed = False
    includes = False

    return_entities = set()

    if request.method == "POST":
        case_id = request.form['case']
        performer = request.form['performer']
        activity = request.form['activity']
        includes = "includes" in request.form
        performed = "performed" in request.form
        works_with = "works_with" in request.form

    if includes:
        return_entities.update(("nc", "ri", "na"))

    if performed:
        return_entities.update(("na", "rp", "np"))

    if works_with or not return_entities:
        return_entities.update(("np", "rw"))

    cypher = f'''
        MATCH
            n=
            (nc:case)-[ri:includes]->
            (na:activity)<-[rp:performed]-
            (np:performer)-[rw:works_with]->()
        WHERE
            nc.id =~ "{case_id}" and
            rp.case =~ "{case_id}" and
            rw.case =~ "{case_id}" and
            np.name =~ "{performer}" and
            na.name =~ "{activity}"
        RETURN {",".join(return_entities or ["n"])}
    '''

    logger.debug(cypher)

    return render_template(
        'public/explorer.html',
        db_config=json.dumps(
            {
                "server_url": app.config["BOLT_URL"],
                "server_user": app.config["DB_USER"],
                "server_password": app.config["DB_PASSWORD"],
                "encrypted": app.config["DB_CONNECTION_ENCRYPTED"],
                "initial_cypher": cypher
            }
        ),
        cases=[case['id'] for case in dal.cases],
        performers=dal.performers,
        activities=dal.activities,
        selected_activity=activity,
        selected_performer=performer,
        selected_case=case_id,
        display_works_with=works_with,
        display_performed=performed,
        display_includes=includes
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
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot

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
    app.run(debug=app.config['DEBUG'])
