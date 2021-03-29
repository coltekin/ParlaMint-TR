#!/usr/bin/env python3
""" Data structure / utilities for data on parliament members.
"""
##TODO: party changes are not handled
##TODO: get/scrape data from TBMM web site

from logging import debug, info, warning, basicConfig
basicConfig(level="INFO", format='%(asctime)s %(message)s')

import os
import argparse
import json
import csv
from lxml import etree as et

#term -> (start, end, seats)
tbmmterms = {
    17: ('1983-11-24', '1987-10-16', 400),
    18: ('1987-12-14', '1991-09-01', 450),
    19: ('1991-11-14', '1995-12-04', 450),
    20: ('1996-01-08', '1999-04-25', 550),
    21: ('1999-05-02', '2002-10-01', 550),
    22: ('2002-11-14', '2007-06-03', 550),
    23: ('2007-07-23', '2011-04-23', 550),
    24: ('2011-06-28', '2015-04-23', 550),
    25: ('2015-06-23', '2015-10-01', 550),
    26: ('2015-11-17', '2018-05-16', 550),
    27: ('2018-07-07', None,         600)
}

class PMData:
    def __init__(self, source='pm.csv', typos='typos.tsv'):
        self.pmdata = dict()
        self.pmnames = dict()
        self.read_tsv('pm.tsv', typos=typos)

    def __contains__(self, item):
        return item in self.pmdata

    def __iter__(self):
        for pmid in self.pmdata:
            yield pmid

    def get(self, pmid, default=None):
        return self.pmdata.get(pmid, default)

    def read_tsv(self, filename, typos=None):
        with open(filename, 'rt') as f:
            csvr = csv.DictReader(f, delimiter='\t')
            for row in csvr:
                fn, ln = row['name'], row['surname']
                pmid = row['id']
                if (ln, fn) not in self.pmnames:
                    self.pmnames[(ln, fn)] = set([pmid])
                else:
                    self.pmnames[(ln, fn)].add(pmid)
                if pmid not in self.pmdata:
                    self.pmdata[pmid] = {
                        'id': pmid,
                        'fname': fn,
                        'lname': ln,
                        'sex': row['sex'],
                        'term': [int(row['term'])],
                        'region': [row['region']],
                        'party': [row['party']],
                    }
                else:
                    pm = self.pmdata[pmid]
                    if (fn, ln) != (pm['fname'], pm['lname']):
                        info("Adding alternative name {}, {} for {}"
                                .format(ln, fn, pmid))
                    if int(row['term']) not in pm['term']:
                        pm['term'].append(int(row['term']))
                        pm['region'].append(row['region'])
                        pm['party'].append(row['party'])
        if typos:
            with open(typos, 'rt') as fp:
                for line in fp:
                    fn, ln, spkid = line.strip().split('\t')
                    info("Adding alternative name {}, {} for {}"
                            .format(ln, fn, spkid))
                    if (ln, fn) not in self.pmnames:
                        self.pmnames[(ln, fn)] = set([spkid])
                    else:
                        self.pmnames[(ln, fn)].add(spkid)

    def get_pmid(self, name=None, lastname=None, firstname=None,
            region=None, term=None, party=None, guess=True):
        pmids = set()
        if lastname and firstname:
            names = firstname.split() + lastname.split()
            namekeys = [(lastname, firstname)]
        elif name:
            name = name.replace('Başbakan ', '')\
                       .replace('Cumhurbaşkanı ', '')\
                       .replace('Maliye Bakan ', '')
            names = name.split()
            namekeys = [(names[-1],  " ".join(names[:-1]))]
            if len(names) > 2:
                # This is mainly for women with multiple surnames
                namekeys.append((" ".join(names[-2:])," ".join(names[:-2])))
                namekeys.append((" ".join(names[-2:]), names[-2]))
        else:
            return None
        for k in namekeys:
            if k in self.pmnames:
                pmids.update(self.pmnames[k])
                break
        if not pmids and guess and len(names) > 2:
            for i in range(len(names)):
                n = names[:i] + names[i+1:]
                for j in range(len(n) - 2):
                    namekeys.append((" ".join(n[i+1:]), " ".join(n[:i+1])))
            for k in namekeys:
                if k in self.pmnames:
                    pmids.update(self.pmnames[k])
        pmid = next(iter(pmids), None)
        if region is not None:
            pmids = [i for i in pmids if region in self.pmdata[i]['region']]
        if len(pmids): pmid = next(iter(pmids), None)
        if term is not None:
            pmids = [i for i in pmids if term in self.pmdata[i]['term']]
        if len(pmids): pmid = next(iter(pmids), None)
        if party is not None:
            pmids = [i for i in pmids if party in self.pmdata[i]['party']]
        if len(pmids): pmid = next(iter(pmids), None)
        if not guess: pmid = next(iter(pmids), None)
        return pmid

    def get_pm(self, **kwargs):
        pmid = self.get_pmid(**kwargs)
        return self.pmdata[pmid] if pmid else None

    def check_similar(self):
        for i in self.pmdata:
            for j in self.pmdata:
                f1 = self.pmdata[i]['fname'].lower().split()
                f2 = self.pmdata[j]['fname'].lower().split()
                l1 = self.pmdata[i]['lname'].lower().split()
                l2 = self.pmdata[j]['lname'].lower().split()
                if l1 == l2 and (f1[:-1] == f2 or f2[:-1] == f1):
                    print(i, j, self.pmdata[i]['region'], self.pmdata[i]['party'], self.pmdata[i]['term'])
                if f1 == f2 and (l1[:-1] == l2 or l2[:-1] == l1):
                    print(i, j, self.pmdata[i]['region'], self.pmdata[i]['party'], self.pmdata[i]['term'])

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--qid')
    args = ap.parse_args()

    pm = PMData()
#    print(pm.get_pmid('Filiz Kerestecioğlu'))
#    print(pm.get_pmid('Filiz Kerestecioğlu Demir'))
#    print(pm.get_pmid('Mehmet Şahin'))
#    print(pm.get_pmid('Mehmet Erdoğan'))
#    print(pm.get_pmid('Mehmet Erdoğan', region='Adıyaman'))
#    print(pm.get_pm(name='Mehmet Erdoğan', region='Adıyaman'))
#    print(pm.get_pm(name='Devlet Bahçeli'))
#    pm.check_similar()
    with open('debug/speakers', 'rt') as fp:
        for line in fp:
            n = line.strip()
            if not pm.get_pmid(n):
                print("Unknown: {}".format(n))
