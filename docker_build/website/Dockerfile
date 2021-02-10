FROM python:3
ENV PYTHONUNBUFFERED 1
RUN mkdir /website
WORKDIR /website
ADD requirements.txt /website/
RUN pip install -r requirements.txt
EXPOSE 8000
ADD . /website/
RUN python3 /website/tradingplatform/manage.py collectstatic --noinput