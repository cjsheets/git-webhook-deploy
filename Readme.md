Git Deploy
==========

Parse webhooks from [GitHub](https://github.com/), [Bitbucket](https://bitbucket.org/) or [VSTS](https://www.visualstudio.com/team-services/) and perform pull requests on a local repository.

Build your own CI workflow:
* Server receives an HTTP webhook and calls `git_deploy.py`
  * (Flask/Gunicorn is a great light-weight option but anything that can forward requests to a python script works)
* Request is validated against `settings.py`
* Local repository performs a git pull
* Email notifications is sent

How to Use
----------

**settings.py**

First, you need to copy `settings_example.py` to `settings.py`:

* Set `ENABLE_EMAIL = False` or set each MAILGUN property.
* Set `ENABLE_LOGFILE = False` or ensure the user that launches git_deploy has write permission to `LOGFILE`.
* Setup `PROVIDERS`:
  * Remove any providers you're not using
  * Each object in the `repo_branch` array represents a repository to deploy

**Customizing**

Depending on your provider, the JSON provided in the HTTP request may vary from what `git_deploy.py` expects. This script is fairly short to make it easier to customize. Try the Development instructions below for customization.

If you have any trouble, I recommend capturing the JSON using a tool like ngrok and ensuring the hard-coded values (ex. `data['repository']['name']`) match those in your request.

I included sample payloads in the `/doc/` folder, however I imagine those are susceptible to change.

Development
-----------

After cloning the repository, setup a dev environment.

```
virtualenv .env
source .env/bin/activate
pip install -r doc/requirements.txt
```

Next, prepare `settings.py` as described above. Change `LOGLEVEL = 'DEBUG'`

Start a flask-listener to receive webhooks:

```
.env/bin/gunicorn git_deploy:APP -b 127.0.0.1:9090
```

I like to use [ngrok](https://ngrok.com/download) to expose our newly created server to the world.

```
./ngrok http 9090
```

Finally, trigger a POST message from your git provider of choice.

Watch the Flask console for messages about the request. If you're using ngrok, you can visit its web interface and replay the webhook until you get the desired result.

Happy Deploying!

### To-Do:

* Add support for git secret
* Add support for multiple repos from the same listener

### License

MIT License

[![Analytics](https://cjs-beacon.appspot.com/UA-10006093-3/github/cjsheets/git-webhook-deploy?pixel)](https://github.com/cjsheets/git-webhook-deploy)
