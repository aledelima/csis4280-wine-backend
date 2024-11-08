# Flask MongoDB Application

This is a Flask-based application that connects to a MongoDB database. The app is designed to manage a warehouse of wines, using an API built with Flask/Python.

## Setup Instructions for Cloud9

1. **Clone the Repository**  
   Clone the repository to your Cloud9 environment:

   ```bash
   git clone <repository-url>
   cd <repository-name>

2. **Install the necessary libraries**

    ```python
    pip install Flask pymongo python-dotenv bson

3. **Mongodb User and Password**

    As those information are sensitive and should not be pushed to github, they are introduced as environment variables. Thus a ".env" file is necessary to be put into the root of the project.

    Content must be
    MONGO_URI="mongodb+srv://<db_username>:<db_password>@<url>/"

4. **Postman Colleciton**

    Notice that the Postman collection uses a variable namede based url. It was successfuly validated locally as base_url=http://localhost:8888/v1/api

    You can change it by editing the collection and then selecting the tab VARIABLES
