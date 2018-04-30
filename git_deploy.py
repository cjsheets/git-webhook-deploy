#!/usr/bin/env python
"""
  Git Deploy
    - Handles webhooks from GitHub and Bitbucket
    - Executes pull requests defined in settings.py
"""

import json
import logging
import os
import subprocess

import ipaddr
import requests
from flask import Flask, request

import settings

APP = Flask(__name__)

if settings.ALLOW_LOCALHOST:
  for allowed_providers in settings.PROVIDERS:
    settings.PROVIDERS[allowed_providers]['whitelist_ips'].append('127.0.0.1')


def log_level(level):
  """ Setup the root logger for the script """
  return {
      'DEBUG': logging.DEBUG,
      'INFO': logging.INFO,
      'WARNING': logging.WARNING,
      'ERROR': logging.ERROR,
      'CRITICAL': logging.CRITICAL,
  }.get(level, logging.INFO)


LOGGING_FORMATTER = logging.Formatter(
    '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
STREAM_HANDLER = logging.StreamHandler()
STREAM_HANDLER.setFormatter(LOGGING_FORMATTER)
FILE_HANDLER = logging.FileHandler(settings.LOGFILE)
FILE_HANDLER.setFormatter(LOGGING_FORMATTER)

LOGGER = logging.getLogger(__name__)

if settings.ENABLE_STDOUT:
  APP.logger.addHandler(STREAM_HANDLER)

if settings.ENABLE_LOGFILE:
  APP.logger.addHandler(FILE_HANDLER)

APP.logger.setLevel(log_level(settings.LOGLEVEL))


def send_email(git_pull_params, git_pull_results):
  """ Compose and send an email notification """
  LOGGER.debug('git pull completed, sending email notification')
  msg = "A " + git_pull_params['provider'] + \
  " webhook triggered a pull request into the following directory: \n\n" + \
    git_pull_params[
        'repo_dir'] + "\n\n Resulting in the following output: \n\n" + git_pull_results
  subject = subprocess.check_output(
      'hostname', shell=True) + " - git pull - " + git_pull_params['repo_name']
  return requests.post(
      settings.MAILGUN_ADDRESS,
      auth=("api", settings.MAILGUN_API_KEY),
      data={
          "from": settings.EMAIL_FROM,
          "to": settings.EMAIL_TO,
          "subject": subject,
          "text": msg
      })


def git_pull(git_pull_params):
  """ After parsing webhook, perform pull on repository """
  assert 'ssh_account' in git_pull_params
  assert 'repo_user' in git_pull_params
  assert 'repo_name' in git_pull_params
  assert 'repo_branch' in git_pull_params
  assert 'repo_dir' in git_pull_params

  dest_directory = git_pull_params['repo_dir']
  repo_name = git_pull_params['repo_name']
  branch_name = git_pull_params['repo_branch']

  if git_pull_params['provider'] == 'VSTS':
    repo_url = git_pull_params['vsts_ssh_string'] + git_pull_params['repo_name']
  else:
    repo_url = git_pull_params['ssh_account'] + ':' + git_pull_params['repo_user'] + \
        '/' + git_pull_params['repo_name'] + '.git'

  LOGGER.debug('Ensuring destination directory exists: %s', dest_directory)
  subprocess.call('mkdir -p ' + dest_directory, shell=True)

  LOGGER.debug("Checking for repository %s in %s", repo_name, dest_directory)
  if not os.path.exists(dest_directory + '/.git'):
    LOGGER.info("Initializing repository: %s", repo_url)
    subprocess.call('git init', cwd=dest_directory, shell=True)
    subprocess.call(
        'git remote add -f origin ' + repo_url, cwd=dest_directory, shell=True)

  try:
    subprocess.call(
        'git show-ref --heads ' + branch_name, cwd=dest_directory, shell=True)
  except StandardError:
    LOGGER.info("Checking out branch: %s", branch_name)
    subprocess.call(
        'git checkout -b ' + branch_name + ' origin/' + branch_name,
        cwd=dest_directory,
        shell=True)

  LOGGER.debug("Performing git pull on: %s", branch_name)
  git_pull_results = subprocess.check_output(
      'git pull origin ' + branch_name, cwd=dest_directory, shell=True)

  if settings.ENABLE_EMAIL:
    send_email(git_pull_params, git_pull_results)


def parse_github_data(data):
  """ Payload Description, See:
  https://help.github.com/articles/post-receive-hooks
  """
  assert 'sender' in data
  assert 'repository' in data
  assert 'owner' in data['repository']

  git_pull_params = {}
  for repo in settings.PROVIDERS['github']['repo_branch']:
    if (repo['remote_repo_user'] == data['sender']['login'] or
        repo['remote_repo_user'] == data['organization']['login']) and \
            repo['remote_repo_name'] == data['repository']['name'] and \
            'refs/heads/' + repo['remote_repo_branch'] == data['ref']:
      # correct default_branch, check correct branch
      LOGGER.debug("GitHub webhook matched to settings")

      git_pull_params = {
          'provider': 'GitHub',
          'ssh_account': settings.PROVIDERS['github']['ssh_account'],
          'repo_user': repo['remote_repo_user'],
          'repo_name': repo['remote_repo_name'],
          'repo_branch': repo['remote_repo_branch'],
          'repo_dir': repo['local_repo_dir']
      }
      return git_pull_params

  LOGGER.debug('Unable to match data with repo in settings.py')

  return []


def parse_bitbucket_data(data):
  """ Payload Description, See:
  https://confluence.atlassian.com/bitbucket/event-payloads-740262817.html#EventPayloads-Push
  """
  changes = data['push']['changes']
  assert 'repository' in changes[0]['new']
  assert 'name' in changes[0]['new']
  assert 'type' in changes[0]['new']
  assert 'target' in changes[0]['new']

  git_pull_params = {}

  for change in changes:
    if change['new']['type'] != 'branch' or not change['new']['name']:
      LOGGER.debug('Pull was not for a branch or branch name was null')
      continue

    # logger.debug(settings.PROVIDERS['bitbucket']['repo_branch'])
    for repo in settings.PROVIDERS['bitbucket']['repo_branch']:
      # also check remote_repo_user
      if repo['remote_repo_name'] == change['new']['repository']['name'] and \
              repo['remote_repo_branch'] == change['new']['name'] and \
              repo['remote_repo_action'] == change['new']['target']['type']:
        LOGGER.debug("Bitbucket webhook matched to settings")
        git_pull_params = {
            'provider': 'Bitbucket',
            'ssh_account': settings.PROVIDERS['bitbucket']['ssh_account'],
            'repo_user': repo['remote_repo_user'],
            'repo_name': repo['remote_repo_name'],
            'repo_branch': repo['remote_repo_branch'],
            'repo_dir': repo['local_repo_dir']
        }
        return git_pull_params

  LOGGER.debug('Unable to match data with repo in settings.py')
  return []


def parse_vsts_data(data):
  assert 'resource' in data
  assert 'publisherId' in data
  assert 'pushedBy' in data['resource']
  assert 'uniqueName' in data['resource']['pushedBy']

  git_pull_params = {}
  for repo in settings.PROVIDERS['vsts']['repo_branch']:
    if (repo['remote_repo_user'] == data['resource']['pushedBy']['uniqueName']) and \
            repo['remote_repo_name'] == data['resource']['repository']['name'] and \
            'refs/heads/' + repo['remote_repo_branch'] == data['resource']['refUpdates'][0]['name']:
      # correct default_branch, check correct branch
      LOGGER.debug("VSTS webhook matched to settings")

      git_pull_params = {
          'provider': 'VSTS',
          'ssh_account': settings.PROVIDERS['vsts']['ssh_account'],
          'repo_user': repo['remote_repo_user'],
          'repo_name': repo['remote_repo_name'],
          'repo_branch': repo['remote_repo_branch'],
          'repo_dir': repo['local_repo_dir'],
          'vsts_ssh_string': repo['vsts_ssh_string']
      }
      return git_pull_params

  LOGGER.debug('Unable to match data with repo in settings.py')

  return []


def parse_data(data):
  """ Extract important fields from webhook """
  LOGGER.info('parsing data')
  LOGGER.info('resourceContainers' in data)
  if 'resourceContainers' in data and 'resource' in data:
    LOGGER.info("Message originated from VSTS, parsing data")
    git_pull_params = parse_vsts_data(data)

  elif 'commits' not in data and 'commits_url' not in data['repository']:
    LOGGER.info("POST request didn't contain a commit, is not actionable")
    return []

  elif 'head_commit' in data and 'pusher' in data and 'repository' in data \
          and 'sender' in data:
    LOGGER.info("Message originated from GitHub, parsing data")
    git_pull_params = parse_github_data(data)
  elif 'actor' in data and 'repository' in data and 'push' in data:
    LOGGER.info("Message originated from Bitbucket, parsing data")
    git_pull_params = parse_bitbucket_data(data)
  else:
    LOGGER.info("Unable to determine message origin. no action taken")
    return []

  LOGGER.debug("Parameters extracted: %s", git_pull_params)
  if git_pull_params:
    git_pull(git_pull_params)
  else:
    LOGGER.info("Unable to extract message data. no action taken")


def check_request_source(remote_addr):
  """ Perform whitelist IP address validation """
  for provider in settings.PROVIDERS:
    whitelist = settings.PROVIDERS[provider].get('whitelist_ips', [])

    for allowed_addr in whitelist:
      if remote_addr in ipaddr.IPNetwork(allowed_addr):
        return True
  return False


@APP.route("/", methods=['POST'])
def index():
  """ Entry point for execution """
  if request.method == 'POST':
    valid_ip = check_request_source(ipaddr.IPAddress(request.remote_addr))
    if not valid_ip:
      LOGGER.error("Received POST request from invalid IP: %s",
                   request.remote_addr)
      return "ERROR"

    LOGGER.info("Received POST request, IP address validated, processing...")
    if request.json:
      LOGGER.debug("JSON MIME type detected")
      parse_data(request.json)
    elif 'payload' in request.form:
      LOGGER.debug("Decoding payload: %s", request.form['payload'])
      # BitBucket includes newlines in the message data; disable
      # strict checking
      json_data = json.loads(request.form['payload'], strict=False)
      parse_data(json_data)
    else:
      LOGGER.info("Request was not recognized. no action taken")

    return "OK"
  return "OK"


if __name__ == "__main__":
  APP.run()
