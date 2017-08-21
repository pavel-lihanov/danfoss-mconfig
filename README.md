Drives configurator

## Running Locally

Make sure you have Python [installed properly](http://install.python-guide.org).  Also, install the [Heroku Toolbelt](https://toolbelt.heroku.com/) and [Postgres](https://devcenter.heroku.com/articles/heroku-postgresql#local-setup).

```sh
$ git clone ...

$ pip install -r requirements.txt

$ python manage.py migrate
$ python manage.py collectstatic
$ python manage.py runserver
