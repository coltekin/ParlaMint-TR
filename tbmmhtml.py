#!/usr/bin/env python3

from logging import debug, info, warning, basicConfig
basicConfig(level="INFO", format='%(asctime)s %(message)s')

import argparse
from lxml.html import soupparser
from bs4 import UnicodeDammit
import regex as re
import os
import sys
import csv
from trmorpy import TrMorph
from trmorpy.utils import tr_capitalize

from patterns import *

class Session:
    __slots__ = ('num', 'startdate', 'enddate', 'starttime','endtime',
                 'sittings', 'term')
    def __init__(self):
        self.startdate = None
        self.enddate = None
        self.starttime = None
        self.endtime = None
        self.num = None
        self.nsittigns = 0
        self.sittings = []

    def new_sitting(self):
        sitt = Sitting()
        self.append(sitt)
        self.nsittings += 1
        return sitt 

    def write(self, filename=None):
        if filename is None:
            outf = sys.stdout
        else:
            outf = open(filename, "wt")
        print("# session: ", end="", file=outf)
        print(", ".join(
                ("{}={}".format(x, str(getattr(self,x))) 
                    for x in self.__slots__
                    if x != 'sittings')),
                file=outf)
        for i, sitt in enumerate(self.sittings):
            print("## sitting: ", end="", file=outf)
            print(", ".join(
                    ("{}={}".format(x, str(getattr(sitt,x))) 
                        for x in sitt.__slots__
                        if x != 'par')),
                    file=outf)
            for par in sitt.par:
                print("{}\t{}\t{}\t{}".format(i+1, *par),
                        file=outf)

    def write_conllu(self, filename=None, prefix='tbmm'):
        trm = TrMorph()
        if filename is None:
            outf = sys.stdout
        else:
            outf = open(filename, "wt")

        print("# new session = ", end="", file=outf)
        self.nsittings = len(self.sittings)
        print(", ".join(
                ("{}:{}".format(x, str(getattr(self,x))) 
                    for x in self.__slots__
                    if x != 'sittings')),
                file=outf)
        for i, sitt in enumerate(self.sittings):
            print("# new sitting = ", end="", file=outf)
            print(", ".join(
                    ("{}:{}".format(x, str(getattr(sitt,x))) 
                        for x in sitt.__slots__
                        if x != 'par')),
                    file=outf)
            for j,par in enumerate(sitt.par):
                sentences, analyses = trm.tokenize(par[2], 
                        return_spaces=True, return_analyses=True)
                parid = "{}-{}s{:02d}p{:03d}".format(
                    prefix, self.startdate, i + 1, j + 1)
                print("# newpar = ", parid, file=outf)
                for k, sent in enumerate(sentences):
                    print("# speaker = ", par[0], file=outf)
                    print("# speaker_type = ", par[1], file=outf)
                    print("# text = ", "".join(sent), file=outf)
                    print("# sent_id = {}-{:06d}".format(
                        parid, 10 * (k + 1)), file=outf)
                    if sent[0] in {'(', '['} and sent[-1] in {')', ']'}:
                        print("# transcriber_comment = true",
                                file=outf)

                    senta = trm.disambiguate(
                            [a for a in analyses[k] if a[0] != '_⟨X⟩'])
                    aidx = 0
                    tokid = 0
                    for itok, tok in enumerate(sent):
                        if tok == ' ': continue
                        misc = '_'
                        if itok < (len(sent) - 1) and sent[itok + 1] != ' ':
                            misc = 'SpaceAfter=No'
                        a = senta[aidx]
                        uda = trm.ud_analysis(tok, a)
                        if len(uda) > 1:
                            print("{}-{}\t{}\t_\t_\t_\t_\t_\t_\t_\t{}".format(
                                tokid + 1, tokid + len(uda), tok, misc),
                                file=outf)
                            misc = "_"
                        for form, lemma, pos, infl \
                                in uda:
                            tokid += 1
                            head, dep = 1, 'dep'
                            if pos == 'PUNCT': dep = 'punct'
                            if tokid == 1:
                                head, dep = 0, 'root'
                            feat = "|".join(sorted(infl))
                            if len(feat) == 0: feat = "_"
                            print("{}\t{}\t{}\t{}\t_\t{}\t{}\t{}\t_\t{}".format(
                                tokid, form, lemma, pos,
                                feat, head, dep, misc),
                                file=outf)
                        aidx += 1
                    print("", file=outf)

class Sitting:
    __slots__ = ('startdate', 'enddate', 'starttime','endtime', 
             'chair', 'scribes', 'par')
    def __init__(self):
        self.startdate = None
        self.enddate = None
        self.starttime = None
        self.endtime = None
        self.chair = None
        self.scribes = []
        self.par = []
    def __str__(self):
        return ','.join(("{}={}".format(x, str(getattr(self, x)))
                            for x in self.__slots__ if getattr(self, x)))
    def __repr__(self):
        return str(self)

month2num = {k:i+1 for i,k in
        enumerate(('ocak', 'şubat', 'mart', 'nisan', 'mayıs', 'haziran', 
            'temmuz', 'ağustos', 'eylül', 'ekim', 'kasım', 'aralık'))
}

def to_isodate(m):
    year = int(m['year'])
    day = int(m['day'])
    month = month2num[m['month'].lower()]
    return "{:04}-{:02}-{:02}".format(year, month, day)

# Sections:
#   'head'  contians the session information and contents
#   'sitth' contians the header of the 'sitting'
#   'sitt'  actual data in a sitting
#
sect_re = {
        'head': re.compile("|".join(
            (sitting_p,date_p,sess_p,contents_p,headmisc_p,contentsX_p))),
        'sitth': re.compile("|".join(
            (begin_p,
             date_p,chair_p,
             scribe_p,
             sithend_p,
             sitstart_p,
             sithignore_p))),
        'sitt': re.compile("|".join(
            (contents_p,
             newspk_p,
             sitting_p,
             end_p,
             paragr_p,
             sitting_p))), # order is important
}

chfilter = str.maketrans({"\n": " ", 
                       "\r": None,
                       "\u2000": " ",
                       "\u2001": " ",
                       "\u2002": " ",
                       "\u2003": " ",
                       "\u2004": " ",
                       "\u2005": " ",
                       "\u2006": " ",
                       "\u2007": " ",
                       "\u2008": " ",
                       "\u2009": " ",
                       "\u200A": " ",
                       "\u200B": None,
                       "\u202F": " ",
                       "\u205F": " ",
                       "\u3000": " ",
                       "\u1680": " ",
                       "\u00A0": " ",
                       "\u00AD": None,
                       "\uFEFF": None})

def normalize_speaker(spk):
    names = spk.strip().split()
    for i, n in enumerate(names):
        names[i] = tr_capitalize(n.strip())
    return ' '.join(names)

fname_re = re.compile(r'.*/tutanak/donem(?P<term>[0-9]+)/.*')
def read_html(filename, pmnames=None, pmdata=None, debug=None, strict=True):
    os.makedirs('debug', exist_ok=True)
    spkf = open('debug/speakers', 'ta+')
    spkif = open('debug/speakers-intro', 'ta+')
    spkpf = open('debug/speakers-par', 'ta+')
    sess = Session()
    with open(filename, 'rb') as f:
        content = f.read()
    m = fname_re.match(filename)
    if m:
        sess.term = m.group('term')
    else:
        sess.term = '0'
    html = soupparser.fromstring(content)
    sect = 'head'
    sitt = None
    for p in html.findall('.//p'):
        # skip content inside tables
        skip = False
        for ancestor in p.iterancestors():
            if ancestor.tag == 'table':
                skip = True
                break
        if skip: continue
        ptext = p.text_content().strip().translate(chfilter)
        if not ptext: continue
        m = sect_re[sect].match(ptext)
        if debug:
            print('SECT: {}'.format(sect), 'PAR TEXT:', ptext)
        if m:
            if debug:
                print('MATCH ({}):'.format(sect), ptext, m.groupdict())
            matches = m.groupdict()
            if matches.get('spk'):
                sect = 'sitt'
                spk, text = matches['spk'], matches['text']
                if spk == 'BAŞKAN' or spk == 'TBMM BAŞKAN VEKİLİ':
                    spk = sitt.chair
                    spktype = 'chair'
                    spkregion = 'unknown'
                elif matches.get('spkintro'):
                    sect = 'sitt'
                    if 'BAKANI' in matches['spkintro']:
                        spktype = 'minister'
                        spkregion = 'unknown'
                    elif 'CUMHURBAŞKANI YARDIMCISI' in matches['spkintro']:
                        spktype = 'vice president'
                        spkregion = 'unknown'
                    elif 'CUMHURBAŞKANI' == matches['spkintro']:
                        spktype = 'president'
                        spkregion = 'unknown'
                else:
                    spktype = 'unknown'
                    spkregion = 'unknown'
                spk = normalize_speaker(spk)
                if pmnames is not None and sess.term in pmnames:
                    if spk == sitt.chair:
                        spktype = 'chair'
                    elif spk in pmnames[sess.term]:
                        spktype = 'reg'
                    else:
                        spktype = 'unknown'
                        pass
#                        print("--- unknown speaker: ", spk, spktype, filename)
                # debugging stuff
                print(spk, file=spkf)
                os.makedirs('debug',exist_ok=True)
                if matches.get('spkintro'):
                    print(matches['spkintro'], file=spkif)
                if matches.get('spkpar'):
                    tmp = normalize_speaker(matches['spkpar'])
                    if not tmp.startswith('Devam'):
                        spkregion = tmp
                    print(spkregion, file=spkpf)
                sitt.par.append((spk, spktype, text))
            elif matches.get('text'):
                text = matches['text']
                if not ('.' in text or '?' in text \
                            or '…' in text or ',' in text\
                            or '!' in text)\
                    and len(text.split()) < 5:
                    # most probably a listing included in the records
                    spk = 'Unknown'
                    spktype = 'None'
                sitt.par.append((spk, spktype, text))
            elif matches.get('sitting'):
                sect = 'sitth'
                sitt = sess.new_sitting()
            elif matches.get('chair'):
                sitt.chair = normalize_speaker(matches['chair'])
            elif matches.get('starttime'):
                sitt.starttime = matches['starttime']
            elif matches.get('sithend'):
                sect = 'sitt'
            elif matches.get('endtime'):
                sitt.endtime = matches['endtime']
                sect = 'head'
            elif matches.get('year'):
                sess.startdate=to_isodate(matches)
            elif matches.get('sessnum'):
                sess.num = matches['sessnum']
            elif matches.get('cnum1'):
                pass
            elif matches.get('cnum2'):
                pass
            elif matches.get('cnum3'):
                pass
            elif matches.get('contdscX'):
                pass
            elif matches.get('headmisc'):
                pass
            elif matches.get('scribe'):
                sitt.scribes.append(matches['scribe'])
            elif matches.get('scribe1'):
                sitt.scribes.append(matches['scribe1'])
            elif matches.get('scribe2'):
                sitt.scribes.append(matches['scribe2'])
            elif matches.get('closed'):
                if debug: print('------closed----------')
                sect = 'sitt'
            else:
                if debug: print('---skip---', ptext, matches)
#            print('--', sect, '--', text)#, matches)
        else:
            print('---unparsed--- {}: __{}__'.format(sect, ptext),
                    file=sys.stderr)
            if strict:
                return None
    if len(sess.sittings) == 0:
        return None
    if not sess.starttime:
        sess.starttime = sess.sittings[0].starttime
    if not sess.endtime:
        sess.endtime = sess.sittings[-1].endtime
    return sess

def create_conllu(inp):
    filename, pmnames, pmdata = inp
    print('--->', filename, flush=True)
    s = read_html(filename, pmnames=pmnames, pmdata=pmdata, debug=args.debug)
    if s is not None:
        print(filename, s.startdate, len(s.sittings), flush=True)
        s.write_conllu(os.path.join('conllu', s.startdate + '.conllu'))
    else:
        print(filename,'FAILED', flush=True)

if __name__ == "__main__":
    from multiprocessing import Pool
    ap = argparse.ArgumentParser()
    ap.add_argument('input', nargs="+")
    ap.add_argument('--output', default='.')
    ap.add_argument('--nproc', '-j', default=4, type=int)
    ap.add_argument('--debug', '-d', action='store_true')
    ap.add_argument('--skip-from', '-s')
    ap.add_argument('--pm-list', '-m', default='pm.tsv')
    args = ap.parse_args()

    transcripts = args.input
    if args.skip_from:
        with open(args.skip_from, 'rt') as f:
            skip = set()
            for line in f:
                line = line.strip()
                if line.startswith('html/'):# \
#                        and not line.endswith('FAILED'):
                    skip.add(line.split()[0])
        transcripts = [x for x in args.input if x not in skip]

    pmdata = []
    pmnames = dict()
    with open(args.pm_list, 'rt') as f:
        csvr = csv.DictReader(f, delimiter='\t')
        for row in csvr:
            pmdata.append([row[x] for x in ('name', 'term', 'region', 'party')])
            if row['term'] not in pmnames:
                pmnames[row['term']] = set()
            pmnames[row['term']].add(row['name'])

    os.makedirs('conllu',exist_ok=True)
    pool = Pool(processes=args.nproc)
    inp = [(x, pmnames, pmdata) for x in transcripts]
    res = pool.map(create_conllu, inp)
