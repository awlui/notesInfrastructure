import os
import re

from fabric import task, Connection
from dotenv import load_dotenv

from copy import deepcopy
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
    new_web_service = { "image": f"{DOCKER_USERNAME}/{DOCKER_IMAGE}:{version}".strip(), "expose": [8000] }
    result2 = conn.run(f'''
        cd /home/app
        cat docker-compose.prod.yml
    ''')
    deserialized_yaml = load(result2.stdout, Loader=Loader)

    initial_compose = deepcopy(deserialized_yaml)

    initial_docker_services = initial_compose['services']
    new_color = None

    if (initial_docker_services.get('green')):
        # deploy blue
        print("ONE")
        new_color = 'blue'
        old_color = 'green'
    elif (initial_docker_services.get('blue')):
        # deploy green
        print("TWO")
        new_color = 'green'
        old_color = 'blue'
    else:
        # deploy blue
        print("THREE")
        new_color = 'blue'
        old_color = None

    initial_docker_services[new_color] = new_web_service

    # final_compose = deepcopy(initial_compose)
    
    # if old_color:
    #     del final_compose['services'][old_color]

    serialized_initial_yaml = dump(initial_compose, Dumper=Dumper)
    print("FOUR")
    result3 = conn.run(f'''
        cd /home/app
        echo "{serialized_initial_yaml}" > docker-compose.prod.yml
    ''')
    print("FIVE")
    result4 = conn.run(f'''
        cd /home/app
        docker-compose -f docker-compose.prod.yml up --build -d
    ''')
    print("SIX")
    if old_color:
        print(old_color, 'old')
        final_compose = deepcopy(initial_compose)
    
        del final_compose['services'][old_color]

        serialized_final_yaml = dump(final_compose, Dumper=Dumper)

        result5 = conn.run(f'''
            cd /home/app
            echo starting nginx
            docker-compose -f docker-compose.prod.yml exec -T nginx sed -ie 's/{old_color}/{new_color}/' /etc/nginx/conf.d/nginx.conf
            echo "{old_color}"
            echo "{new_color}"
            docker-compose -f docker-compose.prod.yml exec -T nginx nginx -s reload
            echo "{serialized_final_yaml}" > docker-compose.prod.yml
            docker-compose -f docker-compose.prod.yml up --build -d --remove-orphans

        ''')





    # print(a['services']['blue'], 'OI')
  #   image: awlui2019/docker_setup:latest
  #   expose:
  #     - 8000

@task
def test(c):
    blue = 'blue'
    green = 'green'
    conn.run(f'''
                cd /home/app
                docker-compose -f docker-compose.prod.yml exec -T nginx sed -ie 's/blue/green/' /etc/nginx/conf.d/nginx.conf
    ''')