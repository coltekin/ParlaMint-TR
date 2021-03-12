#!/usr/bin/env python3
""" Convert CoNLL-U files crated by tbmmhtml.py to Parla-CLARIN TEI.
"""

from logging import debug, info, warning, basicConfig
basicConfig(level="INFO", format='%(asctime)s %(message)s')
from conllu import conllu_sentences

import os
import argparse
from lxml import etree as et

NS = {None: 'http://www.tei-c.org/ns/1.0',
      'xml': 'http://www.w3.org/XML/1998/namespace',
      'xi': 'http://www.w3.org/2001/XInclude',
      }
NSX = dict(NS)
NSX['tei'] = NS[None]
NSX.pop(None)

def new_doc(id_, data=None):
    tc = et.Element("teiCorpus", nsmap=NS)
    tc.set(et.QName(NS['xml'], 'id'), id_)
    tc.set(et.QName(NS['xml'],'lang'), "tr")
#    tc.append(et.Element('teiHeader'))
    return tc

def new_sess(id_, data=None, template="sess-head.ana.xml"):
    tei = et.Element("TEI", nsmap=NS)
    tei.set(et.QName(NS['xml'], 'id'), id_)
    tei.set(et.QName(NS['xml'],'lang'), "tr")
    tei.set('ana', "#parla.session #reference")
    # insert the main docuement header, taking defaults from 'head.xml'
    parser = et.XMLParser(remove_blank_text=True,
                          remove_comments=True)
    shead = et.parse(template, parser).getroot()
    shead = shead.xpath('//tei:teiHeader', namespaces=NSX)[0]
    et.cleanup_namespaces(shead, top_nsmap=NS)
    tei.append(shead)
    text = et.SubElement(tei, 'text', ana='#reference')
    text.set(et.QName(NS['xml'],'lang'), "tr")
    tb = et.SubElement(text, 'body')
    return tei

def new_sitt(id_, **kwargs):
    sittdiv = et.Element('div', type='debateSection')
    if 'sitt_starttime' in kwargs:
        tmp = et.Element('note', type="time")
        tmp.text = kwargs['sitt_starttime']
        sittdiv.append(tmp)
    if 'sitt_chair' in kwargs:
        tmp = et.Element('note', type="chair")
        tmp.text = kwargs['sitt_chair']
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
        elif c.startswith('# sent_id = '):
            p['sent_id'] = c.replace('# sent_id = ', '').strip()
        elif c.startswith('# speaker = '):
            p['speaker'] = c.replace('# speaker = ', '').strip()
        elif c.startswith('# text = '):
            p['text'] = c.replace('# text = ', '').strip()
        elif c.startswith('# transcriber_comment = '):
            p['transcriber_comment'] = True
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
        wid = "{}.t{}".format(comm['sent_id'], node.index)
        w = et.SubElement(s, toktyp,
                msd="UPosTag={}|{}".format(node.upos, node.feats))
        if toktyp == 'w': w.set('lemma', node.lemma)
        w.set(et.QName(NS['xml'], 'id'), wid)
        w.text = node.form
        if node.misc and 'SpaceAfter=No' in node.misc:
            w.set('join', 'right')

        multi = sent.get_multi(node)
        if multi and (multi.multi != node.index
            or (multi.misc and 'SpaceAfter=No' in multi.misc)):
                w.set('join', 'right')
        s.append(w)

        if node.head == 0:
            head = comm['sent_id']
        else:
            head = "{}.t{}".format(comm['sent_id'], node.head)
        l = et.SubElement(lg, 'link',
                ana="ud-syn:{}".format(node.deprel),
                target="{} {}".format(head, wid))
        s.append(lg)
    return s


if __name__ == "__main__":
    from multiprocessing import Pool
    ap = argparse.ArgumentParser()
    ap.add_argument('input', nargs="+")
    ap.add_argument('--output-dir', default='')
    ap.add_argument('--output-type', '-T', default='ana')
    ap.add_argument('--nproc', '-j', default=4, type=int)
    ap.add_argument('--debug', '-d', action='store_true')
    ap.add_argument('--skip-from', '-s')
    ap.add_argument('--pm-list', '-m', default='pm.tsv')
    ap.add_argument('--prefix', '-p', default='ParlaMint-TR')
    args = ap.parse_args()

    ext = '.ana.xml'
    template_mainh = 'head.ana.xml'
    template_sessh = 'sess-head.xml'
    if args.output_type != 'ana':
        args.output_type = 'plain'
        ext = '.xml'
        template_mainh = 'head.plain.xml'
    print(args.output_type)


    # Create the main document
    maindoc = new_doc("trParl.Sample")

    speakers = dict()
    files = dict()
    term = None
    for f in args.input:
        spk, seg_i = None, 0
        for sent in conllu_sentences(f):
            comm = parse_comment(sent.comment)
            if 'new_sess' in comm:
                term = int(comm.get('sess_term', 0))
                sessid = "ParlaMint-TR_T{}_{}".format(term, comm['sent_id'][:15])
                doc = new_sess(sessid, comm, template=template_sessh)
                tb = doc.xpath('/TEI/text/body')[0]
            if 'new_sitt' in comm:
                sitt = new_sitt(tb, **comm)
#                print(et.tostring(sitt, encoding='unicode'))
                tb.append(sitt)
            if 'new_par' in comm:
                if spk != comm.get('speaker', 'unknown'):
                    spk = comm.get('speaker', 'Unknown')
                    spktype = comm.get('speaker_type', 'None')
                    if spktype == 'reg': spktype = 'regular'
                    elif spktype == 'unknown': spktype = 'guest'
                    elif spktype == 'None': spktype = 'unknown'
                    spkid = spk.replace(" ", "")
                    seg_i = 0
                    u = et.SubElement(sitt, 'u',
                            who="#{}".format(spkid),
                            ana="#{}".format(spktype))
                    u.set(et.QName(NS['xml'], 'id'), comm['new_par'])
                    #TODO: better speker management
                    if spkid != 'Unknown' and spkid not in speakers:
                        speakers[spkid] = spk
                seg = et.SubElement(u, 'seg')
                seg.set(et.QName(NS['xml'], 'id'),
                        "{}.seg{}".format(comm['new_par'], seg_i))
                seg_i += 1

            # TODO: check if the notes attach to the correct points
            # TODO: is analysis possible for comments?
            if 'transcriber_comment' in comm:
                pass
                note = et.SubElement(seg, 'note')
                note.text = comm['text']
            else:
                if args.output_type == 'ana':
                    seg.append(new_sent(sent, comm))
                else:
                    if not seg.text: seg.text = sent.text()
                    else: seg.text += " " + sent.text()

#        path = os.path.join(args.output_dir, 'term-{:03d}'.format(term))
        path = args.output_dir
        if path: os.makedirs(path, exist_ok=True)
        outfile = os.path.basename(f).replace('.conllu', ext)
        outfile = "{}_T{}_{}".format(args.prefix, term, outfile)
        outpath = os.path.join(path, outfile)
        with open(outpath, 'wt') as fp:
            fp.write(et.tostring(doc, xml_declaration=True,
                pretty_print=True, encoding='utf-8').decode())
#            print(et.tostring(doc, pretty_print=True,
#                encoding='unicode'), file=fp)
        maindoc.append(
                et.Element(et.QName(NS['xi'], 'include'),
                    href=outfile))

    # insert the main docuement header, taking defaults from 'head.xml'
    parser = et.XMLParser(remove_blank_text=True,
                          remove_comments=True)
    head = et.parse(template_mainh, parser).getroot()
    head = head.xpath('//tei:teiHeader', namespaces=NSX)[0]
    et.cleanup_namespaces(head, top_nsmap=NS)
    firstincl = maindoc.xpath('//xi:include', namespaces=NSX)[0]
    firstincl.addprevious(head)

    person_list = head.xpath('//tei:listPerson', namespaces=NSX)[0]
    for sid, name in speakers.items():
        # TODO: more precise/detailed info
        p = et.SubElement(person_list, 'person')
        p.set(et.QName(NS['xml'], 'id'), sid)
        pn = et.SubElement(p, 'persName')
        surname = et.SubElement(pn, 'surname')
        surname.text = name.split()[-1] # FIXME
        forename = et.SubElement(pn, 'forename')
        forename.text = " ".join(name.split()[:-1]) # FIXME
#        p.append(et.Element('sex', value='F'))

    out_ana = "{}{}".format(args.prefix, ext)
    with open(os.path.join(args.output_dir, out_ana),'wt') as fp:
        fp.write(et.tostring(maindoc, xml_declaration=True,
            pretty_print=True, encoding='utf-8').decode())
