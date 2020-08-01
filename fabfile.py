import os
import re

from fabric import task, Connection
from dotenv import load_dotenv

from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from constants import SEMVER_TYPES

load_dotenv()
DOCKER_USERNAME = os.environ.get("DOCKER_USERNAME")
DOCKER_IMAGE = os.environ.get("DOCKER_IMAGE")
WD = os.environ.get("NOTES_WORKING_DIRECTORY")
conn = Connection('138.68.227.38', user="root", connect_kwargs={ "allow_agent": False})

def runWithContext(connection, script, wd=WD):
    print(wd)
    return connection.run(f'''
        cd {wd}
        version=`cat ./VERSION`
        {script}
    ''')

def getUpdateType():
    semver_type = None
    while True:
        semver_type = input(f"Semver: [ {' | '.join(SEMVER_TYPES)} ]: ")
        print()
        if semver_type.lower() in SEMVER_TYPES:                
            return semver_type

def getManualSemver():
    p = re.compile('\d+.\d+.\d+')
    while True:
        version = input(f"Manually input the next version (ex. 3.1.2): ")
        print()
        if (p.match(version)):
            return version
        else:
            print(f"Wrong format, try again.")


def updateVersion(c):
    semver_type = getUpdateType()
    print(semver_type)
    if 'manual' == semver_type:
        manualVersion = getManualSemver()
        result = runWithContext(c,
          f'''
            echo {manualVersion} > VERSION
          '''
        )
    else:
        result = runWithContext(c,
        f'''
            docker run --rm -v "$PWD":/app treeder/bump {semver_type}
        ''')
    
@task
def deploy(c):
    result = conn.run('ls', warn=True)

@task
def deployApp(c):
    '''Currently set to deploy the latest'''
    semver_type = updateVersion(c)

    buildImage(c)

    pushImage(c)

    deployImage(c)

@task
def buildImage(c):
    runWithContext(c, f'''
        docker build -t {DOCKER_USERNAME}/{DOCKER_IMAGE}:$version .
    ''')

@task
def pushImage(c):
    runWithContext(c, f'''
        docker login -u awlui2019 --password-stin aLways2020
        docker image push {DOCKER_USERNAME}/{DOCKER_IMAGE}:$version
    ''')

@task
def deployImage(c):
    print("DEPLOY IMAGE RUNNING")
    result = runWithContext(c, f'''
        echo $version
    ''')

    version = result.stdout
    
    result2 = conn.run(f'''
        cd /home/app
        cat docker-compose.prod.yml
    ''')

    load(result2.stdout, Loader=Loader)
