import logging
import re
import requests

from flask import Flask, jsonify, render_template, request
from flask_opentracing import FlaskTracing
from jaeger_client import Config
from jaeger_client.metrics.prometheus import PrometheusMetricsFactory
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

metrics = PrometheusMetrics(app)
# static information as metric
metrics.info("app_info", "Trial", version="1.0.3")

logging.getLogger("").handlers = []
logging.basicConfig(format="%(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

metrics.register_default(
    metrics.counter(
        'by_path_counter', 'count  the requests by request paths',
        labels={'path': lambda: request.path}
    )
)

endpoint_counter = metrics.counter(
    'endpoint_counter', 'count the requests by endpoints',
    labels={'endpoint': lambda: request.endpoint}
)


def init_tracer(service):
    config = Config(
        config={
            "sampler": {"type": "const", "param": 1},
            "logging": True,
            "reporter_batch_size": 1,
        },
        service_name=service,
        validate=True,
        metrics_factory=PrometheusMetricsFactory(service_name_label=service),
    )

    # this call also sets opentracing.tracer
    return config.initialize_tracer()


tracer = init_tracer("trial")
flask_tracer = FlaskTracing(tracer, True, app)


@app.route("/")
def homepage():
    with tracer.start_span('get-python-jobs') as span:
        homepages = []
        res = requests.get('https://jobs.github.com/positions.json?description=python')
        span.set_tag('first-tag', len(res.json()))
        for result in res.json():
            try:
                homepages.append(requests.get(result['company_url']))
            except:
                return "Unable to get site for %s" % result['company']

    return jsonify(homepages)


if __name__ == "__main__":
    app.run(debug=True, )
