from flask import Flask, request, jsonify, json
from flask_pymongo import PyMongo
from flask_opentracing import FlaskTracing
from jaeger_client import Config
import logging

from os import getenv

from prometheus_flask_exporter import PrometheusMetrics

JAEGER_HOST = getenv('JAEGER_AGENT_HOST', 'localhost')

app = Flask(__name__)

app.config['MONGO_DBNAME'] = 'example-mongodb'
app.config['MONGO_URI'] = 'mongodb://example-mongodb-svc.default.svc.cluster.local:27017/example-mongodb'
mongo = PyMongo(app)

metrics = PrometheusMetrics(app, group_by='endpoint')
metrics.info('app_info', 'Backend', version='1.0.0')

metrics.register_default(
    metrics.counter(
        'by_path_counter', 'Request count by request paths',
        labels={'path': lambda: request.path}
    )
)

by_full_path_counter = metrics.counter('full_path_counter', 'counting requests by full path', labels={
    'full_path': lambda: request.full_path})

endpoint_counter = metrics.counter(
    'endpoint_counter', 'Request count by endpoints',
    labels={'endpoint': lambda: request.endpoint}
)


def init_tracer(service):
    logging.getLogger('').handlers = []
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)

    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
            'local_agent': {'reporting_host': JAEGER_HOST},
        },
        service_name=service,
    )

    # this call also sets opentracing.tracer
    return config.initialize_tracer()


tracer = init_tracer('backend')
tracing = FlaskTracing(tracer, True, app)


@app.route('/')
@endpoint_counter
@tracing.trace()
@by_full_path_counter
def homepage():
    with tracer.start_span('hello-world'):
        message = "Hello World"
    return message


@app.route('/api')
@endpoint_counter
@by_full_path_counter
def my_api():
    with tracer.start_span('api'):
        answer = "something"
    return jsonify(repsonse=answer)


@app.route('/star', methods=['POST'])
@endpoint_counter
@tracing.trace()
@by_full_path_counter
def add_star():
    try:
        star = mongo.db.stars
        name = request.json['name']
        distance = request.json['distance']
        star_id = star.insert({'name': name, 'distance': distance})
        new_star = star.find_one({'_id': star_id})
        output = {'name': new_star['name'], 'distance': new_star['distance']}
    except Exception as e:
        return jsonify({'message': e})
    else:
        return jsonify({'result': output})


@endpoint_counter
@by_full_path_counter
@tracing.trace()
@app.route('/status')
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
