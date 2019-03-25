FROM python:3.7-alpine

# Depencencies for psycopg2 and uwsgi
RUN apk add build-base linux-headers postgresql-dev
RUN python3 -m pip install uwsgi==2.0.18

RUN addgroup uwsgi && adduser -DH -G uwsgi uwsgi

WORKDIR /code
ADD requirements.txt /code/
ADD setup.py /code/
RUN echo 0.0.0-0-fakeForDocker > version.txt
ADD yakbak /code/yakbak/
RUN python3 -m pip install -r requirements.txt -e .

ADD alembic /code/alembic/
ADD alembic.ini /code/
ADD wsgi.py /code/
ADD uwsgi.ini /code/
ADD start-web.sh /code/

EXPOSE 5000

CMD ["uwsgi", "--ini", "/code/uwsgi.ini"]
