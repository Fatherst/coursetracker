FROM python:3.9

RUN mkdir /coursetracker

WORKDIR /coursetracker

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .