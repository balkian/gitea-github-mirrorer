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


def env_list(name):
    return list(filter(None, os.environ.get(name, "").split(",")))

# The following users and orgs will be mirrored
users_and_orgs = env_list("GITHUB_USERS_ORGS") + [gitea_user]
# And this list of projects as well
repo_list = env_list("GITHUB_REPO_LIST")

print(f"Cloning to {gitea_url}. Default user: {gitea_user}")
print(f'\tUsers and orgs: {" ".join(users_and_orgs)}')

if repo_list:
    print(f'\tHandpicked repos: {" ".join(repo_list)} ({len(repo_list)})')
    print(f'"{repo_list[0]}"')

session = requests.Session()        # Gitea
session.headers.update({
    "Content-type"  : "application/json",
    "Authorization" : "token {0}".format(gitea_token),
})

# Ask to remove repositories that "should not be mirrored" but are
prune = False

github_username = os.environ.get("GITHUB_USER", "balkian")
github_token = os.environ.get("GITHUB_TOKEN") or open(os.path.expanduser(".github-token")).read().strip()
gh = Github(github_token)

uids = {}

def get_uid(user):
    if user in uids:
        return uids[user]

    r = session.get(f"{gitea_url}/users/{gitea_dest_user}")
    if r.status_code != 200:
        msg = f"Cannot get user id for '{gitea_dest_user}'"
        print(msg, file=sys.stderr)
        raise Exception(msg)
    uid = json.loads(r.text)["id"]
    uids[user] = uid
    return uid


for repo in gh.get_user().get_repos():
    # Mirror to Gitea if I haven't forked this repository from elsewhere
    if not repo.fork:
        user_or_org, repo_name = repo.full_name.split('/')[:2]
        # By default, mirror to the default user
        gitea_dest_user = gitea_user
        if repo_name in repo_map:
            # We're creating the repo in another account (most likely an organization)
            gitea_dest_user = repo_map[repo_name]
        elif user_or_org in users_and_orgs or repo_name in repo_list or f"{user_or_org}/{repo_name}" in repo_list:
            pass
        else:
            print(f'... Skipping {repo.full_name}')

            r = session.get(f"{gitea_url}/repos/{gitea_user}/{repo_name}")
            if r.status_code == 200:
                print(f'*** repo exists: {gitea_user}/{repo_name}')
                if not prune:
                    continue
                resp = input('\tRemove? [y/N]')
                if resp.lower() in ['y', 'yes']:
                    r = session.delete(f"{gitea_url}/repos/{gitea_user}/{repo_name}")
                    if r.status_code not in [200, 204]:
                        print('Error', r.status_code, r.text)
            continue

        m = {
            "repo_name"         : repo_name,
            "description"       : repo.description or "not really known",
            "clone_addr"        : repo.clone_url,
            "mirror"            : True,
            "private"           : repo.private,
            "uid"               : get_uid(gitea_dest_user),
        }

        if repo.private:
            m["auth_username"]  = github_username
            m["auth_password"]  = f"{github_token}"

        jsonstring = json.dumps(m)

        r = session.post(f"{gitea_url}/repos/migrate", data=jsonstring)
        if r.status_code == 201:            # if CREATED
            print(f'\u2713 project created: {repo_name}')
        elif r.status_code == 409:        # repository exists
            print(f'... already exists {repo_name}')
        else:
            print(r.status_code, r.text, jsonstring)
            print(m)
