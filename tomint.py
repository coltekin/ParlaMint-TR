#!/usr/bin/env python3
""" Convert CoNLL-U files crated by tbmmhtml.py to Parla-CLARIN TEI.
"""

from logging import debug, info, warning, basicConfig
basicConfig(level="INFO", format='%(asctime)s %(message)s')
from conllu import conllu_sentences

from datetime import date

import os
import argparse
from lxml import etree as et
from pmdata import PMData, tbmmterms

# tags to count
CTAGS=("text", "body", "div", "head", "note", "u", "seg",
        "kinesic", "desc", "gap", "vocal", "incident",
        "s", "name", "w", "pc", "linkGrp", "link")


NS = {None: 'http://www.tei-c.org/ns/1.0',
      'xml': 'http://www.w3.org/XML/1998/namespace',
      'xi': 'http://www.w3.org/2001/XInclude',
      }
NSX = dict(NS)
NSX['tei'] = NS[None]
NSX.pop(None)

def remove_xmlnode(doc, xpath, ns=NSX):
    tag = doc.xpath(xpath, namespaces=ns)[0]
    print(tag)
    tag.getparent().remove(tag)

def new_doc(id_, doctype="ana", data=None):
    tc = et.Element("teiCorpus", nsmap=NS)
    tc.set(et.QName(NS['xml'], 'id'), id_)
    tc.set(et.QName(NS['xml'],'lang'), "tr")
#    tc.append(et.Element('teiHeader'))
    # insert the main docuement header, taking defaults from 'head.xml'
    parser = et.XMLParser(remove_blank_text=True,
                          remove_comments=True)
    head = et.parse('head.xml', parser).getroot()
    head = head.xpath('//tei:teiHeader', namespaces=NSX)[0]
    et.cleanup_namespaces(head, top_nsmap=NS)
    tc.append(head)
    if doctype != 'ana':
        remove_xmlnode(tc, '//tei:taxonomy[@xml:id="UD-SYN"]') 
        remove_xmlnode(tc, '//tei:appInfo')
        remove_xmlnode(tc, '//tei:listPrefixDef')
        tag = tc.xpath('//tei:fileDesc/tei:titleStmt/tei:title',
                namespaces=NSX)[0]
        tag.text = tag.text.strip().replace('.ana ', ' ')
        tag = tc.xpath('//tei:publicationStmt/tei:idno[@subtype="handle"]',
                namespaces=NSX)[0]
        tag.text = "http://hdl.handle.net/11356/1388"
        tag = tc.xpath('//tei:publicationStmt/tei:pubPlace/tei:ref',
                namespaces=NSX)[0]
        tag.text = "http://hdl.handle.net/11356/1388"
        tag.set('target', "http://hdl.handle.net/11356/1388")
    return tc

def new_sess(id_, data=None, doctype="ana"):
    tei = et.Element("TEI", nsmap=NS)
    tei.set(et.QName(NS['xml'], 'id'), id_)
    tei.set(et.QName(NS['xml'],'lang'), "tr")
    tei.set('ana', "#parla.session #reference")
    # insert the main docuement header, taking defaults from 'head.xml'
    parser = et.XMLParser(remove_blank_text=True,
                          remove_comments=True)
    shead = et.parse('sess-head.xml', parser).getroot()
    shead = shead.xpath('//tei:teiHeader', namespaces=NSX)[0]
    et.cleanup_namespaces(shead, top_nsmap=NS)
    tei.append(shead)
    text = et.SubElement(tei, 'text', ana='#reference')
    text.set(et.QName(NS['xml'],'lang'), "tr")
    tb = et.SubElement(text, 'body')
    if doctype != 'ana':
        tag = tei.xpath('//tei:fileDesc/tei:titleStmt/tei:title',
                namespaces=NSX)[0]
        tag.text = tag.text.strip().replace('.ana ', ' ')

    meetingdate = id_[22:32]
    term = id_[14:16]
    sessnum = data.get('sess_num', 0)
    tag = tei.xpath('//tei:fileDesc/tei:titleStmt/tei:title[@xml:lang="en"]', namespaces=NSX)[0]
    tag.text = tag.text.replace(' 000 ', " {} ".format(sessnum))

    tag  = tei.xpath(
        '//tei:fileDesc/tei:titleStmt/tei:meeting', namespaces=NSX)[0]
    tag.text = str(sessnum)
    tag.set('n', str(sessnum))

    tag.set('n', str(sessnum))
    tag.text = str(sessnum)
    termtag = et.Element('meeting', n=str(term),
        corresp="#TBMM", ana="#parla.term #TBMM.{}".format(term))
    termtag.text = "Term {}".format(term)
    tag.addprevious(termtag)

    tag = tei.xpath(
        '//tei:sourceDesc/tei:bibl/tei:date', namespaces=NSX)[0]
    tag.text = meetingdate
    tag.set('when', meetingdate)
    tag = tei.xpath(
        '//tei:publicationStmt/tei:date', namespaces=NSX)[0]
    tag.text = date.isoformat(date.today())
    tag.set('when', date.isoformat(date.today()))
    tag = tei.xpath(
        '//tei:settingDesc/tei:setting/tei:date', namespaces=NSX)[0]
    tag.set('when', meetingdate)
    tag.text = '.'.join(reversed(meetingdate.split('-')))
    return tei

def new_sitt(id_, **kwargs):
    sittdiv = et.Element('div', type='debateSection')
    if 'sitt_starttime' in kwargs:
        tmp = et.Element('note', type="time")
        if kwargs['sitt_starttime']:
            tmp.text = kwargs['sitt_starttime'].strip()
        sittdiv.append(tmp)
    if 'sitt_chair' in kwargs:
        tmp = et.Element('note', type="chair")
        if kwargs['sitt_chair']:
            tmp.text = kwargs['sitt_chair'].strip()
        sittdiv.append(tmp)
    return sittdiv

def parse_comment(s):
    p = dict()
    for c in s:
        if c.startswith('# sent_id = '):
            p['sent_id'] = c.replace('# sent_id = ', '').strip()
        elif c.startswith('# new session = '):
            for kv in c.replace('# new session = ', '').split(','):
                k, v = kv.strip().split(':')
                if v == 'None': v = None
                p['new_sess'] = True
                p['sess_' + k] = v
        elif c.startswith('# new sitting = '):
            for kv in c.replace('# new sitting = ', '').split(','):
                k, v = kv.strip().split(':')
                if v == 'None': v = None
                p['new_sitt'] = True
                p['sitt_' + k] = v
        elif c.startswith('# newpar = '):
            p['new_par'] = c.replace('# newpar = ', '').strip()
        elif c.startswith('# speaker = '):
            p['speaker'] = c.replace('# speaker = ', '').strip()
        elif c.startswith('# speaker_type = '):
            p['spktype'] = c.replace('# speaker_type = ', '').strip()
            if p['spktype'] == 'reg': p['spktype'] = 'regular'
        elif c.startswith('# text = '):
            p['text'] = c.replace('# text = ', '').strip()
        elif c.startswith('# transcriber_comment = '):
            p['transcriber_comment'] = True
        elif c.startswith('# pm_id = '):
            p['pm_id'] = c.replace('# pm_id = ', '')
    return p

def new_sent(sent, comm, tagcount):
    s = et.Element('s')
    s.set(et.QName(NS['xml'], 'id'),  comm['sent_id'])
    tagcount['s'] +=1

    lg = et.Element('linkGrp', #corresp=comm['sent_id'],
                                     targFunc="head argument",
                                     type="UD-SYN")
    tagcount['linkGrp'] += 1
    for node in sent.nodes[1:]:
        if node.upos == 'PUNCT': toktyp = 'pc'
        else: toktyp = 'w'
        ne = node.get_misc('NER')
        if not ne or ne == 'O':
            tokparent = s
        elif ne.startswith('B-'):
            tokparent = et.SubElement(s, "name")
            tokparent.set('type', ne.replace('B-', ''))
            tagcount['name'] += 1

        wid = "{}.t{}".format(comm['sent_id'], node.index)
        if node.feats is None:
            msd="UPosTag={}".format(node.upos)
        else:
            msd="UPosTag={}|{}".format(node.upos, node.feats)
        w = et.SubElement(tokparent, toktyp, msd=msd)
        tagcount[toktyp] += 1
        if toktyp == 'w': w.set('lemma', node.lemma)
        w.set(et.QName(NS['xml'], 'id'), wid)
        w.text = node.form.strip()
        if node.misc and 'SpaceAfter=No' in node.misc:
            w.set('join', 'right')

        multi = sent.get_multi(node)
        if multi and (multi.multi != node.index
            or (multi.misc and 'SpaceAfter=No' in multi.misc)):
                w.set('join', 'right')
        tokparent.append(w)

        if node.head == 0:
            head = comm['sent_id']
        else:
            head = "{}.t{}".format(comm['sent_id'], node.head)
        l = et.SubElement(lg, 'link',
                ana="ud-syn:{}".format(node.deprel.replace(":", "_")),
                target="#{} #{}".format(head, wid))
        tagcount['link'] += 1
    s.append(lg)
    return s

def move_notes(node):
    """Move segment and utterance final notes to their parent node."""
    if node is None or len(node) == 0: return
    for ch in reversed(node.getchildren()):
        if ch.tag != 'note': break
        node.remove(ch)
        node.addnext(ch)
    if len(node.getchildren()) == 0:
        node.getparent().remove(node)

def add_speaker(speakers, guests, pmdata,
        spkid=None, spkname=None):
    if spkid and spkid in pmdata:
        speakers.add(spkid)
        return spkid, 'regular'
    else:
        if spkid is not None:
            # this should not happen
            warning("Unknown id {}".format(spkid))
        return None, 'guest'
    pmid = pmdata.get_pmid(name=spkname)
    if pmid is not None:
        speakers.add(pmid)
        return pmid, 'regular'
    spk =  spkname.replace(" ", "")
    spkid = spk
    i = 1
    while spkid not in pmdata:
        i += 1
        spkid = spk + str(i)
    if spkid not in guests:
        guests[spkid] = spkname
    return skpkid, "guest"

def process_conllu(inp):
    f, pmdata, args = inp
    ext = '.ana.xml'
    if args.output_type != 'ana':
        ext = '.xml'
    guest_spk = dict()
    speakers = set()
    term = None
    u, seg, sitt = None, None, None
    meetingdate = os.path.basename(f).replace('.conllu', '')
    spk, seg_i = None, 0
    tagcount = {tag:0 for tag in CTAGS}
    spk_word = list()
    for sent in conllu_sentences(f):
        comm = parse_comment(sent.comment)
        if 'new_sess' in comm:
            term = int(comm.get('sess_term', 0))
            sessid = "ParlaMint-TR_T{}-{}".format(
                    term, comm['sent_id'][:15])
            if args.output_type == 'ana': sessid += ".ana"
            doc = new_sess(sessid, comm, doctype=args.output_type)
            tagcount['body'] += 1
            tb = doc.xpath('/TEI/text/body')[0]
        if 'new_sitt' in comm:
            sitt = new_sitt(tb, **comm)
            tagcount['div'] += 1
            if 'sitt_starttime' in comm: tagcount['note'] += 1
            if 'sitt_chair' in comm: tagcount['note'] += 1
            tb.append(sitt)
            spk, seg_i = None, 0
        if 'new_par' in comm:
            if spk != comm.get('speaker', 'Unknown'):
                # new speaker
                spkid = comm.get('pm_id', None)
                if spkid == 'None': spkid = None
                spkname = comm.get('speaker', None)
                if spkname == 'None': spkname = None
                spkid, spktype = add_speaker(speakers, guest_spk, pmdata,
                        spkid, spkname)
                seg_i = 0
                move_notes(seg)
                move_notes(u)
                u = et.SubElement(sitt, 'u',
                        ana="#{}".format(spktype))
                tagcount['u'] += 1
                if spkid is not None:
                    u.set('who', '#{}'.format(spkid))
#                    else:
#                        u.set('who', '#Unknown')
                u.set(et.QName(NS['xml'], 'id'), comm['new_par'])
            move_notes(seg)
            seg = et.SubElement(u, 'seg')
            seg.set(et.QName(NS['xml'], 'id'),
                    "{}.seg{}".format(comm['new_par'], seg_i))
            seg_i += 1
            tagcount['seg'] += 1

        if 'transcriber_comment' in comm:
            note = et.SubElement(seg, 'note')
            note.text = comm['text'].strip(' ()[]')
            tagcount['note'] += 1
        else:
            if args.output_type == 'ana':
                seg.append(new_sent(sent, comm, tagcount))
            else:
                if not seg.text:
                    seg.text = sent.text().strip()
                else:
                    seg.text += " " + sent.text()
        spk_word.append((spkid, spktype, len(sent.tokens())))


    # Approcimate heuristic, trying to skip interruptions
    wordcount, speechcount = 0, 0
    for i, (spk, spktype, wc) in enumerate(spk_word):
        wordcount += wc
        if i == 0: prev_spk = None
        else: prev_spk = spk_word[i-1]
        if i == len(spk_word) - 1: next_spk = None
        else: next_spk = spk_word[i+1]
        if spktype == 'regular' and prev_spk != spk and prev_spk != next_spk and wc > 30:
            speechcount += 1
        
    path = args.output_dir
    if args.split:
        year = os.path.basename(f).split('-')[0]
        path = os.path.join(path, year)
    if path: os.makedirs(path, exist_ok=True)
    outfile = os.path.basename(f).replace('.conllu', ext)
    outfile = "{}_T{}-tbmm-{}".format(args.prefix, term, outfile)
    outpath = os.path.join(path, outfile)
    if args.no_sample:
        title = doc.xpath('//tei:fileDesc/tei:titleStmt/tei:title[@xml:lang="en"]', namespaces=NSX)[0]
        title.text = title.text.replace(' SAMPLE', '')
    for tag,count in tagcount.items():
        xmltag = doc.xpath(
            '//tei:namespace/tei:tagUsage[@gi="{}"]'.format(tag),
            namespaces=NSX)[0]
        if count == 0:
            xmltag.getparent().remove(xmltag)
        else:
            xmltag.set('occurs', str(count))
    tag = doc.xpath(
        '//tei:fileDesc/tei:extent/tei:measure[@unit="speeches"]',
        namespaces=NSX)[0]
    tag.text = "{:,} {}".format(speechcount,
        "speeches" if speechcount > 1 else "speech")
    tag.set('quantity', str(speechcount))
    tag = doc.xpath(
        '//tei:fileDesc/tei:extent/tei:measure[@unit="words"]',
        namespaces=NSX)[0]
    tag.text = "{:,} words".format(wordcount)
    tag.set('quantity', str(wordcount))
    with open(outpath, 'wt') as fp:
        fp.write(et.tostring(doc, xml_declaration=True,
            pretty_print=True, encoding='utf-8').decode())
#            print(et.tostring(doc, pretty_print=True,
#                encoding='unicode'), file=fp)

    return outfile, wordcount, speechcount, tagcount, guest_spk, speakers, term

if __name__ == "__main__":
    from multiprocessing import Pool
    ap = argparse.ArgumentParser()
    ap.add_argument('input', nargs="+")
    ap.add_argument('--output-dir', '-o', default='')
    ap.add_argument('--output-type', '-T', default='ana')
    ap.add_argument('--nproc', '-j', default=4, type=int)
    ap.add_argument('--debug', '-d', action='store_true')
    ap.add_argument('--skip-from', '-s')
    ap.add_argument('--split', '-S', action='store_true',
            help="Split xml files into directories per year.")
    ap.add_argument('--no-sample', '-R', action='store_true',
            help="This is the real corpus, (remove 'SAMPLE' from the header.)")
    ap.add_argument('--prefix', '-p', default='ParlaMint-TR')
    args = ap.parse_args()

    ext = '.ana.xml'
    if args.output_type != 'ana':
        args.output_type = 'plain'
        ext = '.xml'

    print(args.output_type)

    pmdata = PMData()

    # Create the main document
    maindoc = new_doc("ParlaMint-TR" +
            ('.ana' if args.output_type == 'ana' else ''),
            doctype=args.output_type)

    tagcount_main = {tag:0 for tag in CTAGS}
    # TODO: speech count is wrong
    wordcount_main = 0
    speechcount_main = 0
    guest_spk = dict()
    speakers = set()
    terms = set()

    pool = Pool(processes=args.nproc)
    inp = [(f, pmdata, args) for f in args.input]
    res = pool.map(process_conllu, inp)

    for outfile, wc, sc, tagc, guest, spk, term in res:
        wordcount_main += wc
        speechcount_main += sc
        guest_spk.update(guest)
        speakers.update(spk)
        terms.add(term)
        for tag, count in tagc.items():
            tagcount_main[tag] += count
        tagcount_main['text'] += 1
        maindoc.append(
                et.Element(et.QName(NS['xi'], 'include'),
                    href=outfile))

#     for f in args.input:
#         wc, tagc, guest, spk, term = process_conllu(f, pmdata, args)
#         wordcount_main += wc
#         guest_spk.update(guest)
#         speakers.update(spk)
#         terms.add(term)
#         for tag, count in tagc.items():
#             tagcount_main[tag] += count
# 
# 
#     for f in args.input:
#         tagcount_main['text'] += 1
#         outfile = os.path.basename(f).replace('.conllu', ext)
#         year = os.path.basename(f).split('-')[0]
#         if args.split:
#             outfile = '/'.join((year, outfile))
#         maindoc.append(
#                 et.Element(et.QName(NS['xi'], 'include'),
#                     href=outfile))

    person_list = maindoc.xpath('//tei:listPerson', namespaces=NSX)[0]
    for spkid in sorted(speakers):
        pm = pmdata.get(spkid)
        p = et.SubElement(person_list, 'person')
        p.set(et.QName(NS['xml'], 'id'), spkid)
        pn = et.SubElement(p, 'persName')
        surname = et.SubElement(pn, 'surname')
        surname.text = pm['lname'].strip()
        forename = et.SubElement(pn, 'forename')
        forename.text = pm['fname'].strip()
        p.append(et.Element('sex', value=pm['sex']))
        for i, term in enumerate(pm['term']):
            if term == 0: continue
            a_parl = et.SubElement(p, 'affiliation',
                role='MP', ref='#TBMM', ana="#TBMM.{}".format(term))
            a_parl.set('from', tbmmterms[term][0])
            party = pm['party'][i]
            if party != "Bağımsız":
                a_party = et.SubElement(p, 'affiliation', role='member',
                        ref='#party.{}'.format(party),
                        ana="#TBMM.{}".format(term))
                a_party.set('from', tbmmterms[term][0])
            if tbmmterms[term][1] is not None:
                a_parl.set('to', tbmmterms[term][1])
                if party != "Bağımsız":
                    a_party.set('to', tbmmterms[term][1])
    for spkid, spk in guest_spk:
        p = et.SubElement(person_list, 'person')
        p.set(et.QName(NS['xml'], 'id'), spkid)
        pn = et.SubElement(p, 'persName')
        surname = et.SubElement(pn, 'surname')
        surname.text = name.split()[-1].strip() # TODO: guesswork
        forename = et.SubElement(pn, 'forename')
        forename.text = " ".join(name.split()[:-1]).trip() # FIXME

    out_ana = "{}{}".format(args.prefix, ext)
    for tag,count in tagcount_main.items():
        xmltag = maindoc.xpath(
            '//tei:namespace/tei:tagUsage[@gi="{}"]'.format(tag),
            namespaces=NSX)[0]
        if count == 0:
            xmltag.getparent().remove(xmltag)
        else:
            xmltag.set('occurs', str(count))
    stag = maindoc.xpath(
        '//tei:fileDesc/tei:extent/tei:measure[@unit="speeches"]',
        namespaces=NSX)[0]
    stag.text = "{:,} {}".format(speechcount_main,
            "speeches" if speechcount_main > 1 else "speech")
    stag.set('quantity', str(speechcount_main))
    wtag = maindoc.xpath(
        '//tei:fileDesc/tei:extent/tei:measure[@unit="words"]',
        namespaces=NSX)[0]
    wtag.text = "{:,} words".format(wordcount_main)
    wtag.set('quantity', str(wordcount_main))
    with open(os.path.join(args.output_dir, out_ana),'wt') as fp:
        if args.no_sample:
            title = maindoc.xpath('//tei:fileDesc/tei:titleStmt/tei:title[@xml:lang="en"]', namespaces=NSX)[0]
            title.text = title.text.replace(' SAMPLE', '')
        fp.write(et.tostring(maindoc, xml_declaration=True,
            pretty_print=True, encoding='utf-8').decode())
