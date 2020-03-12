#!/usr/bin/env python

from github import Github		# https://github.com/PyGithub/PyGithub
import requests
import json
import sys
import os

# repo_map = { "some-github-repo":		"a-gitea-org",
#              "another-github-repo":		"another-gitea-org",
#            }
repo_map = {}

TOKEN_FOLDER = os.environ.get("TOKEN_FOLDER, ")

gitea_url = os.environ.get("GITEA_API", "https://git.sinpapel.es/api/v1")
gitea_user = os.environ.get("GITEA_USER", "balkian")
gitea_token = os.environ.get("GITEA_TOKEN") or open(os.path.expanduser("~/.gitea-token")).read().strip()

print(gitea_user, gitea_token, gitea_url)

session = requests.Session()        # Gitea
session.headers.update({
    "Content-type"  : "application/json",
    "Authorization" : "token {0}".format(gitea_token),
})

users_and_orgs = [gitea_user]

github_username = os.environ.get("GITHUB_USER", "balkian")
github_token = os.environ.get("GITHUB_TOKEN") or open(os.path.expanduser(".github-token")).read().strip()
gh = Github(github_token)

for repo in gh.get_user().get_repos():
    # Mirror to Gitea if I haven't forked this repository from elsewhere
    if not repo.fork:
        user_or_org, real_repo = repo.full_name.split('/')[:2]
        if real_repo in repo_map:
            # We're creating the repo in another account (most likely an organization)
            gitea_dest_user = repo_map[real_repo]
        elif user_or_org in users_and_orgs:
            gitea_dest_user = gitea_user
        else:
            print('Not cloning', repo.full_name)

            r = session.get("{0}/repos/{1}/{2}".format(gitea_url, gitea_user, real_repo))
            if r.status_code == 200:
                resp = input('repo exists. Remove? [y/N]')
                if resp.lower() in ['y', 'yes']:
                    r = session.delete("{0}/repos/{1}/{2}".format(gitea_url, gitea_user, real_repo))
                    if r.status_code not in [200, 204]:
                        print('Error', r.status_code, r.text)
            continue

        r = session.get("{0}/users/{1}".format(gitea_url, gitea_dest_user))
        if r.status_code != 200:
            print("Cannot get user id for '{0}'".format(gitea_dest_user), file=sys.stderr)
            exit(1)

        gitea_uid = json.loads(r.text)["id"]

        m = {
            "repo_name"         : "{0}".format(real_repo),
            "description"       : repo.description or "not really known",
            "clone_addr"        : repo.clone_url,
            "mirror"            : True,
            "private"           : repo.private,
            "uid"               : gitea_uid,
        }

        if repo.private:
            m["auth_username"]  = github_username
            m["auth_password"]  = "{0}".format(github_token)

        jsonstring = json.dumps(m)

        r = session.post("{0}/repos/migrate".format(gitea_url), data=jsonstring)
        if r.status_code != 201:            # if not CREATED
            if r.status_code == 409:        # repository exists
                print('{0} already exists'.format(real_repo))
                continue
            print(r.status_code, r.text, jsonstring)
            print(m)
