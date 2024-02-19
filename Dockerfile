FROM python:3.11

RUN addgroup --gid 1000 dockeruser
RUN adduser --disabled-login --uid 1000 --gid 1000 dockeruser
RUN mkdir -p /app/
RUN chown -R dockeruser:dockeruser /app/

RUN pip install poetry

USER dockeruser

COPY . /app
WORKDIR /app

RUN poetry install

CMD ["poetry", "run", "python", "fhirpath_py_server/main.py"]
