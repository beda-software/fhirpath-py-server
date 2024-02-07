import re
import aiohttp_cors
from aiohttp import web
from fhirpathpy import evaluate


def parse_request_data(data):
    expression = None
    resource = None
    context = None

    for param in data["parameter"]:
        if param["name"] == "expression":
            expression = param.get("valueString")
        elif param["name"] == "resource":
            resource = param.get("resource")
        elif param["name"] == "context":
            context = param.get("valueString")

    return expression, resource, context


def create_parameters(expression, context, resource):
    expression = re.sub(r"trace\(.*?\)", "", expression)

    if context:
        expression = f"{context}.{expression}"

    result = evaluate(resource, expression)

    return [
        {
            "name": "parameters",
            "part": [
                {"name": "evaluator", "valueString": "fhirpath-py"},
                {"name": "expression", "valueString": expression},
                {"name": "context", "valueString": context},
                {"name": "resource", "resource": resource},
            ],
        },
        {
            "name": "result",
            "part": [
                {
                    "name": "",
                    "resource": (
                        result[0]
                        if len(result) == 1
                        else None if len(result) == 0 else result
                    ),
                }
            ],
        },
    ]


async def handle_fhirpath(request):
    expression, resource, context = parse_request_data(await request.json())

    if expression is None or resource is None:
        return web.json_response({"error": "Not enough data"}, status=400)

    return web.json_response(
        {
            "resourceType": "Parameters",
            "id": "fhirpath",
            "parameter": create_parameters(expression, context, resource),
        }
    )


app = web.Application()

resource_fhirpath = app.router.add_resource("/fhir/$fhirpath")
route = resource_fhirpath.add_route("POST", handle_fhirpath)

cors = aiohttp_cors.setup(app)
allowed_domains = [
    "https://fhirpath-lab.com",
    "https://dev.fhirpath-lab.com",
    "https://fhirpath-lab.azurewebsites.net",
    "https://fhirpath-lab-dev.azurewebsites.net",
    "http://localhost:3000",
]

cors_options = {
    domain: aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
        allow_methods="*",
    )
    for domain in allowed_domains
}

cors.add(resource_fhirpath, cors_options)


if __name__ == "__main__":
    web.run_app(app, port=8081)
