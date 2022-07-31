from flask import Flask, render_template, request

import logging
from jaeger_client import Config
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app, group_by="endpoint")

metrics.info('app_info', 'Frontend', version='1.0.3')

metrics.register_default(
    metrics.counter(
        'by_path_counter', 'Request count by request paths',
        labels={'path': lambda: request.path}
    )
)

endpoint_counter = metrics.counter('endpoint_counter', 'counting request by endpoint', labels={
    'endpoint': lambda: request.endpoint})


# Tracing Initialization
def init_tracer(service_name="frontend"):
    logging.getLogger('').handlers = []
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)

    config = Config(
        config={
            'logging': True,
        },
        service_name=service_name,
        validate=True
    )

    return config.initialize_tracer()


tracer = init_tracer("frontend")


@app.route("/")
@endpoint_counter
def homepage():
    return render_template("main.html")


if __name__ == "__main__":
    app.run(threaded=True)
