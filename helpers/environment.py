# global dependencies
from os                     import getenv
from os.path                import join, dirname
from dotenv                 import load_dotenv

# loads environment variables from .env file
dotenv_path = join(dirname(dirname(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

# mikrotik configuration
HOST = str(getenv("HOST"))
USERNAME = str(getenv("USERNAME"))
PASSWORD = str(getenv("PASSWORD"))
PORT = int(getenv("PORT"))

# authentification secret
SECRET = str(getenv("SECRET"))