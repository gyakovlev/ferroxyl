#!/usr/bin/env python3

import errno
import glob
import json
import os
import re
import shlex
import subprocess

PKG_PATH = "/var/db/pkg"

#if not os.path.exists(PKG_PATH):

def find_ebuilds(pkg_path):
    ebuilds = []
    for dirpath, dirs, files in os.walk(pkg_path):
        for filename in files:
            if filename.endswith(".ebuild"):
                ebuilds.append(os.path.join(dirpath,filename))
    return ebuilds

def find_CRATED(ebuilds):
    crated = []
    for ebuild in ebuilds:
        with open(ebuild, 'r') as f:
            for line in f:
                if "CRATES=" in line:
                    crated.append(ebuild)
    return crated

def parse_crates(ebuilds):
    ebuild_crates = {}
    for ebuild in ebuilds:
        with open(ebuild, 'r') as f:
            for line in shlex.split(f.read()):
                var, eq, value = line.partition('=')
                if eq:
                    if var == "CRATES":
                        ename = ebuild[len(PKG_PATH) + 1:] if ebuild.startswith(PKG_PATH) else ebuild
                        ebuild_crates.update({ename: [ i for i in value.splitlines() if i]})
    #return json.dumps(ebuild_crates, indent = 4) 
    return ebuild_crates

def create_fake_locks(dict):
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
        audit = subprocess.call(["cargo", "audit"]) 
        print("\n")
        
all_ebuilds = find_ebuilds(PKG_PATH)
ebuilds_with_crates = find_CRATED(all_ebuilds)
crates = parse_crates(ebuilds_with_crates)
create_fake_locks(crates)
scan_locks()
#print(parse_crates(find_CRATED(find_ebuilds(PKG_PATH))))
                    
