FROM python:3.12.1-slim

WORKDIR /usr/src/app/

RUN apt-get clean && apt-get -y update && apt-get install -y build-essential cmake libopenblas-dev liblapack-dev libopenblas-dev liblapack-dev

RUN apt-get install ffmpeg libsm6 libxext6  -y


COPY requirements.txt .

RUN pip install --upgrade pip setuptools

RUN pip install -r requirements.txt


COPY . .

RUN python3 manage.py makemigrations && python3 manage.py migrate

CMD [ "python3","manage.py","runserver", "0.0.0.0:3000" ]


EXPOSE 8000
