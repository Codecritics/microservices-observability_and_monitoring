from flask import Flask, render_template, request

import json
import logging
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app, group_by="endpoint")

metrics.info('app_info', 'Frontend', version='1.0.0')

metrics.register_default(
    metrics.counter(
        'by_path_counter', 'Request count by request paths',
        labels={'path': lambda: request.path}
    )
)

endpoint_counter = metrics.counter('endpoint_counter', 'counting request by endpoint', labels={
    'endpoint': lambda: request.endpoint})


@app.route("/")
@endpoint_counter
def homepage():
    return render_template("main.html")


@app.route("/status")
@endpoint_counter
def healthcheck():
    response = app.response_class(
        response=json.dumps({"result": "OK - healthy"}),
        status=200,
        mimetype='application/json'
    )
    app.logger.info('Status request successful')
    return response


if __name__ == "__main__":
    app.run(threaded=True)
