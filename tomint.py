#!/usr/bin/env python3
""" Convert CoNLL-U files crated by tbmmhtml.py to Parla-CLARIN TEI.
"""

from logging import debug, info, warning, basicConfig
basicConfig(level="INFO", format='%(asctime)s %(message)s')
from conllu import conllu_sentences

import os
import argparse
from lxml import etree as et
from pmdata import PMData, tbmmterms

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
    return tei

def new_sitt(id_, **kwargs):
    sittdiv = et.Element('div', type='debateSection')
    if 'sitt_starttime' in kwargs:
        tmp = et.Element('note', type="time")
        tmp.text = kwargs['sitt_starttime'].strip()
        sittdiv.append(tmp)
    if 'sitt_chair' in kwargs:
        tmp = et.Element('note', type="chair")
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

def new_sent(sent, comm):
    s = et.Element('s')
    s.set(et.QName(NS['xml'], 'id'),  comm['sent_id'])

    lg = et.Element('linkGrp', #corresp=comm['sent_id'],
                                     targFunc="head argument",
                                     type="UD-SYN")
    for node in sent.nodes[1:]:
        if node.upos == 'PUNCT': toktyp = 'pc'
        else: toktyp = 'w'
        ne = node.get_misc('NER')
        if not ne or ne == 'O':
            tokparent = s
        elif ne.startswith('B-'):
            tokparent = et.SubElement(s, "name")
            tokparent.set('type', ne.replace('B-', ''))

        wid = "{}.t{}".format(comm['sent_id'], node.index)
        w = et.SubElement(tokparent, toktyp,
                msd="UPosTag={}|{}".format(node.upos, node.feats))
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


if __name__ == "__main__":
    from multiprocessing import Pool
    ap = argparse.ArgumentParser()
    ap.add_argument('input', nargs="+")
    ap.add_argument('--output-dir', '-o', default='')
    ap.add_argument('--output-type', '-T', default='ana')
    ap.add_argument('--nproc', '-j', default=4, type=int)
    ap.add_argument('--debug', '-d', action='store_true')
    ap.add_argument('--skip-from', '-s')
    ap.add_argument('--prefix', '-p', default='ParlaMint-TR')
    args = ap.parse_args()

    ext = '.ana.xml'
    template_mainh = 'head.xml'
    template_sessh = 'sess-head.xml'
    if args.output_type != 'ana':
        args.output_type = 'plain'
        ext = '.xml'
    print(args.output_type)

    pmdata = PMData()

    # Create the main document
    maindoc = new_doc("ParlaMint-TR" +
            ('.ana' if args.output_type == 'ana' else ''),
            doctype=args.output_type)

    guest_spk = dict()
    speakers = set()
    files = dict()
    term = None
    u, seg, sitt = None, None, None
    for f in args.input:
        spk, seg_i = None, 0
        for sent in conllu_sentences(f):
            comm = parse_comment(sent.comment)
            if 'new_sess' in comm:
                term = int(comm.get('sess_term', 0))
                sessid = "ParlaMint-TR_T{}-{}".format(
                        term, comm['sent_id'][:15])
                if args.output_type == 'ana': sessid += ".ana"
                doc = new_sess(sessid, comm, doctype=args.output_type)
                tb = doc.xpath('/TEI/text/body')[0]
            if 'new_sitt' in comm:
                sitt = new_sitt(tb, **comm)
#                print(et.tostring(sitt, encoding='unicode'))
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
                    if spkid is not None:
                        u.set('who', '#{}'.format(spkid))
                    else:
                        u.set('who', '#Unknown')
                    u.set(et.QName(NS['xml'], 'id'), comm['new_par'])
                move_notes(seg)
                seg = et.SubElement(u, 'seg')
                seg.set(et.QName(NS['xml'], 'id'),
                        "{}.seg{}".format(comm['new_par'], seg_i))
                seg_i += 1

            if 'transcriber_comment' in comm:
                note = et.SubElement(seg, 'note')
                note.text = comm['text'].strip()
            else:
                if args.output_type == 'ana':
                    seg.append(new_sent(sent, comm))
                else:
                    if not seg.text: seg.text = sent.text().strip()
                    else: seg.text += " " + sent.text()

#        path = os.path.join(args.output_dir, 'term-{:03d}'.format(term))
        path = args.output_dir
        if path: os.makedirs(path, exist_ok=True)
        outfile = os.path.basename(f).replace('.conllu', ext)
        outfile = "{}_T{}-tbmm-{}".format(args.prefix, term, outfile)
        outpath = os.path.join(path, outfile)
        with open(outpath, 'wt') as fp:
            fp.write(et.tostring(doc, xml_declaration=True,
                pretty_print=True, encoding='utf-8').decode())
#            print(et.tostring(doc, pretty_print=True,
#                encoding='unicode'), file=fp)
        maindoc.append(
                et.Element(et.QName(NS['xi'], 'include'),
                    href=outfile))

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
    with open(os.path.join(args.output_dir, out_ana),'wt') as fp:
        fp.write(et.tostring(maindoc, xml_declaration=True,
            pretty_print=True, encoding='utf-8').decode())
