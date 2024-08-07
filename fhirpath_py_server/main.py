import aiohttp_cors
from aiohttp import web

from fhirpath import handle_fhirpath


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
