from aiohttp import web
from fhirpathpy import evaluate, __version__ as fhirpathpy_version


def parse_request_data(data):
    expression = None
    resource = None
    context = None
    validate = None
    variables = None
    terminology_server = None

    for param in data["parameter"]:
        if param["name"] == "expression":
            expression = param.get("valueString")
        elif param["name"] == "resource":
            resource = param.get("resource")
        elif param["name"] == "context":
            context = param.get("valueString")
        elif param["name"] == "validate":
            validate = param.get("valueBoolean")
        elif param["name"] == "variables":
            variables = {
                part["name"]: part.get("valueString") for part in param.get("part", [])
            }
        elif param["name"] == "terminologyserver":
            terminology_server = param.get("valueString")

    return expression, resource, context, terminology_server, variables, validate


def node_results_to_types(node_results):
    result = []
    for result_item in node_results:
        item_type = type(result_item).__name__
        result.append({"name": item_type, "valueString": result_item})

    return result


def create_parameters(
    expression, resource, context, terminology_server, variables, validate
):
    results = []

    resource_type = resource.get("resourceType")
    resource_type_path = f"{resource_type}." if resource_type else ""

    if context:
        context_nodes = evaluate(resource, context, variables)
        for context_node_index, context_node in enumerate(context_nodes):
            result_data = {
                "result": [],
                "trace": [],
                "context": f"{resource_type_path}{context}[{context_node_index}]",
            }

            context_node_results = evaluate(context_node, expression, variables)
            result_data["result"] = node_results_to_types(context_node_results)

            results.append(
                {
                    "name": "result",
                    "part": result_data["result"],
                    "valueString": result_data.get("context", expression),
                }
            )

    else:
        result_data = {
            "result": [],
            "trace": [],
        }

        node_results = evaluate(resource, expression, variables)
        result_data["result"] = node_results_to_types(node_results)

        results.append(
            {
                "name": "result",
                "part": result_data["result"],
            }
        )

    return [
        {
            "name": "parameters",
            "part": [
                {
                    "name": "evaluator",
                    "valueString": f"fhirpath-py {fhirpathpy_version}",
                },
                *([{"name": "context", "valueString": context}] if context else []),
                {"name": "expression", "valueString": expression},
                {"name": "resource", "resource": resource},
                {
                    "name": "terminologyServerUrl",
                    "valueString": terminology_server,
                },
                {
                    "name": "variables",
                    **(
                        {
                            "part": [
                                {"name": k, "valueString": v}
                                for k, v in variables.items()
                            ]
                        }
                        if variables
                        else {}
                    ),
                },
            ],
        },
        *results,
    ]


async def handle_fhirpath(request):
    expression, resource, context, terminology_server, variables, validate = (
        parse_request_data(await request.json())
    )

    if expression is None or resource is None:
        return web.json_response({"error": "Not enough data"}, status=400)

    return web.json_response(
        {
            "resourceType": "Parameters",
            "id": "fhirpath",
            "parameter": create_parameters(
                expression, resource, context, terminology_server, variables, validate
            ),
        }
    )
