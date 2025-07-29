from aiohttp import web
from fhirpathpy import evaluate, __version__ as fhirpathpy_version
import fhirpathpy.engine.nodes as nodes
import json
from decimal import Decimal


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
        if isinstance(result_item, nodes.ResourceNode):
            type_info = result_item.get_type_info()
            val = {
                "extension": [{"url": "http://fhir.forms-lab.com/StructureDefinition/resource-path", "valueString": result_item.propName}],
                "name": result_item.path if result_item.path else type_info.name if type_info and hasattr(type_info, "name") else "Unknown",
            }
            result.append(val)
            # convert all the known extension value types to use the actual property https://hl7.org/fhir/R4/extensibility.html
            match val["name"]:
                # primitive types
                case "base64binary":
                    val["valueBase64Binary"] = result_item.data
                case "boolean":
                    val["valueBoolean"] = result_item.data
                case "canonical":
                    val["valueCanonical"] = result_item.data
                case "code":
                    val["valueCode"] = result_item.data
                case "date":
                    val["valueDate"] = result_item.data
                case "dateTime":
                    val["valueDateTime"] = result_item.data
                case "decimal":
                    val["valueDecimal"] = result_item.data
                case "id":
                    val["valueId"] = result_item.data
                case "instant":
                    val["valueInstant"] = result_item.data
                case "integer":
                    val["valueInteger"] = result_item.data
                case "markdown":
                    val["valueMarkdown"] = result_item.data
                case "oid":
                    val["valueOid"] = result_item.data
                case "positiveInt":
                    val["valuePositiveInt"] = result_item.data
                case "string":
                    val["valueString"] = result_item.data
                case "time":
                    val["valueTime"] = result_item.data
                case "unsignedInt":
                    val["valueUnsignedInt"] = result_item.data
                case "uri":
                    val["valueUri"] = result_item.data
                case "url":
                    val["valueUrl"] = result_item.data
                case "uuid":
                    val["valueUuid"] = result_item.data

                # complex types
                case "Address":
                    val["valueAddress"] = result_item.data
                case "Annotation":
                    val["valueAnnotation"] = result_item.data
                case "Attachment":
                    val["valueAttachment"] = result_item.data
                case "CodeableConcept":
                    val["valueCodeableConcept"] = result_item.data
                case "Coding":
                    val["valueCoding"] = result_item.data
                case "ContactPoint":
                    val["valueContactPoint"] = result_item.data
                case "HumanName":
                    val["valueHumanName"] = result_item.data
                case "Identifier":
                    val["valueIdentifier"] = result_item.data
                case "Money":
                    val["valueMoney"] = result_item.data
                case "Period":
                    val["valuePeriod"] = result_item.data
                case "Quantity":
                    val["valueQuantity"] = result_item.data
                case "Range":
                    val["valueRange"] = result_item.data
                case "Ratio":
                    val["valueRatio"] = result_item.data
                case "Reference":
                    val["valueReference"] = result_item.data
                case "SampledData":
                    val["valueSampledData"] = result_item.data
                case "Signature":
                    val["valueSignature"] = result_item.data
                case "Timing":
                    val["valueTiming"] = result_item.data
                case "ContactDetail":
                    val["valueContactDetail"] = result_item.data
                case "Contributor":
                    val["valueContributor"] = result_item.data
                case "DataRequirement":
                    val["valueDataRequirement"] = result_item.data
                case "Expression":
                    val["valueExpression"] = result_item.data
                case "ParameterDefinition":
                    val["valueParameterDefinition"] = result_item.data
                case "RelatedArtifact":
                    val["valueRelatedArtifact"] = result_item.data
                case "TriggerDefinition":
                    val["valueTriggerDefinition"] = result_item.data
                case "UsageContext":
                    val["valueUsageContext"] = result_item.data
                case "Dosage":
                    val["valueDosage"] = result_item.data
                case "Meta":
                    val["valueMeta"] = result_item.data

                # everything else (fallback to raw json in extension)
                case _:
                    extVal = { 
                       "url": "http://fhir.forms-lab.com/StructureDefinition/json-value", 
                       "valueString": result_item.toJSON()
                    }
                    val["extension"].append(extVal)
        elif isinstance(result_item, Decimal):
            result.append({
                "name": "Decimal",
                "valueDecimal": float(result_item),
            })
        elif isinstance(result_item, nodes.FP_Quantity):
            result.append({
                "name": "Quantity",
                "valueQuantity": {
                    "value": float(result_item.value),
                    "unit": result_item.unit,
                }
            })
        elif isinstance(result_item, nodes.FP_DateTime):
            result.append({
                "name": "DateTime",
                "valueDateTime": result_item.asStr,
            })
        elif isinstance(result_item, nodes.FP_Time):
            result.append({
                "name": "Time",
                "valueTime": result_item.asStr,
            })
        else:
            if type(result_item).__name__ == "int":
                # case "int": # from raw fhirpath content, not FHIR data
                #    val["valueInteger"] = result_item.data
                result.append({
                    "name": "Integer",
                    "valueInteger": result_item 
                })
            else:
                result.append({
                    "name": type(result_item).__name__,
                    "valueString": json.dumps(result_item), 
                })

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
    try:
        expression, resource, context, terminology_server, variables, validate = (
            parse_request_data(await request.json())
        )

        if variables is None:
            variables = {}
        variables["resource"] = resource

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
    except ValueError as e:
        return web.json_response(
            {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "invalid",
                        "details": {"text": f"Invalid input: {str(e)}"}
                    }
                ]
            },
            status=400
        )
    except KeyError as e:
        return web.json_response(
            {
                "resourceType": "OperationOutcome", 
                "issue": [
                    {
                        "severity": "error",
                        "code": "required",
                        "details": {"text": f"Missing required field: {str(e)}"}
                    }
                ]
            },
            status=400
        )
    except Exception as e:
        return web.json_response(
            {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "exception",
                        "details": {"text": f"Internal server error: {str(e)}"}
                    }
                ]
            },
            status=500
        )
