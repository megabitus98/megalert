# Megalert

A Flask-based, API-centric system to send SMS using a Mikrotik device with LTE capabilities.

## Run

To run Megalert, we recommend you follow these steps:
1. Clone this repository;
2. Rename `.env.sample` to `.env` and fill in the settings;
3. Install the required dependencies using `pip3 install -r requirements.txt`;
4. Run the application using `python server.py` on Windows or `python3 server.py` on Unix-like operating systems.

You can also run it as a Docker container using our official [Docker image](https://hub.docker.com/r/megabitus/megalert).

The `docker run` command should look like this:

```
docker run -d -p 5000:5000 -e MIKROTIK_HOST='192.168.0.1' -e MIKROTIK_USER='admin' -e MIKROTIK_PASS='password' -e MIKROTIK_PORT=8728 -e AUTH_SECRET='secret' megabitus/megalert
```

### Environment variables

Variable        | Function
--------------- | --------
MEGALERT_HOST   | IP address of Megalert API (_default_: **0.0.0.0**)
MEGALERT_PORT   | port of Megalert API (_default_: **5000**)
MEGALERT_DEBUG  | debug logging for Megalert API (_default_: **True**) 
MIKROTIK_HOST   | IP address of Mikrotik device
MIKROTIK_USER   | username of Mikrotik device user account
MIKROTIK_PASS   | password of Mikrotik device user account
MIKROTIK_PORT   | port of Mikrotik API (_default_: **8728**)
AUTH_SECRET     | authentication secret for Mikrotik API

## Endpoints

You can find details about the Megalert API's endpoints, request and response bodies etc. on this repository's [wiki](https://github.com/megabitus98/megalert/wiki).

## Features

* Send SMS messages
* Retrieve the SMS inbox
* Retrieve SMS messages by phone number

## Disclaimer

_Megalert comes with ABSOLUTELY NO WARRANTY, to the extent permitted by applicable law._

## License

This project is distributed under the [MIT License](https://github.com/megabitus98/megalert/blob/main/LICENSE). 
