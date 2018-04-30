#!/usr/bin/env python
"""
  Copy this file to settings.py and adjust as necessary
"""

#| Permit connections from 127.0.0.1 (ex. for ngrok)

ALLOW_LOCALHOST = True

#| Email Options

ENABLE_EMAIL = True
MAILGUN_ADDRESS = 'https://api.mailgun.net/v3/xxxxxxxx/messages'
MAILGUN_API_KEY = 'your-mailgun-key'
EMAIL_TO = ['you@example.com']
EMAIL_FROM = 'Server <server@example.com>'

#| Logging Options

ENABLE_STDOUT = True
ENABLE_LOGFILE = True

LOGFILE = '/var/log/gunicorn/git-deploy.log'
LOGLEVEL = 'DEBUG'

#| Repository Definitions

PROVIDERS = {}

#| Remove any providers you're not using and adjust 'repo_branch':

PROVIDERS['github'] = {
    'whitelist_ips': [
        '207.97.227.224/27', '173.203.140.192/27', '204.232.175.64/27',
        '72.4.117.96/27', '192.30.252.0/22', '204.232.175.64/27'
    ],
    'ssh_account':
        'git@github.com',
    'repo_branch': [
        {
            'remote_repo_user': 'cjsheets',
            'remote_repo_name': 'git-webhook-deploy',
            'remote_repo_branch': 'master',
            'remote_repo_action': 'push',
            'local_repo_dir': '/var/www/git-webhook-deploy/public'
        },
    ]
}

PROVIDERS['bitbucket'] = {
    'whitelist_ips':
        ['131.103.20.160/27', '165.254.145.0/26', '104.192.143.0/24'],
    'ssh_account':
        'git@bitbucket.org',
    'repo_branch': [
        {
            'remote_repo_user': 'cjsheets',
            'remote_repo_name': 'git-webhook-deploy',
            'remote_repo_branch': 'master',
            'remote_repo_action': 'push',
            'local_repo_dir': '/var/www/git-webhook-deploy/public'
        },
    ]
}

PROVIDERS['vsts'] = {
  'whitelist_ips' : ['207.97.227.224/27', '173.203.140.192/27',
				   '204.232.175.64/27', '72.4.117.96/27',
				   '192.30.252.0/22', '204.232.175.64/27'],
  'ssh_account' : '<account_name>@vs-ssh.visualstudio.com',
  'repo_branch'	 : [ {
    'remote_repo_user' : 'chad@sheets.ch',
    'remote_repo_name' : 'git-webhook-deploy',
    'remote_repo_branch' : 'master',
    'remote_repo_action' : 'push',
    'local_repo_dir' : '/var/www/git-webhook-deploy/public',
    'vsts_ssh_string' : 'ssh://<user-name>@vs-ssh.visualstudio.com:22/<project-name>/_ssh/'
  },
  ]
}
