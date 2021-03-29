# Megalert

A Flask-based, API-centric system to send SMS using a Mikrotik with LTE capabilities

## Run

Requirements to run Megalert locally can be found in the requirements.txt file

To run the API system locally you should follow the following steps:
1. Clone this repository
2. Rename `.env.sample` to `.env` and fill in the settings
3. Install requirements using `pip install -r requirements.txt` (on linux/macos use `pip3` instead of `pip`)
4. Run the application using `python server.py` (on linux/macos use `python3` instead of `python`)

You can also run it under docker using the official docker image [megabitus/megalert](https://hub.docker.com/r/megabitus/megalert)

## Features

* send SMS
* get SMS inbox

## Disclaimer

_Megalert comes with ABSOLUTELY NO WARRANTY, to the extent permitted by applicable law._

## License

This project is distributed under the [MIT License](https://github.com/megabitus98/megalert/blob/main/LICENSE). 
