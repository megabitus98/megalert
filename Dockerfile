FROM python:3.9.2-slim

WORKDIR /megalert

COPY . .
RUN pip3 install -r requirements.txt

CMD [ "python3", "server.py"]