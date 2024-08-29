FROM python:3.10

RUN mkdir -p /usr/src/factgenie
WORKDIR /usr/src/factgenie

COPY . /usr/src/factgenie

RUN pip install -e .[deploy]

EXPOSE 80
ENTRYPOINT ["gunicorn", "--env", "SCRIPT_NAME=", "-b", ":80", "-w", "1", "--threads", "2", "factgenie.cli:create_app()"]
