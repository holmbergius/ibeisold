#!/usr/bin/env python2.7
from __future__ import absolute_import, division, print_function
from os.path import dirname, realpath
import platform
import sys
import os
"""
PREREQ:
git config --global push.default current
export CODE_DIR=~/code
mkdir $CODE_DIR
cd $CODE_DIR
git clone https://github.com/Erotemic/ibeis.git
cd ibeis
./_scripts/bootstrap.py
./_scripts/__install_prereqs__.sh
./super_setup.py --build --develop
./super_setup.py --build --develop
"""

print('[super_setup] __IBEIS_SUPER_SETUP__')
CODE_DIR = dirname(dirname(realpath(__file__)))   # '~/code'
print('[super_setup] code_dir: %r' % CODE_DIR)

(DISTRO, DISTRO_VERSION, DISTRO_TAG) = platform.dist()
python_version = platform.python_version()
assert python_version.startswith('2.7'), \
    'IBEIS currently needs python 2.7,  Instead got python=%r' % python_version


#pythoncmd = 'python'
#if DISTRO == 'centos':
pythoncmd = 'python' if sys.platform.startswith('win32') else 'python2.7'


def userid_prompt():
    # TODO: Make this prompt for the userid
    if False:
        return {'userid': 'Erotemic', 'permitted_repos': ['pyrf', 'detecttools']}
    return {}

#################
## ENSURING UTOOL
#################


def syscmd(cmdstr):
    print('RUN> ' + cmdstr)
    os.system(cmdstr)

try:
    # HACK IN A WAY TO ENSURE UTOOL
    print('Checking utool')
    import utool
    utool.set_userid(**userid_prompt())  # FIXME
except Exception:
    print('FATAL ERROR: UTOOL IS NEEDED FOR SUPER_SETUP. Attempting to get utool')
    os.chdir(os.path.expanduser(CODE_DIR))
    print('cloning utool')
    if not os.path.exists('utool'):
        syscmd('git clone https://github.com/Erotemic/utool.git')
    os.chdir('utool')
    print('pulling utool')
    syscmd('git pull')
    print('installing utool for development')
    syscmd('sudo {pythoncmd} setup.py develop'.format(**locals()))
    cwdpath = os.path.realpath(os.getcwd())
    sys.path.append(cwdpath)
    print('Please rerun super_setup.py')
    sys.exit(1)

utool.init_catch_ctrl_c()

#-----------
# Third-Party-Libraries
#-----------

print('[super_setup] Checking third-party-libraries')

TPL_MODULES_AND_REPOS = [
    ('cv2',     'https://github.com/Erotemic/opencv.git'),
    ('pyflann', 'https://github.com/Erotemic/flann.git'),
    #('yael',    'https://github.com/Erotemic/yael.git'),
    (('PyQt5', 'PyQt4'),   None)
]

TPL_REPO_URLS = []
# Test to see if opencv and pyflann have been built
for nametup, repo_url in TPL_MODULES_AND_REPOS:
    try:
        # Allow for multiple module aliases
        if isinstance(nametup, str):
            nametup = [nametup]
        module = None
        for name_ in nametup:
            try:
                module = __import__(name_, globals(), locals(), fromlist=[], level=0)
            except ImportError as ex:
                pass
        if module is None:
            raise ex
        print('found %s=%r' % (nametup, module,))
    except ImportError:
        assert repo_url is not None, ('FATAL ERROR: Need to manually install %s' % nametup)
        print('!!! NEED TO BUILD %s=%r' % (nametup, repo_url,))
        TPL_REPO_URLS.append(repo_url)


(TPL_REPO_URLS, TPL_REPO_DIRS) = utool.repo_list(TPL_REPO_URLS, CODE_DIR)

#-----------
# IBEIS project repos
#-----------

# Non local project repos
(IBEIS_REPO_URLS, IBEIS_REPO_DIRS) = utool.repo_list([
    'https://github.com/Erotemic/utool.git',
    'https://github.com/Erotemic/guitool.git',
    'https://github.com/Erotemic/plottool.git',
    'https://github.com/Erotemic/vtool.git',
    'https://github.com/bluemellophone/detecttools.git',
    'https://github.com/Erotemic/hesaff.git',
    'https://github.com/bluemellophone/pyrf.git',
    'https://github.com/Erotemic/ibeis.git',
    'https://github.com/aweinstock314/cyth.git',
    #'https://github.com/hjweide/pygist',
], CODE_DIR, forcessh=False)


PROJECT_REPO_URLS = IBEIS_REPO_URLS + TPL_REPO_URLS
PROJECT_REPO_DIRS = IBEIS_REPO_DIRS + TPL_REPO_DIRS

# Set utool global git repos
utool.set_project_repos(PROJECT_REPO_URLS, PROJECT_REPO_DIRS)


# Commands on global git repos
if utool.get_argflag('--status'):
    utool.gg_command('git status')
    utool.sys.exit(0)

if utool.get_argflag('--branch'):
    utool.gg_command('git branch')
    utool.sys.exit(0)

utool.gg_command('ensure')

if utool.get_argflag('--pull'):
    utool.gg_command('git pull')


if utool.get_argflag('--tag-status'):
    utool.gg_command('git tag')

# Tag everything
tag_name = utool.get_argval('--newtag', type_=str, default=None)
if tag_name is not None:
    utool.gg_command('git tag -a "{tag_name}" -m "super_setup autotag {tag_name}"'.format(**locals()))
    utool.gg_command('git push --tags')

if utool.get_argflag('--bext'):
    utool.gg_command('{pythoncmd} setup.py build_ext --inplace'.format(**locals()))

if utool.get_argflag('--build'):
    # Build tpl repos
    for repo in TPL_REPO_DIRS:
        utool.util_git.std_build_command(repo)  # Executes {plat}_build.{ext}
    # Build only IBEIS repos with setup.py
    utool.set_project_repos(IBEIS_REPO_URLS, IBEIS_REPO_DIRS)
    utool.gg_command('sudo {pythoncmd} setup.py build'.format(**locals()))

if utool.get_argflag('--develop'):
    utool.set_project_repos(IBEIS_REPO_URLS, IBEIS_REPO_DIRS)
    utool.gg_command('sudo {pythoncmd} setup.py develop'.format(**locals()))

if utool.get_argflag('--install'):
    utool.set_project_repos(IBEIS_REPO_URLS, IBEIS_REPO_DIRS)
    utool.gg_command('python setup.py install'.format(**locals()))

if utool.get_argflag('--test'):
    import ibeis
    print('found ibeis=%r' % (ibeis,))

if utool.get_argflag('--push'):
    utool.gg_command('git push')


commit_msg = utool.get_argval('--commit', type_=str, default=None)
if commit_msg is not None:
    utool.gg_command('git commit -am "{commit_msg}"'.format(**locals()))

if utool.get_argflag('--clean'):
    utool.gg_command('{pythoncmd} setup.py clean'.format(**locals()))

# Change Branch
branch_name = utool.get_argval('--checkout', type_=str, default=None)
if branch_name is not None:
    utool.gg_command('git checkout "{branch_name}"'.format(**locals()))

# Creates new branches
newbranch_name = utool.get_argval('--newbranch', type_=str, default=None)
if newbranch_name is not None:
    utool.gg_command('git stash"'.format(**locals()))
    utool.gg_command('git checkout -b "{newbranch_name}"'.format(**locals()))
    utool.gg_command('git stash pop"'.format(**locals()))

# Creates new branches
mergebranch_name = utool.get_argval('--merge', type_=str, default=None)
if mergebranch_name is not None:
    utool.gg_command('git merge "{mergebranch_name}"'.format(**locals()))

newbranch_name2 = utool.get_argval('--newbranch2', type_=str, default=None)
if newbranch_name2 is not None:
    utool.gg_command('git checkout -b "{newbranch_name2}"'.format(**locals()))
    utool.gg_command('git push --set-upstream origin {newbranch_name2}'.format(**locals()))

if utool.get_argflag('--serverchmod'):
    utool.gg_command('chmod -R 755 *')

if utool.get_argflag('--chown'):
    username = os.environ['USERNAME']
    usergroup = username
    utool.gg_command('sudo chown -R {username}:{usergroup} *'.format(**locals()))

upstream_branch = utool.get_argval('--set-upstream', type_=str, default=None)
if upstream_branch is not None:
    # git 2.0
    utool.gg_command('git branch --set-upstream-to=origin/{upstream_branch} {upstream_branch}'.format(**locals()))


upstream_push = utool.get_argval('--upstream-push', type_=str, default=None)
if upstream_push is not None:
    utool.gg_command('git push --set-upstream origin {upstream_push}'.format(**locals()))


gg_cmd = utool.get_argval('--gg', None)  # global command
if gg_cmd is not None:
    ans = raw_input('Are you sure you want to run: %r on all directories? ' % (gg_cmd,))
    if ans == 'yes':
        utool.gg_command(gg_cmd)
