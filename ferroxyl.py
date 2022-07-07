#!/usr/bin/env python3

import errno
import glob
import json
import os
import re
import shlex
import shutil
import subprocess

AUDIT_DB_DIR = "/tmp/ferroxyl-audit-db"
PKG_PATH = "/var/db/repos/gentoo"

#if not os.path.exists(PKG_PATH):

#vartree = portage.db[portage.root]["vartree"]
#d = vartree.dbapi._aux_env_search("x11-terms/alacritty-0.8.0", "CRATES")

def find_ebuilds(pkg_path):
    ebuilds = []
    for dirpath, dirs, files in os.walk(pkg_path):
        for filename in files:
            if filename.endswith(".ebuild"):
                ebuilds.append(os.path.join(dirpath,filename))
    return ebuilds

def find_CRATED(ebuilds):
    print('\033[1m' + '\033[96m' + "***Looking for ebuilds with CRATES " + '\033[0m')
    crated = []
    for ebuild in ebuilds:
        with open(ebuild, 'r') as f:
            for line in f:
                if "CRATES=" in line:
                    crated.append(ebuild)
    return crated

def parse_crates(ebuilds):
    print('\033[1m' + '\033[96m' + "***Parsing CRATES " + '\033[0m')
    ebuild_crates = {}
    for ebuild in ebuilds:
        with open(ebuild, 'r') as f:
            try:
                lines = shlex.split(f.read())
            except ValueError:
                print(ebuild + ": failed to parse")

            for line in lines:
                var, eq, value = line.partition('=')
                if eq:
                    if var == "CRATES":
                        ename = ebuild[len(PKG_PATH) + 1:] if ebuild.startswith(PKG_PATH) else ebuild
                        ebuild_crates.update({ename: [ i for i in value.splitlines() if i]})
    #return json.dumps(ebuild_crates, indent = 4) 
    return ebuild_crates

def create_fake_locks(dict):
    print('\033[1m' + '\033[96m' + "***Creating fake locks " + '\033[0m')
    for k in dict:
        f = open("Cargo.lock-" + k.replace("/", "_"), 'w+')
        for dep in dict[k]:
            version_list = re.split('^([a-zA-Z0-9_\-]+)-([0-9]+\.[0-9]+\.[0-9]+.*)$', dep.strip())
            try:
                version =  version_list[2]
            except IndexError:
                version = "error"

            try:
                name = version_list[1]
            except IndexError:
                version = "error"

            f.write("[[package]]\n")
            f.write("name = \"" + name + "\"\n")
            f.write("version = \"" + version + "\"\n")


def scan_locks():
    # pre-fetch db
    print('\033[1m' + '\033[96m' + "***Fetching db to " + AUDIT_DB_DIR + '\033[0m')
    open("Cargo.lock", 'a').close()
    update_db = subprocess.call(["cargo", "audit", "--db", AUDIT_DB_DIR])
    for lock in glob.glob("Cargo.lock-*"):
        print('\033[1m' + '\033[96m' + "***Checking " + lock + '\033[0m')
        try:
            os.symlink(lock, "Cargo.lock")
        except OSError as e:
            if e.errno == errno.EEXIST:
                os.remove("Cargo.lock")
                os.symlink(lock, "Cargo.lock")
            else:
                raise e
        audit = subprocess.call(["cargo", "audit", "--no-fetch", "--db", AUDIT_DB_DIR]) 
        print("\n")


def cleanup():
    print('\033[1m' + '\033[96m' + "***Cleaning up" + '\033[0m')
    try:
        shutil.rmtree(AUDIT_DB_DIR)
    except OSError as e:
        print("Error: %s : %s" % (AUDIT_DB_DIR, e.strerror))

    for lock in glob.glob("Cargo.lock*"):
        try:
            os.remove(lock)
        except OSError as e:
            print("Error: %s : %s" % (lock, e.strerror))


all_ebuilds = find_ebuilds(PKG_PATH)
ebuilds_with_crates = find_CRATED(all_ebuilds)
crates = parse_crates(ebuilds_with_crates)
create_fake_locks(crates)
scan_locks()
cleanup()
#print(parse_crates(find_CRATED(find_ebuilds(PKG_PATH))))
                    
